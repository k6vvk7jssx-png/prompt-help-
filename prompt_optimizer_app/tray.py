import logging
import os
import subprocess
import threading

import pystray
from PIL import Image, ImageDraw

from prompt_optimizer_app.config import LOG_FILE, AppConfig, load_config
from prompt_optimizer_app.dashboard import DashboardServer
from prompt_optimizer_app.deepseek import DeepSeekClient
from prompt_optimizer_app.hotkeys import HotkeyController
from prompt_optimizer_app.storage import PromptHistoryStore
from prompt_optimizer_app.worker import PromptOptimizerWorker


logger = logging.getLogger(__name__)


class PromptOptimizerTrayApp:
    def __init__(self, config: AppConfig):
        self.config = config
        self.status = "Starting..."
        self.client = DeepSeekClient(config)
        self.history_store = PromptHistoryStore()
        self.worker = PromptOptimizerWorker(
            config,
            self.client,
            self.history_store,
            self.set_status,
        )
        self.hotkeys = HotkeyController(config.hotkey, self.run_worker_thread)
        self.dashboard = DashboardServer(
            config,
            self.history_store,
            self.hotkeys,
            self.set_status,
        )
        self.icon = pystray.Icon(
            "prompt-optimizer",
            icon=_create_icon(),
            title="Prompt Optimizer",
            menu=self._build_menu(),
        )

    def run(self) -> None:
        try:
            self.hotkeys.start()
            self.set_status(f"Running. Hotkey: {self.config.hotkey}")
        except Exception as exc:
            self.set_status(f"Hotkey failed: {exc}")
            logger.exception("Failed to register hotkey.")

        logger.info("Prompt Optimizer tray app started.")
        self.icon.run()

    def run_worker_thread(self) -> None:
        threading.Thread(target=self.worker.run_once, daemon=True).start()

    def test_clipboard_optimization(self, _icon=None, _item=None) -> None:
        threading.Thread(
            target=self.worker.optimize_clipboard,
            daemon=True,
        ).start()

    def toggle_hotkey(self, _icon=None, _item=None) -> None:
        try:
            if self.hotkeys.is_running:
                self.hotkeys.stop()
                self.set_status("Hotkey stopped.")
            else:
                self.hotkeys.start()
                self.set_status(f"Hotkey running: {self.config.hotkey}")
        except Exception as exc:
            self.set_status(f"Hotkey toggle failed: {exc}")
            logger.exception("Failed to toggle hotkey.")
        finally:
            self.icon.update_menu()

    def open_logs(self, _icon=None, _item=None) -> None:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        LOG_FILE.touch(exist_ok=True)
        try:
            os.startfile(LOG_FILE)
        except OSError:
            subprocess.Popen(["notepad.exe", str(LOG_FILE)])

    def open_dashboard(self, _icon=None, _item=None) -> None:
        try:
            self.dashboard.open()
            self.set_status(f"Dashboard open: {self.dashboard.url}")
        except Exception as exc:
            self.set_status(f"Dashboard failed: {exc}")
            logger.exception("Failed to open dashboard.")

    def reload_config(self, _icon=None, _item=None) -> None:
        try:
            new_config = load_config()
            self.config = new_config
            self.client.config = new_config
            self.worker.config = new_config
            self.dashboard.update_config(new_config)
            self.hotkeys.reload(new_config.hotkey, self.run_worker_thread)
            self.set_status(f"Config reloaded. Hotkey: {new_config.hotkey}")
            logger.info("Config reloaded.")
        except Exception as exc:
            self.set_status(f"Reload failed: {exc}")
            logger.exception("Failed to reload config.")
        finally:
            self.icon.update_menu()

    def quit(self, _icon=None, _item=None) -> None:
        self.hotkeys.stop()
        logger.info("Prompt Optimizer tray app stopped.")
        self.icon.stop()

    def set_status(self, message: str) -> None:
        self.status = message
        logger.info("Status: %s", message)

    def _build_menu(self):
        return pystray.Menu(
            pystray.MenuItem(lambda _item: self.status, None, enabled=False),
            pystray.MenuItem(
                lambda _item: "Stop hotkey"
                if self.hotkeys.is_running
                else "Start hotkey",
                self.toggle_hotkey,
            ),
            pystray.MenuItem(
                "Test clipboard optimization",
                self.test_clipboard_optimization,
            ),
            pystray.MenuItem("Open dashboard", self.open_dashboard),
            pystray.MenuItem("Open logs", self.open_logs),
            pystray.MenuItem("Reload config", self.reload_config),
            pystray.MenuItem("Quit", self.quit),
        )


def _create_icon() -> Image.Image:
    image = Image.new("RGB", (64, 64), "#1f2937")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((8, 8, 56, 56), radius=10, fill="#2563eb")
    draw.line((20, 24, 44, 24), fill="white", width=5)
    draw.line((20, 34, 38, 34), fill="white", width=5)
    draw.line((20, 44, 48, 44), fill="white", width=5)
    return image
