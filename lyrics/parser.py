from __future__ import annotations

from dataclasses import dataclass
import re

TIMESTAMP_PATTERN = re.compile(r"\[(?P<minutes>\d{1,2}):(?P<seconds>\d{2})(?:\.(?P<fraction>\d{1,3}))?\]")


@dataclass(frozen=True, slots=True)
class LyricLine:
    timestamp: float
    text: str


def parse_lrc(lrc_text: str) -> list[LyricLine]:
    """Parse standard and repeated-timestamp LRC text into sorted lyric lines."""

    lines: list[LyricLine] = []
    for raw_line in lrc_text.splitlines():
        matches = list(TIMESTAMP_PATTERN.finditer(raw_line))
        if not matches:
            continue

        text = TIMESTAMP_PATTERN.sub("", raw_line).strip()
        for match in matches:
            minutes = int(match.group("minutes"))
            seconds = int(match.group("seconds"))
            fraction_text = match.group("fraction") or "0"
            fraction = int(fraction_text.ljust(3, "0")[:3]) / 1000
            lines.append(LyricLine(timestamp=(minutes * 60) + seconds + fraction, text=text))

    return sorted(lines, key=lambda line: line.timestamp)
