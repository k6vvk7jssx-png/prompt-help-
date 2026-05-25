import logging
from dataclasses import dataclass
from threading import Lock

from prompt_optimizer_app.consent_dialog import confirm_deepseek_run, confirm_web_helper_run
from prompt_optimizer_app.config import AppConfig
from prompt_optimizer_app.deepseek import DeepSeekClient
from prompt_optimizer_app.provider_detector import detect_provider
from prompt_optimizer_app.runtime_settings import RuntimeSettingsStore
from prompt_optimizer_app.web_helpers import WebHelperError, WebHelperPipeline


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OptimizationResult:
    optimized_text: str
    detected_provider: str
    execution_path: str
    helper_name: str
    helper_latency_ms: int
    helper_error_code: str
    helper_error_message: str
    active_window_title: str
    consent_required: bool
    consent_granted: bool
    consent_denied: bool


@dataclass(frozen=True)
class PipelineStatus:
    last_provider: str = "generic"
    last_execution_path: str = "-"
    last_helper_name: str = "-"
    last_helper_error: str = ""
    last_helper_latency_ms: int = 0
    web_access_armed: bool = False
    consent_required: bool = False
    consent_granted: bool = False
    consent_denied: bool = False


class OptimizationRouter:
    def __init__(
        self,
        config: AppConfig,
        deepseek_client: DeepSeekClient,
        web_helpers: WebHelperPipeline,
        runtime_settings_store: RuntimeSettingsStore,
    ):
        self.config = config
        self.deepseek_client = deepseek_client
        self.web_helpers = web_helpers
        self.runtime_settings_store = runtime_settings_store
        self._status = PipelineStatus()
        self._status_lock = Lock()

    @property
    def status(self) -> PipelineStatus:
        with self._status_lock:
            return self._status

    def optimize(self, selected_text: str) -> OptimizationResult:
        runtime_settings = self.runtime_settings_store.load()
        detection = detect_provider(runtime_settings.auto_provider_detection)
        provider = detection.provider
        active_window_title = detection.active_window_title

        can_try_web = (
            self.config.web_helpers_enabled
            and runtime_settings.web_access_armed
            and provider in {"chatgpt", "claude", "gemini"}
        )
        if can_try_web:
            try:
                target = self.web_helpers.get_helper_target(provider)
                consent_granted = confirm_web_helper_run(
                    provider=provider,
                    helper_url=target.helper_url,
                    text_length=len(selected_text),
                )
                if not consent_granted:
                    fallback_text = self._optimize_with_deepseek_guarded(
                        selected_text=selected_text,
                        provider=provider,
                    )
                    result = OptimizationResult(
                        optimized_text=fallback_text,
                        detected_provider=provider,
                        execution_path="local_fallback",
                        helper_name="deepseek_fallback",
                        helper_latency_ms=0,
                        helper_error_code="consent_denied",
                        helper_error_message="External web helper run denied by user.",
                        active_window_title=active_window_title,
                        consent_required=True,
                        consent_granted=False,
                        consent_denied=True,
                    )
                    self._set_status_from_result(result, runtime_settings.web_access_armed)
                    return result

                web_result = self.web_helpers.optimize(provider, selected_text)
                result = OptimizationResult(
                    optimized_text=web_result.optimized_text,
                    detected_provider=provider,
                    execution_path="web_helper",
                    helper_name=web_result.helper_name,
                    helper_latency_ms=web_result.latency_ms,
                    helper_error_code="",
                    helper_error_message="",
                    active_window_title=active_window_title,
                    consent_required=True,
                    consent_granted=True,
                    consent_denied=False,
                )
                self._set_status_from_result(result, runtime_settings.web_access_armed)
                return result
            except WebHelperError as exc:
                logger.warning("Web helper failed: %s (%s)", exc, exc.code)
                if not self.config.web_helper_fallback_local:
                    result = OptimizationResult(
                        optimized_text="",
                        detected_provider=provider,
                        execution_path="web_helper_failed",
                        helper_name="",
                        helper_latency_ms=0,
                        helper_error_code=exc.code,
                        helper_error_message=str(exc),
                        active_window_title=active_window_title,
                        consent_required=True,
                        consent_granted=True,
                        consent_denied=False,
                    )
                    self._set_status_from_result(result, runtime_settings.web_access_armed)
                    raise

                fallback_text = self._optimize_with_deepseek_guarded(
                    selected_text=selected_text,
                    provider=provider,
                )
                result = OptimizationResult(
                    optimized_text=fallback_text,
                    detected_provider=provider,
                    execution_path="local_fallback",
                    helper_name="deepseek_fallback",
                    helper_latency_ms=0,
                    helper_error_code=exc.code,
                    helper_error_message=str(exc),
                    active_window_title=active_window_title,
                    consent_required=True,
                    consent_granted=True,
                    consent_denied=False,
                )
                self._set_status_from_result(result, runtime_settings.web_access_armed)
                return result

        optimized_text = self._optimize_with_deepseek_guarded(
            selected_text=selected_text,
            provider=provider,
        )
        helper_error_code = ""
        helper_error_message = ""
        if self.config.web_helpers_enabled and not runtime_settings.web_access_armed:
            helper_error_code = "web_access_disarmed"
            helper_error_message = "Web access is disarmed. Local optimization used."
        result = OptimizationResult(
            optimized_text=optimized_text,
            detected_provider=provider,
            execution_path="local_deepseek",
            helper_name="deepseek",
            helper_latency_ms=0,
            helper_error_code=helper_error_code,
            helper_error_message=helper_error_message,
            active_window_title=active_window_title,
            consent_required=False,
            consent_granted=False,
            consent_denied=False,
        )
        self._set_status_from_result(result, runtime_settings.web_access_armed)
        return result

    def _set_status_from_result(
        self,
        result: OptimizationResult,
        web_access_armed: bool,
    ) -> None:
        with self._status_lock:
            helper_error = ""
            if result.helper_error_code or result.helper_error_message:
                helper_error = f"{result.helper_error_code}: {result.helper_error_message}".strip(": ")
            self._status = PipelineStatus(
                last_provider=result.detected_provider,
                last_execution_path=result.execution_path,
                last_helper_name=result.helper_name or "-",
                last_helper_error=helper_error,
                last_helper_latency_ms=result.helper_latency_ms,
                web_access_armed=web_access_armed,
                consent_required=result.consent_required,
                consent_granted=result.consent_granted,
                consent_denied=result.consent_denied,
            )

    def _optimize_with_deepseek_guarded(self, selected_text: str, provider: str) -> str:
        if self.config.require_deepseek_consent:
            allowed = confirm_deepseek_run(len(selected_text))
            if not allowed:
                raise RuntimeError(
                    "DeepSeek consent denied. No external API request was sent."
                )
        return self.deepseek_client.optimize_prompt(selected_text, provider=provider)
