from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
import warnings

from utils.logging_config import get_logger
from utils.settings import AudioSettings

logger = get_logger(__name__)


class AudioCaptureError(RuntimeError):
    """Raised when system audio capture cannot start or continue."""


@dataclass(slots=True)
class AudioCapture:
    """Capture Windows system audio from the default speaker loopback."""

    settings: AudioSettings
    _running: bool = False
    _loopback_device: Any | None = None
    _recorder_context: Any | None = None
    _recorder: Any | None = None

    def start(self) -> None:
        if self._running:
            return

        try:
            import soundcard as sc
        except ImportError as exc:
            raise AudioCaptureError(
                "The soundcard package is required for WASAPI loopback capture."
            ) from exc

        try:
            self._loopback_device = self._find_loopback_device(sc)
            self._recorder_context = self._loopback_device.recorder(
                samplerate=self.settings.sample_rate,
                channels=2,
                blocksize=self.settings.buffer_size,
            )
            self._recorder = self._recorder_context.__enter__()
        except Exception as exc:
            self._cleanup_recorder()
            raise AudioCaptureError(f"Could not start system audio capture: {exc}") from exc

        logger.info("Audio capture started from speaker loopback: %s", self._loopback_device)
        self._running = True

    def read(self) -> bytes:
        frames = self.read_array()
        if frames is None:
            return b""

        try:
            import numpy as np
        except ImportError as exc:
            raise AudioCaptureError("The numpy package is required for audio conversion.") from exc

        pcm = np.clip(frames, -1.0, 1.0)
        pcm = (pcm * 32767).astype("<i2")
        return pcm.tobytes()

    def read_array(self) -> Any | None:
        if not self._running:
            return None
        if self._recorder is None:
            raise AudioCaptureError("Audio capture is running without a recorder.")

        try:
            with warnings.catch_warnings():
                try:
                    from soundcard import SoundcardRuntimeWarning

                    warnings.simplefilter("ignore", SoundcardRuntimeWarning)
                except ImportError:
                    pass
                return self._recorder.record(numframes=self.settings.buffer_size)
        except Exception as exc:
            raise AudioCaptureError(f"Could not read system audio: {exc}") from exc

    def stop(self) -> None:
        if self._running:
            logger.info("Audio capture stopped")
        self._running = False
        self._cleanup_recorder()

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def selected_device(self) -> Optional[str]:
        return self.settings.device_name

    def _find_loopback_device(self, soundcard_module: Any) -> Any:
        default_speaker = soundcard_module.default_speaker()
        loopback_devices = [
            device
            for device in soundcard_module.all_microphones(include_loopback=True)
            if getattr(device, "isloopback", False)
        ]
        if not loopback_devices:
            raise AudioCaptureError("No Windows speaker loopback device was found.")

        if not self.settings.device_name:
            return self._match_loopback(default_speaker.name, loopback_devices) or loopback_devices[0]

        normalized_name = self.settings.device_name.casefold()
        for device in loopback_devices:
            normalized_device_name = device.name.casefold()
            if normalized_name in normalized_device_name or normalized_device_name in normalized_name:
                return device

        logger.warning(
            "Configured audio device %r was not found; using default speaker.",
            self.settings.device_name,
        )
        return self._match_loopback(default_speaker.name, loopback_devices) or loopback_devices[0]

    def _match_loopback(self, speaker_name: str, loopback_devices: list[Any]) -> Any | None:
        normalized_speaker = speaker_name.casefold()
        for device in loopback_devices:
            if device.name.casefold() == normalized_speaker:
                return device
        for device in loopback_devices:
            if device.name.casefold() in normalized_speaker or normalized_speaker in device.name.casefold():
                return device
        return None

    def _cleanup_recorder(self) -> None:
        if self._recorder_context is None:
            self._recorder = None
            return

        try:
            self._recorder_context.__exit__(None, None, None)
        except Exception:
            logger.exception("Could not close audio recorder cleanly")
        finally:
            self._recorder_context = None
            self._recorder = None
