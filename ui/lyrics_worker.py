from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from lyrics.cache import LyricsCache
from lyrics.search import LyricsResult, LyricsSearch
from recognizer.models import SongResult
from utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class LyricsLookupResult:
    song: SongResult
    lyrics: LyricsResult | None
    from_cache: bool


class LyricsLookupWorker(QObject):
    result_ready = Signal(object)
    error_changed = Signal(str)
    finished = Signal()

    def __init__(self, song: SongResult, cache_dir: Path) -> None:
        super().__init__()
        self.song = song
        self.cache_dir = cache_dir

    @Slot()
    def run(self) -> None:
        try:
            cache = LyricsCache(self.cache_dir)
            cached_result = cache.load_result(self.song)
            if cached_result is not None:
                self.result_ready.emit(LyricsLookupResult(self.song, cached_result, True))
                return

            result = LyricsSearch().search(self.song)
            if result is not None:
                cache.store_result(self.song, result)

            self.result_ready.emit(LyricsLookupResult(self.song, result, False))
        except Exception as exc:
            logger.exception("Lyrics lookup worker failed")
            self.error_changed.emit(str(exc))
        finally:
            self.finished.emit()
