from __future__ import annotations

from dataclasses import dataclass, replace
from threading import Event
import time

from PySide6.QtCore import QObject, Signal, Slot

from audio.capture import AudioCapture, AudioCaptureError
from audio.levels import rms_level
from recognizer.manager import RecognitionManager
from recognizer.models import SongResult
from recognizer.providers import WindowsMediaSessionProvider
from utils.logging_config import get_logger
from utils.settings import AudioSettings, RecognitionSettings

logger = get_logger(__name__)

INITIAL_RETRY_SECONDS = 1.0
MAX_RETRY_SECONDS = 8.0


@dataclass(frozen=True, slots=True)
class AudioMonitorUpdate:
    active: bool
    level: float
    song: SongResult | None
    recognition_message: str
    message: str


class AudioMonitorWorker(QObject):
    status_changed = Signal(object)
    error_changed = Signal(str)
    finished = Signal()

    def __init__(
        self,
        audio_settings: AudioSettings,
        recognition_settings: RecognitionSettings,
        active_threshold: float = 0.006,
    ) -> None:
        super().__init__()
        self.audio_settings = audio_settings
        self.recognition_settings = recognition_settings
        self.active_threshold = active_threshold
        self._stop_requested = Event()
        self.media_provider = WindowsMediaSessionProvider()
        self.recognition_manager = RecognitionManager([self.media_provider])

    @Slot()
    def run(self) -> None:
        current_song: SongResult | None = None
        next_recognition_at = 0.0
        retry_seconds = INITIAL_RETRY_SECONDS

        try:
            while not self._stop_requested.is_set():
                capture = AudioCapture(self.audio_settings)
                try:
                    capture.start()
                    retry_seconds = INITIAL_RETRY_SECONDS
                    current_song = None
                    next_recognition_at = 0.0
                    self.status_changed.emit(
                        AudioMonitorUpdate(
                            False,
                            0.0,
                            None,
                            "Recognition: waiting",
                            self._device_message("Audio: listening"),
                        )
                    )

                    last_emit = 0.0
                    while not self._stop_requested.is_set():
                        try:
                            frames = capture.read_array()
                        except AudioCaptureError as exc:
                            logger.warning("Audio capture was interrupted; reconnecting", exc_info=True)
                            self._emit_reconnecting_status(exc, retry_seconds)
                            current_song = None
                            next_recognition_at = 0.0
                            break

                        level = rms_level(frames)
                        active = level >= self.active_threshold
                        now = time.monotonic()

                        if active and now >= next_recognition_at:
                            current_song = self.recognition_manager.recognize(b"system-audio-active")
                            next_recognition_at = now + self.recognition_settings.interval_seconds
                        elif active and current_song is not None:
                            position_seconds, duration_seconds = self.media_provider.current_timeline()
                            current_song = replace(
                                current_song,
                                position_seconds=position_seconds,
                                duration_seconds=duration_seconds,
                            )
                        elif not active:
                            current_song = None
                            next_recognition_at = now

                        if now - last_emit >= 0.25:
                            level_percent = min(100, int(level * 1000))
                            if active:
                                message = self._device_message(
                                    f"Audio: system audio detected ({level_percent}%)"
                                )
                            else:
                                message = self._device_message("Audio: waiting for system audio")
                            self.status_changed.emit(
                                AudioMonitorUpdate(
                                    active,
                                    level,
                                    current_song,
                                    self._recognition_message(active, current_song),
                                    message,
                                )
                            )
                            last_emit = now

                except AudioCaptureError as exc:
                    logger.warning("Audio capture could not start; retrying", exc_info=True)
                    self._emit_reconnecting_status(exc, retry_seconds)
                finally:
                    capture.stop()

                if not self._stop_requested.is_set():
                    self._sleep_retry(retry_seconds)
                    retry_seconds = min(MAX_RETRY_SECONDS, retry_seconds * 2)

        except Exception as exc:
            logger.exception("Unexpected audio monitor failure")
            self.error_changed.emit(f"Unexpected audio monitor failure: {exc}")
        finally:
            self.finished.emit()

    def _emit_reconnecting_status(self, error: Exception, retry_seconds: float) -> None:
        self.status_changed.emit(
            AudioMonitorUpdate(
                False,
                0.0,
                None,
                "Recognition: waiting",
                self._device_message(
                    f"Audio: reconnecting in {retry_seconds:.0f}s ({self._friendly_audio_error(error)})"
                )
            )
        )

    def _sleep_retry(self, retry_seconds: float) -> None:
        deadline = time.monotonic() + retry_seconds
        while not self._stop_requested.is_set() and time.monotonic() < deadline:
            time.sleep(0.1)

    @Slot()
    def stop(self) -> None:
        self._stop_requested.set()

    def _recognition_message(self, active: bool, song: SongResult | None) -> str:
        if not active:
            return "Recognition: waiting"
        if song is not None:
            return f"Recognition: {song.artist} - {song.title}"
        if not any(provider.is_available for provider in self.recognition_manager.providers):
            return "Recognition: install winsdk provider"
        return "Recognition: waiting for media metadata"

    def _device_message(self, message: str) -> str:
        if self.audio_settings.device_name:
            return f"{message} [{self.audio_settings.device_name}]"
        return f"{message} [Windows default]"

    def _friendly_audio_error(self, error: Exception) -> str:
        message = str(error)
        if "0x88890004" in message:
            return "audio device changed"
        return message
