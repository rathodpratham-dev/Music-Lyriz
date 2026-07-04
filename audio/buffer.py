from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from threading import Lock


@dataclass(slots=True)
class AudioBuffer:
    """Thread-safe byte buffer used by future capture and recognition workers."""

    max_chunks: int = 120
    _chunks: deque[bytes] = field(default_factory=deque, init=False, repr=False)
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)

    def push(self, chunk: bytes) -> None:
        with self._lock:
            self._chunks.append(chunk)
            while len(self._chunks) > self.max_chunks:
                self._chunks.popleft()

    def read_latest(self) -> bytes:
        with self._lock:
            if not self._chunks:
                return b""
            return self._chunks[-1]

    def drain(self) -> list[bytes]:
        with self._lock:
            chunks = list(self._chunks)
            self._chunks.clear()
            return chunks

    def clear(self) -> None:
        with self._lock:
            self._chunks.clear()
