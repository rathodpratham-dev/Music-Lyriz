from __future__ import annotations

from typing import Protocol

from recognizer.models import SongResult


class RecognitionProvider(Protocol):
    """Contract every recognition provider must implement."""

    @property
    def name(self) -> str:
        ...

    @property
    def is_available(self) -> bool:
        ...

    def recognize(self, audio_chunk: bytes) -> SongResult | None:
        ...
