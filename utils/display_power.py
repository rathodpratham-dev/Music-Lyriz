from __future__ import annotations

import ctypes
import sys

ES_CONTINUOUS = 0x80000000
ES_DISPLAY_REQUIRED = 0x00000002
ES_SYSTEM_REQUIRED = 0x00000001


def keep_display_awake() -> None:
    if not sys.platform.startswith("win"):
        return
    ctypes.windll.kernel32.SetThreadExecutionState(
        ES_CONTINUOUS | ES_DISPLAY_REQUIRED | ES_SYSTEM_REQUIRED
    )


def release_display_awake() -> None:
    if not sys.platform.startswith("win"):
        return
    ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
