from __future__ import annotations

from dataclasses import dataclass, field

from recognizer.models import SongResult
from recognizer.providers.base import RecognitionProvider
from utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class RecognitionManager:
    """Runs configured providers and returns the highest-confidence song."""

    providers: list[RecognitionProvider] = field(default_factory=list)

    def add_provider(self, provider: RecognitionProvider) -> None:
        logger.info("Registered recognition provider: %s", provider.name)
        self.providers.append(provider)

    def recognize(self, audio_chunk: bytes) -> SongResult | None:
        if not audio_chunk:
            logger.debug("Skipping recognition because the audio chunk is empty")
            return None

        best_result: SongResult | None = None
        for provider in self.providers:
            if not provider.is_available:
                logger.debug("Skipping unavailable provider: %s", provider.name)
                continue
            try:
                result = provider.recognize(audio_chunk)
            except Exception:
                logger.exception("Recognition provider failed: %s", provider.name)
                continue
            if result is None:
                continue
            if best_result is None or result.confidence > best_result.confidence:
                best_result = result

        return best_result
