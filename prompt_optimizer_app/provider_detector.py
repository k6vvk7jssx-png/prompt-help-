import ctypes
from dataclasses import dataclass


SUPPORTED_PROVIDERS = {"chatgpt", "claude", "gemini", "generic"}


@dataclass(frozen=True)
class ProviderDetection:
    provider: str
    active_window_title: str


def detect_provider(auto_detection_enabled: bool = True) -> ProviderDetection:
    title = get_active_window_title()
    if not auto_detection_enabled:
        return ProviderDetection(provider="generic", active_window_title=title)
    return ProviderDetection(provider=_provider_from_title(title), active_window_title=title)


def get_active_window_title() -> str:
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return ""
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return ""
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        return buffer.value.strip()
    except Exception:
        return ""


def _provider_from_title(title: str) -> str:
    lower = title.lower()
    if "chatgpt" in lower or "openai" in lower:
        return "chatgpt"
    if "claude" in lower or "anthropic" in lower:
        return "claude"
    if "gemini" in lower or "ai studio" in lower:
        return "gemini"
    return "generic"
