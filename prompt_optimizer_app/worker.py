import logging
import threading
import time
import uuid
from typing import Callable

import pyautogui
import pyperclip

from prompt_optimizer_app.config import AppConfig
from prompt_optimizer_app.optimization_router import OptimizationRouter
from prompt_optimizer_app.storage import PromptHistoryStore


logger = logging.getLogger(__name__)


HOTKEY_KEYS_TO_RELEASE = ("ctrl", "alt", "shift", "win", "p")


class PromptOptimizerWorker:
    def __init__(
        self,
        config: AppConfig,
        optimization_router: OptimizationRouter,
        history_store: PromptHistoryStore,
        on_status: Callable[[str], None] | None = None,
    ):
        self.config = config
        self.optimization_router = optimization_router
        self.history_store = history_store
        self.on_status = on_status or (lambda message: None)
        self._lock = threading.Lock()

    def run_once(self, paste_result: bool = True) -> None:
        if not self._lock.acquire(blocking=False):
            self._report("Already optimizing; ignoring repeated hotkey.")
            return

        original_clipboard = ""
        try:
            self._report("Hotkey triggered. Reading selected text...")
            original_clipboard = pyperclip.paste()

            copy_marker = f"__PROMPT_OPTIMIZER_COPY_MARKER_{uuid.uuid4()}__"
            pyperclip.copy(copy_marker)
            self._release_hotkey_keys()
            pyautogui.hotkey("ctrl", "c")
            time.sleep(self.config.copy_settle_seconds)
            selected_text = pyperclip.paste()

            if selected_text == copy_marker or not selected_text or not selected_text.strip():
                pyperclip.copy(original_clipboard)
                self.history_store.add_error(
                    source="hotkey",
                    original_text="",
                    error_message="No selected text found.",
                )
                self._report("No selected text found. Select text first, then try again.")
                return

            self._report("Optimizing selected text...")
            result = self.optimization_router.optimize(selected_text)
            optimized = result.optimized_text
            self.history_store.add_success(
                source=result.execution_path if result.execution_path else "hotkey",
                original_text=selected_text,
                optimized_text=optimized,
                detected_provider=result.detected_provider,
                execution_path=result.execution_path,
                helper_name=result.helper_name,
                helper_latency_ms=result.helper_latency_ms,
                active_window_title=result.active_window_title,
                consent_required=result.consent_required,
                consent_granted=result.consent_granted,
                consent_denied=result.consent_denied,
            )

            pyperclip.copy(optimized)
            if paste_result:
                time.sleep(self.config.paste_settle_seconds)
                pyautogui.hotkey("ctrl", "v")
                self._report(
                    f"Optimized prompt pasted ({result.detected_provider} via {result.execution_path})."
                )
            else:
                self._report("Optimized prompt copied to clipboard.")
        except Exception as exc:
            self.history_store.add_error(
                source="hotkey",
                original_text=selected_text if "selected_text" in locals() else "",
                error_message=str(exc),
                detected_provider=self.optimization_router.status.last_provider,
                execution_path=self.optimization_router.status.last_execution_path,
                helper_name=self.optimization_router.status.last_helper_name,
                consent_required=self.optimization_router.status.consent_required,
                consent_granted=self.optimization_router.status.consent_granted,
                consent_denied=self.optimization_router.status.consent_denied,
            )
            self._report(f"Optimization failed: {exc}", exc_info=True)
            try:
                pyperclip.copy(original_clipboard)
            except Exception:
                logger.exception("Failed to restore clipboard after optimization error.")
        finally:
            self._lock.release()

    def optimize_clipboard(self) -> None:
        if not self._lock.acquire(blocking=False):
            self._report("Already optimizing; ignoring repeated request.")
            return

        original_clipboard = ""
        try:
            original_clipboard = pyperclip.paste()
            if not original_clipboard or not original_clipboard.strip():
                self.history_store.add_error(
                    source="clipboard_test",
                    original_text="",
                    error_message="Clipboard is empty.",
                )
                self._report("Clipboard is empty. Copy text first, then run the test.")
                return

            self._report("Optimizing clipboard text...")
            result = self.optimization_router.optimize(original_clipboard)
            optimized = result.optimized_text
            self.history_store.add_success(
                source=f"clipboard_test_{result.execution_path}",
                original_text=original_clipboard,
                optimized_text=optimized,
                detected_provider=result.detected_provider,
                execution_path=result.execution_path,
                helper_name=result.helper_name,
                helper_latency_ms=result.helper_latency_ms,
                active_window_title=result.active_window_title,
                consent_required=result.consent_required,
                consent_granted=result.consent_granted,
                consent_denied=result.consent_denied,
            )
            pyperclip.copy(optimized)
            self._report("Optimized prompt copied to clipboard.")
        except Exception as exc:
            self.history_store.add_error(
                source="clipboard_test",
                original_text=original_clipboard,
                error_message=str(exc),
                detected_provider=self.optimization_router.status.last_provider,
                execution_path=self.optimization_router.status.last_execution_path,
                helper_name=self.optimization_router.status.last_helper_name,
                consent_required=self.optimization_router.status.consent_required,
                consent_granted=self.optimization_router.status.consent_granted,
                consent_denied=self.optimization_router.status.consent_denied,
            )
            self._report(f"Clipboard optimization failed: {exc}", exc_info=True)
            try:
                pyperclip.copy(original_clipboard)
            except Exception:
                logger.exception("Failed to restore clipboard after test error.")
        finally:
            self._lock.release()

    def _report(self, message: str, exc_info: bool = False) -> None:
        if exc_info:
            logger.exception(message)
        else:
            logger.info(message)
        self.on_status(message)

    @staticmethod
    def _release_hotkey_keys() -> None:
        for key in HOTKEY_KEYS_TO_RELEASE:
            try:
                pyautogui.keyUp(key)
            except Exception:
                logger.debug("Failed to release key: %s", key, exc_info=True)
        time.sleep(0.15)
