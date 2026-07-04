from __future__ import annotations

import json
from pathlib import Path

from lyrics.search import LyricsResult
from recognizer.models import SongResult
from utils.logging_config import get_logger

logger = get_logger(__name__)


class LyricsCache:
    """Small JSON cache boundary for future lyrics metadata."""

    def __init__(self, cache_dir: Path) -> None:
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def song_path(self, song: SongResult) -> Path:
        safe_key = "".join(char if char.isalnum() else "_" for char in song.cache_key)
        return self.cache_dir / f"{safe_key}.json"

    def store_lyrics(
        self,
        song: SongResult,
        lyrics_text: str,
        is_lrc: bool,
        source: str = "unknown",
    ) -> Path:
        path = self.song_path(song)
        payload = {
            "song": {
                "title": song.title,
                "artist": song.artist,
                "album": song.album,
                "confidence": song.confidence,
            },
            "lyrics": lyrics_text,
            "is_lrc": is_lrc,
            "source": source,
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        logger.info("Stored lyrics cache: %s", path)
        return path

    def store_result(self, song: SongResult, result: LyricsResult) -> Path:
        return self.store_lyrics(song, result.text, result.is_lrc, result.source)

    def load_lyrics(self, song: SongResult) -> dict[str, object] | None:
        path = self.song_path(song)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            logger.exception("Could not read lyrics cache: %s", path)
            return None

    def load_result(self, song: SongResult) -> LyricsResult | None:
        payload = self.load_lyrics(song)
        if not payload:
            return None

        lyrics_text = payload.get("lyrics")
        if not isinstance(lyrics_text, str) or not lyrics_text.strip():
            return None

        return LyricsResult(
            text=lyrics_text,
            is_lrc=bool(payload.get("is_lrc")),
            source=str(payload.get("source") or "cache"),
        )
