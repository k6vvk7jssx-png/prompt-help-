import logging
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from prompt_optimizer_app.config import AppConfig, WEB_HELPER_PROFILE_DIR


logger = logging.getLogger(__name__)
ALLOWED_WEB_HELPER_HOSTS = {
    "platform.openai.com",
    "claude.ai",
    "aistudio.google.com",
}


class WebHelperError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class WebHelperResult:
    optimized_text: str
    helper_name: str
    latency_ms: int


@dataclass(frozen=True)
class WebHelperTarget:
    helper_name: str
    helper_url: str
    helper_domain: str


class WebHelperPipeline:
    def __init__(self, config: AppConfig):
        self.config = config
        self.profile_dir = Path(WEB_HELPER_PROFILE_DIR)

    def optimize(self, provider: str, text: str) -> WebHelperResult:
        if provider == "generic":
            raise WebHelperError("provider_not_supported", "Provider not supported by web helper.")

        target = self.get_helper_target(provider)
        marker_token = uuid.uuid4().hex
        prompt = _build_helper_prompt(text, marker_token)
        attempts = max(1, self.config.web_helper_retry_count + 1)
        last_error: WebHelperError | None = None

        for _ in range(attempts):
            try:
                start = time.perf_counter()
                optimized_text = self._run_playwright(target.helper_url, prompt, marker_token)
                elapsed_ms = int((time.perf_counter() - start) * 1000)
                return WebHelperResult(
                    optimized_text=optimized_text,
                    helper_name=target.helper_name,
                    latency_ms=elapsed_ms,
                )
            except WebHelperError as exc:
                logger.warning("Web helper attempt failed (%s): %s", exc.code, exc)
                last_error = exc

        if last_error is None:
            raise WebHelperError("unknown", "Unknown web helper failure.")
        raise last_error

    def get_helper_target(self, provider: str) -> WebHelperTarget:
        if provider == "chatgpt":
            return self._validated_target("openai_helper", self.config.openai_helper_url)
        if provider == "claude":
            return self._validated_target("claude_helper", self.config.claude_helper_url)
        if provider == "gemini":
            return self._validated_target("gemini_ai_studio", self.config.gemini_helper_url)
        raise WebHelperError("provider_not_supported", f"Unsupported provider: {provider}")

    def _validated_target(self, helper_name: str, helper_url: str) -> WebHelperTarget:
        parsed = urlparse(helper_url)
        domain = (parsed.netloc or "").lower()
        if domain not in ALLOWED_WEB_HELPER_HOSTS:
            raise WebHelperError(
                "blocked_domain",
                f"Blocked helper domain: {domain or 'unknown'}",
            )
        return WebHelperTarget(
            helper_name=helper_name,
            helper_url=helper_url,
            helper_domain=domain,
        )

    def _run_playwright(self, helper_url: str, prompt: str, marker_token: str) -> str:
        try:
            from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
            from playwright.sync_api import sync_playwright
        except Exception as exc:
            raise WebHelperError(
                "playwright_missing",
                "Playwright is not installed. Run: pip install playwright && playwright install chromium",
            ) from exc

        timeout_ms = int(self.config.web_helper_timeout_seconds * 1000)
        self.profile_dir.mkdir(parents=True, exist_ok=True)

        with sync_playwright() as playwright:
            context = playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.profile_dir),
                headless=False,
            )
            try:
                page = context.pages[0] if context.pages else context.new_page()
                page.goto(helper_url, wait_until="domcontentloaded", timeout=timeout_ms)
                page.wait_for_timeout(1500)

                input_locator = _find_input_locator(page)
                if input_locator is None:
                    body_text = page.inner_text("body")[:1000].lower()
                    if "log in" in body_text or "sign in" in body_text:
                        raise WebHelperError("not_logged_in", "You must be logged in to use this helper.")
                    raise WebHelperError("selector_not_found", "Could not find prompt input on helper page.")

                input_locator.click()
                page.keyboard.press("Control+A")
                page.keyboard.type(prompt, delay=1)
                page.keyboard.press("Enter")

                deadline = time.time() + self.config.web_helper_timeout_seconds
                while time.time() < deadline:
                    try:
                        body = page.inner_text("body")
                    except PlaywrightTimeoutError:
                        body = ""
                    parsed = _extract_marked_output(body, marker_token)
                    if parsed:
                        return parsed
                    page.wait_for_timeout(1000)

                raise WebHelperError(
                    "timeout",
                    "Timed out waiting for helper output markers.",
                )
            finally:
                context.close()


def _find_input_locator(page):
    selectors = [
        "textarea",
        "#prompt-textarea",
        "[contenteditable='true']",
        "div[role='textbox']",
    ]
    for selector in selectors:
        locator = page.locator(selector)
        if locator.count() > 0:
            return locator.first
    return None


def _build_helper_prompt(raw_prompt: str, marker_token: str) -> str:
    begin_marker = _begin_marker(marker_token)
    end_marker = _end_marker(marker_token)
    return (
        "You are a senior prompt engineering assistant.\n"
        "Rewrite and optimize the following rough prompt.\n"
        "Return only the optimized prompt in Markdown.\n"
        "Do not add explanation.\n"
        f"Output strictly between these markers:\n{begin_marker}\n...\n{end_marker}\n\n"
        f"Input prompt:\n{raw_prompt}"
    )


def _extract_marked_output(body_text: str, marker_token: str) -> str:
    begin_marker = _begin_marker(marker_token)
    end_marker = _end_marker(marker_token)
    start = body_text.rfind(begin_marker)
    if start < 0:
        return ""
    end = body_text.find(end_marker, start + len(begin_marker))
    if end < 0:
        return ""
    content = body_text[start + len(begin_marker) : end].strip()
    if content in {"", "..."}:
        return ""
    return content


def _begin_marker(marker_token: str) -> str:
    return f"BEGIN_OPTIMIZED_PROMPT_{marker_token}"


def _end_marker(marker_token: str) -> str:
    return f"END_OPTIMIZED_PROMPT_{marker_token}"
