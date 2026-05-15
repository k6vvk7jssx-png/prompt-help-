import logging

import keyboard


logger = logging.getLogger(__name__)


class HotkeyController:
    def __init__(self, hotkey: str, callback):
        self.hotkey = hotkey
        self.callback = callback
        self._handle = None

    @property
    def is_running(self) -> bool:
        return self._handle is not None

    def start(self) -> None:
        if self.is_running:
            return

        self._handle = keyboard.add_hotkey(self.hotkey, self.callback, suppress=False)
        logger.info("Hotkey registered: %s", self.hotkey)

    def stop(self) -> None:
        if not self.is_running:
            return

        keyboard.remove_hotkey(self._handle)
        self._handle = None
        logger.info("Hotkey stopped: %s", self.hotkey)

    def reload(self, hotkey: str, callback) -> None:
        was_running = self.is_running
        self.stop()
        self.hotkey = hotkey
        self.callback = callback
        if was_running:
            self.start()

