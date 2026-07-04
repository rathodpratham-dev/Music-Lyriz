"""Recognition provider implementations."""

from recognizer.providers.base import RecognitionProvider
from recognizer.providers.windows_media import WindowsMediaSessionProvider

__all__ = ["RecognitionProvider", "WindowsMediaSessionProvider"]
