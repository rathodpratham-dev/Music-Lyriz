from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SongResult:
    title: str
    artist: str
    album: str | None = None
    confidence: float = 0.0
    position_seconds: float | None = None
    duration_seconds: float | None = None
    album_art: bytes | None = None

    @property
    def cache_key(self) -> str:
        title = self.title.strip().casefold()
        artist = self.artist.strip().casefold()
        return f"{artist}::{title}"
