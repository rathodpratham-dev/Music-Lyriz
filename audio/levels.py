from __future__ import annotations

from typing import Any


def rms_level(frames: Any) -> float:
    """Return normalized RMS level for a NumPy-like audio frame array."""

    if frames is None:
        return 0.0

    try:
        import numpy as np
    except ImportError:
        return 0.0

    if len(frames) == 0:
        return 0.0

    samples = np.asarray(frames, dtype="float32")
    if samples.size == 0:
        return 0.0

    return float(np.sqrt(np.mean(np.square(samples))))
