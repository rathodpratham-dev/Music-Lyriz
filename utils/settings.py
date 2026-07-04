from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields, is_dataclass
import json
from pathlib import Path
from typing import Any, TypeVar, get_type_hints

from utils.paths import CACHE_DIR, CONFIG_DIR, LOGS_DIR

SETTINGS_FILE = CONFIG_DIR / "settings.json"
VALID_ANIMATION_MODES = {"current_glow", "line_by_line"}


@dataclass(slots=True)
class AudioSettings:
    device_name: str | None = None
    sample_rate: int = 44_100
    buffer_size: int = 2048


@dataclass(slots=True)
class RecognitionSettings:
    interval_seconds: int = 15
    min_confidence: float = 0.75
    retry_seconds: int = 20


@dataclass(slots=True)
class UiSettings:
    theme: str = "dark"
    font_size: int = 42
    animation_speed_ms: int = 260
    animation_mode: str = "current_glow"
    always_on_top: bool = False
    transparency: float = 1.0
    window_width: int = 980
    window_height: int = 640


@dataclass(slots=True)
class PathSettings:
    cache_dir: Path = CACHE_DIR
    logs_dir: Path = LOGS_DIR


@dataclass(slots=True)
class AppSettings:
    audio: AudioSettings = field(default_factory=AudioSettings)
    recognition: RecognitionSettings = field(default_factory=RecognitionSettings)
    ui: UiSettings = field(default_factory=UiSettings)
    paths: PathSettings = field(default_factory=PathSettings)


T = TypeVar("T")


def load_settings(path: Path = SETTINGS_FILE) -> AppSettings:
    if not path.exists():
        settings = validate_settings(AppSettings())
        save_settings(settings, path)
        return settings

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        settings = validate_settings(AppSettings())
        save_settings(settings, path)
        return settings

    return validate_settings(_from_dict(AppSettings, payload))


def save_settings(settings: AppSettings, path: Path = SETTINGS_FILE) -> None:
    settings = validate_settings(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_to_jsonable(settings), indent=2), encoding="utf-8")


def validate_settings(settings: AppSettings) -> AppSettings:
    settings.audio.sample_rate = _clamp_int(settings.audio.sample_rate, 8_000, 192_000, 44_100)
    settings.audio.buffer_size = _clamp_int(settings.audio.buffer_size, 256, 16_384, 2048)
    if settings.audio.device_name is not None:
        settings.audio.device_name = str(settings.audio.device_name).strip() or None

    settings.recognition.interval_seconds = _clamp_int(
        settings.recognition.interval_seconds,
        5,
        120,
        15,
    )
    settings.recognition.min_confidence = _clamp_float(
        settings.recognition.min_confidence,
        0.0,
        1.0,
        0.75,
    )
    settings.recognition.retry_seconds = _clamp_int(
        settings.recognition.retry_seconds,
        1,
        300,
        20,
    )

    settings.ui.theme = "dark"
    settings.ui.font_size = _clamp_int(settings.ui.font_size, 18, 72, 42)
    settings.ui.animation_speed_ms = _clamp_int(settings.ui.animation_speed_ms, 50, 1000, 260)
    if settings.ui.animation_mode not in VALID_ANIMATION_MODES:
        settings.ui.animation_mode = "current_glow"
    settings.ui.always_on_top = bool(settings.ui.always_on_top)
    settings.ui.transparency = _clamp_float(settings.ui.transparency, 0.6, 1.0, 1.0)
    settings.ui.window_width = _clamp_int(settings.ui.window_width, 760, 3840, 980)
    settings.ui.window_height = _clamp_int(settings.ui.window_height, 480, 2160, 640)

    if not isinstance(settings.paths.cache_dir, Path):
        settings.paths.cache_dir = Path(settings.paths.cache_dir)
    if not isinstance(settings.paths.logs_dir, Path):
        settings.paths.logs_dir = Path(settings.paths.logs_dir)
    return settings


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return {key: _to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    return value


def _from_dict(model: type[T], payload: dict[str, Any]) -> T:
    if not isinstance(payload, dict):
        return model()

    type_hints = get_type_hints(model)
    values: dict[str, Any] = {}
    for field_info in fields(model):
        field_type = type_hints[field_info.name]
        raw_value = payload.get(field_info.name)
        if raw_value is None:
            continue
        if hasattr(field_type, "__dataclass_fields__"):
            if not isinstance(raw_value, dict):
                continue
            values[field_info.name] = _from_dict(field_type, raw_value)
        elif field_type is Path:
            try:
                values[field_info.name] = Path(raw_value)
            except TypeError:
                continue
        else:
            values[field_info.name] = raw_value
    return model(**values)


def _clamp_int(value: Any, minimum: int, maximum: int, fallback: int) -> int:
    try:
        numeric_value = int(value)
    except (TypeError, ValueError):
        return fallback
    return max(minimum, min(maximum, numeric_value))


def _clamp_float(value: Any, minimum: float, maximum: float, fallback: float) -> float:
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return fallback
    return max(minimum, min(maximum, numeric_value))
