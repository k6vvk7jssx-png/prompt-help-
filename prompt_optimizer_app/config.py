import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT_DIR / "logs"
LOG_FILE = LOG_DIR / "prompt_optimizer.log"
DATA_DIR = ROOT_DIR / "data"
DATABASE_FILE = DATA_DIR / "prompt_history.sqlite3"
SINGLE_INSTANCE_HOST = "127.0.0.1"
SINGLE_INSTANCE_PORT = 18765


DEFAULT_HOTKEY = "ctrl+alt+p"
DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEFAULT_DEEPSEEK_MODEL = "deepseek-chat"
DEFAULT_TIMEOUT_SECONDS = 60.0
DEFAULT_COPY_SETTLE_SECONDS = 0.25
DEFAULT_PASTE_SETTLE_SECONDS = 0.1
DEFAULT_DASHBOARD_HOST = "127.0.0.1"
DEFAULT_DASHBOARD_PORT = 8765


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
