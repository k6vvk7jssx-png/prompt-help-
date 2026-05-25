import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT_DIR / "logs"
LOG_FILE = LOG_DIR / "prompt_optimizer.log"
DATA_DIR = ROOT_DIR / "data"
DATABASE_FILE = DATA_DIR / "prompt_history.sqlite3"
SYSTEM_PROMPT_FILE = DATA_DIR / "system_prompt.md"
RUNTIME_SETTINGS_FILE = DATA_DIR / "runtime_settings.json"
WEB_HELPER_PROFILE_DIR = DATA_DIR / "web_helper_browser_profile"
SINGLE_INSTANCE_HOST = "127.0.0.1"
SINGLE_INSTANCE_PORT = 18765


DEFAULT_HOTKEY = "ctrl+alt+p"
DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEFAULT_DEEPSEEK_MODEL = "deepseek-chat"
DEFAULT_TIMEOUT_SECONDS = 60.0
DEFAULT_COPY_SETTLE_SECONDS = 0.45
DEFAULT_PASTE_SETTLE_SECONDS = 0.1
DEFAULT_DASHBOARD_HOST = "127.0.0.1"
DEFAULT_DASHBOARD_PORT = 8765
DEFAULT_WEB_HELPERS_ENABLED = False
DEFAULT_WEB_HELPER_TIMEOUT_SECONDS = 90
DEFAULT_WEB_HELPER_RETRY_COUNT = 1
DEFAULT_WEB_HELPER_FALLBACK_LOCAL = True
DEFAULT_OPENAI_HELPER_URL = "https://platform.openai.com/chat/edit?models=gpt-5.4-mini&optimize=true"
DEFAULT_CLAUDE_HELPER_URL = "https://claude.ai/public/artifacts/3796db7e-4ef1-4cab-b70c-d045778f23ec"
DEFAULT_GEMINI_HELPER_URL = "https://aistudio.google.com/prompts/new_chat"


@dataclass(frozen=True)
class AppConfig:
    deepseek_api_key: str
    deepseek_base_url: str
    deepseek_model: str
    deepseek_timeout_seconds: float
    hotkey: str
    copy_settle_seconds: float
    paste_settle_seconds: float
    dashboard_host: str
    dashboard_port: int
    web_helpers_enabled: bool
    web_helper_timeout_seconds: int
    web_helper_retry_count: int
    web_helper_fallback_local: bool
    openai_helper_url: str
    claude_helper_url: str
    gemini_helper_url: str


def load_config() -> AppConfig:
    load_dotenv(ROOT_DIR / ".env")

    return AppConfig(
        deepseek_api_key=os.getenv("DEEPSEEK_API_KEY", "").strip(),
        deepseek_base_url=os.getenv(
            "DEEPSEEK_BASE_URL", DEFAULT_DEEPSEEK_BASE_URL
        ).rstrip("/"),
        deepseek_model=os.getenv("DEEPSEEK_MODEL", DEFAULT_DEEPSEEK_MODEL),
        deepseek_timeout_seconds=_float_env(
            "DEEPSEEK_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS
        ),
        hotkey=os.getenv("PROMPT_OPTIMIZER_HOTKEY", DEFAULT_HOTKEY),
        copy_settle_seconds=_float_env(
            "COPY_SETTLE_SECONDS", DEFAULT_COPY_SETTLE_SECONDS
        ),
        paste_settle_seconds=_float_env(
            "PASTE_SETTLE_SECONDS", DEFAULT_PASTE_SETTLE_SECONDS
        ),
        dashboard_host=os.getenv("DASHBOARD_HOST", DEFAULT_DASHBOARD_HOST),
        dashboard_port=_int_env("DASHBOARD_PORT", DEFAULT_DASHBOARD_PORT),
        web_helpers_enabled=_bool_env(
            "WEB_HELPERS_ENABLED", DEFAULT_WEB_HELPERS_ENABLED
        ),
        web_helper_timeout_seconds=_int_env(
            "WEB_HELPER_TIMEOUT_SECONDS", DEFAULT_WEB_HELPER_TIMEOUT_SECONDS
        ),
        web_helper_retry_count=_int_env(
            "WEB_HELPER_RETRY_COUNT", DEFAULT_WEB_HELPER_RETRY_COUNT
        ),
        web_helper_fallback_local=_bool_env(
            "WEB_HELPER_FALLBACK_LOCAL", DEFAULT_WEB_HELPER_FALLBACK_LOCAL
        ),
        openai_helper_url=os.getenv("OPENAI_HELPER_URL", DEFAULT_OPENAI_HELPER_URL),
        claude_helper_url=os.getenv("CLAUDE_HELPER_URL", DEFAULT_CLAUDE_HELPER_URL),
        gemini_helper_url=os.getenv("GEMINI_HELPER_URL", DEFAULT_GEMINI_HELPER_URL),
    )


def _float_env(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value.strip() == "":
        return default

    try:
        return float(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a number, got: {raw_value}") from exc


def _int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value.strip() == "":
        return default

    try:
        return int(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer, got: {raw_value}") from exc


def _bool_env(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value.strip() == "":
        return default

    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False

    raise RuntimeError(
        f"{name} must be a boolean (true/false), got: {raw_value}"
    )
