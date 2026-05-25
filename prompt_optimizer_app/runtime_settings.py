import json
from dataclasses import asdict, dataclass
from pathlib import Path

from prompt_optimizer_app.config import DATA_DIR, RUNTIME_SETTINGS_FILE


@dataclass(frozen=True)
class RuntimeSettings:
    auto_provider_detection: bool = True
    web_access_armed: bool = False


class RuntimeSettingsStore:
    def __init__(self, settings_file: Path = RUNTIME_SETTINGS_FILE):
        self.settings_file = settings_file

    def load(self) -> RuntimeSettings:
        if not self.settings_file.exists():
            return RuntimeSettings()

        try:
            raw = json.loads(self.settings_file.read_text(encoding="utf-8"))
        except Exception:
            return RuntimeSettings()

        return RuntimeSettings(
            auto_provider_detection=_as_bool(
                raw.get("auto_provider_detection", True),
                default=True,
            ),
            web_access_armed=_as_bool(
                raw.get("web_access_armed", False),
                default=False,
            ),
        )

    def save(self, settings: RuntimeSettings) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.settings_file.write_text(
            json.dumps(asdict(settings), indent=2),
            encoding="utf-8",
        )

    def toggle_auto_provider_detection(self) -> RuntimeSettings:
        current = self.load()
        updated = RuntimeSettings(
            auto_provider_detection=not current.auto_provider_detection,
            web_access_armed=current.web_access_armed,
        )
        self.save(updated)
        return updated

    def set_web_access_armed(self, armed: bool) -> RuntimeSettings:
        current = self.load()
        updated = RuntimeSettings(
            auto_provider_detection=current.auto_provider_detection,
            web_access_armed=armed,
        )
        self.save(updated)
        return updated

    def disarm_web_access_on_startup(self) -> RuntimeSettings:
        return self.set_web_access_armed(False)


def _as_bool(value, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return default
