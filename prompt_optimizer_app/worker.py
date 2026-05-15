import logging
import threading
import time
import uuid
from typing import Callable

import pyautogui
import pyperclip

from prompt_optimizer_app.config import AppConfig
from prompt_optimizer_app.deepseek import DeepSeekClient
from prompt_optimizer_app.storage import PromptHistoryStore


logger = logging.getLogger(__name__)


class PromptOptimizerWorker:
    def __init__(
        self,
        config: AppConfig,
        client: DeepSeekClient,
        history_store: PromptHistoryStore,
        on_status: Callable[[str], None] | None = None,
    ):
        self.config = config
        self.client = client
        self.history_store = history_store
        self.on_status = on_status or (lambda message: None)
        self._lock = threading.Lock()

    def run_once(self, paste_result: bool = True) -> None:
        if not self._lock.acquire(blocking=False):
            self._report("Already optimizing; ignoring repeated hotkey.")
            return

        original_clipboard = ""
        try:
            original_clipboard = pyperclip.paste()

            copy_marker = f"__PROMPT_OPTIMIZER_COPY_MARKER_{uuid.uuid4()}__"
            pyperclip.copy(copy_marker)
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

            self._report("Optimizing selected text with DeepSeek...")
            optimized = self.client.optimize_prompt(selected_text)
            self.history_store.add_success(
                source="hotkey",
                original_text=selected_text,
                optimized_text=optimized,
            )

            pyperclip.copy(optimized)
            if paste_result:
                time.sleep(self.config.paste_settle_seconds)
                pyautogui.hotkey("ctrl", "v")
                self._report("Optimized prompt pasted.")
            else:
                self._report("Optimized prompt copied to clipboard.")
        except Exception as exc:
            self.history_store.add_error(
                source="hotkey",
                original_text=selected_text if "selected_text" in locals() else "",
                error_message=str(exc),
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

            self._report("Optimizing clipboard text with DeepSeek...")
            optimized = self.client.optimize_prompt(original_clipboard)
            self.history_store.add_success(
                source="clipboard_test",
                original_text=original_clipboard,
                optimized_text=optimized,
            )
            pyperclip.copy(optimized)
            self._report("Optimized prompt copied to clipboard.")
        except Exception as exc:
            self.history_store.add_error(
                source="clipboard_test",
                original_text=original_clipboard,
                error_message=str(exc),
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
