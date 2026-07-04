from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from utils.logging_config import get_logger

logger = get_logger(__name__)

DEFAULT_SYSTEM_OUTPUT_LABEL = "Default system output (Windows setting)"


@dataclass(frozen=True, slots=True)
class AudioDeviceChoice:
    label: str
    device_name: str | None
    is_default: bool = False


def list_system_audio_devices(soundcard_module: Any | None = None) -> list[AudioDeviceChoice]:
    choices = [AudioDeviceChoice(DEFAULT_SYSTEM_OUTPUT_LABEL, None, True)]

    try:
        soundcard = soundcard_module or _import_soundcard()
        default_speaker_name = _device_name(soundcard.default_speaker())
        loopback_devices = [
            device
            for device in soundcard.all_microphones(include_loopback=True)
            if getattr(device, "isloopback", False)
        ]
    except Exception as exc:
        logger.warning("Could not list Windows system audio devices: %s", exc)
        return choices

    if default_speaker_name:
        choices[0] = AudioDeviceChoice(
            f"Default system output ({default_speaker_name})",
            None,
            True,
        )

    seen_names: set[str] = set()
    for device in loopback_devices:
        name = _device_name(device)
        if not name:
            continue

        normalized_name = name.casefold()
        if normalized_name in seen_names:
            continue
        seen_names.add(normalized_name)

        label = name
        if default_speaker_name and _names_match(default_speaker_name, name):
            label = f"{name} (current Windows default)"
        choices.append(AudioDeviceChoice(label, name))

    return choices


def _import_soundcard() -> Any:
    import soundcard

    return soundcard


def _device_name(device: Any) -> str:
    return str(getattr(device, "name", "") or "").strip()


def _names_match(first: str, second: str) -> bool:
    normalized_first = first.casefold()
    normalized_second = second.casefold()
    return (
        normalized_first == normalized_second
        or normalized_first in normalized_second
        or normalized_second in normalized_first
    )
