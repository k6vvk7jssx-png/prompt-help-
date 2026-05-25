import ctypes
from urllib.parse import urlparse


IDYES = 6
MB_YESNO = 0x00000004
MB_ICONWARNING = 0x00000030
MB_TOPMOST = 0x00040000
MB_SETFOREGROUND = 0x00010000


def confirm_web_helper_run(provider: str, helper_url: str, text_length: int) -> bool:
    parsed = urlparse(helper_url)
    domain = parsed.netloc or "unknown-domain"
    message = (
        "External account access requested.\n\n"
        f"Provider: {provider}\n"
        f"Target domain: {domain}\n"
        f"Prompt length: {text_length} chars\n"
        "Planned path: web helper\n\n"
        "Allow this single run?"
    )
    title = "Prompt Optimizer - Confirm External Run"
    flags = MB_YESNO | MB_ICONWARNING | MB_TOPMOST | MB_SETFOREGROUND

    try:
        result = ctypes.windll.user32.MessageBoxW(None, message, title, flags)
    except Exception:
        return False
    return result == IDYES


def confirm_deepseek_run(text_length: int) -> bool:
    message = (
        "External API access requested.\n\n"
        "Provider: DeepSeek API\n"
        f"Prompt length: {text_length} chars\n"
        "Planned path: local API fallback\n\n"
        "Allow this single run?"
    )
    title = "Prompt Optimizer - Confirm DeepSeek Run"
    flags = MB_YESNO | MB_ICONWARNING | MB_TOPMOST | MB_SETFOREGROUND

    try:
        result = ctypes.windll.user32.MessageBoxW(None, message, title, flags)
    except Exception:
        return False
    return result == IDYES
