from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass

from lyrics.parser import LyricLine


@dataclass(frozen=True, slots=True)
class SyncState:
    previous_line: LyricLine | None
    current_line: LyricLine | None
    next_line: LyricLine | None


class LyricsSynchronizer:
    """Maps playback time to previous, current, and next lyric lines."""

    def __init__(self, lines: list[LyricLine] | None = None) -> None:
        self.set_lines(lines or [])

    def set_lines(self, lines: list[LyricLine]) -> None:
        self._lines = sorted(lines, key=lambda line: line.timestamp)
        self._timestamps = [line.timestamp for line in self._lines]

    def state_at(self, playback_seconds: float) -> SyncState:
        if not self._lines:
            return SyncState(None, None, None)

        index = self.current_index_at(playback_seconds)
        if index is None:
            return SyncState(None, None, self._lines[0])

        previous_line = self._lines[index - 1] if index > 0 else None
        current_line = self._lines[index]
        next_line = self._lines[index + 1] if index + 1 < len(self._lines) else None
        return SyncState(previous_line, current_line, next_line)

    def current_index_at(self, playback_seconds: float) -> int | None:
        if not self._lines:
            return None

        index = bisect_right(self._timestamps, playback_seconds) - 1
        if index < 0:
            return None
        return index
