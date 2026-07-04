from __future__ import annotations

import asyncio

from utils.logging_config import get_logger

logger = get_logger(__name__)


class WindowsMediaControls:
    def previous(self) -> bool:
        return self._run_command("previous")

    def play_pause(self) -> bool:
        return self._run_command("play_pause")

    def next(self) -> bool:
        return self._run_command("next")

    def _run_command(self, command: str) -> bool:
        try:
            return asyncio.run(self._run_command_async(command))
        except Exception:
            logger.exception("Windows media control failed: %s", command)
            return False

    async def _run_command_async(self, command: str) -> bool:
        from winsdk.windows.media.control import (
            GlobalSystemMediaTransportControlsSessionManager as MediaManager,
        )

        manager = await MediaManager.request_async()
        session = manager.get_current_session()
        if session is None:
            return False

        if command == "previous":
            return bool(await session.try_skip_previous_async())
        if command == "play_pause":
            return bool(await session.try_toggle_play_pause_async())
        if command == "next":
            return bool(await session.try_skip_next_async())
        return False
