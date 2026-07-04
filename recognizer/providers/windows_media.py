from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from recognizer.artwork import fetch_hd_album_art
from recognizer.models import SongResult
from utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class WindowsMediaSessionProvider:
    """Recognize currently playing media from Windows media-session metadata."""

    _current_session: Any | None = None
    _album_art_cache: dict[str, bytes | None] = field(default_factory=dict)

    @property
    def name(self) -> str:
        return "Windows Media Session"

    @property
    def is_available(self) -> bool:
        try:
            from winsdk.windows.media.control import (  # noqa: F401
                GlobalSystemMediaTransportControlsSessionManager,
            )
        except ImportError:
            return False
        return True

    def recognize(self, audio_chunk: bytes) -> SongResult | None:
        if not self.is_available:
            return None

        try:
            return asyncio.run(self._recognize_async())
        except RuntimeError:
            logger.exception("Windows media session recognition could not start its event loop")
        except Exception:
            logger.exception("Windows media session recognition failed")
        return None

    async def _recognize_async(self) -> SongResult | None:
        from winsdk.windows.media.control import (
            GlobalSystemMediaTransportControlsSessionManager as MediaManager,
        )

        manager = await MediaManager.request_async()
        sessions = self._ordered_sessions(manager)

        for session in sessions:
            if not self._is_playing(session):
                continue

            properties = await session.try_get_media_properties_async()
            title = (properties.title or "").strip()
            artist = (properties.artist or "").strip()
            album = (properties.album_title or "").strip() or None
            app_name = self._friendly_app_name(getattr(session, "source_app_user_model_id", ""))

            if not title:
                continue

            self._current_session = session
            position_seconds, duration_seconds = self.current_timeline()
            album_art = await self._album_art_for_song(title, artist, album, properties)
            return SongResult(
                title=title,
                artist=artist or app_name or "Unknown artist",
                album=album,
                confidence=0.92,
                position_seconds=position_seconds,
                duration_seconds=duration_seconds,
                album_art=album_art,
            )

        return None

    def current_timeline(self) -> tuple[float | None, float | None]:
        if self._current_session is None:
            return None, None

        try:
            return self._timeline_for_session(self._current_session)
        except Exception:
            logger.debug("Could not read Windows media timeline", exc_info=True)
            return None, None

    def _ordered_sessions(self, manager: Any) -> list[Any]:
        current_session = manager.get_current_session()
        sessions = []
        if current_session is not None:
            sessions.append(current_session)

        for session in manager.get_sessions():
            if session is not current_session:
                sessions.append(session)

        return sessions

    def _is_playing(self, session: Any) -> bool:
        try:
            playback_info = session.get_playback_info()
            status = playback_info.playback_status
        except Exception:
            return False
        return "PLAYING" in str(status).upper()

    def _timeline_for_session(self, session: Any) -> tuple[float | None, float | None]:
        timeline = session.get_timeline_properties()
        playback_info = session.get_playback_info()

        position = timeline.position.total_seconds()
        duration = timeline.end_time.total_seconds()

        if self._is_playing(session) and timeline.last_updated_time:
            updated_at = timeline.last_updated_time
            if updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=timezone.utc)
            elapsed = (datetime.now(timezone.utc) - updated_at).total_seconds()
            rate = playback_info.playback_rate or 1.0
            position += max(0.0, elapsed) * rate

        if duration > 0:
            position = min(max(position, 0.0), duration)
        else:
            duration = None

        return position, duration

    async def _read_thumbnail(self, properties: Any) -> bytes | None:
        thumbnail = getattr(properties, "thumbnail", None)
        if thumbnail is None:
            return None

        stream = None
        reader = None
        try:
            from winsdk.windows.storage.streams import DataReader

            stream = await thumbnail.open_read_async()
            reader = DataReader(stream.get_input_stream_at(0))
            size = int(stream.size)
            if size <= 0:
                return None
            await reader.load_async(size)
            buffer = bytearray(size)
            reader.read_bytes(buffer)
            return bytes(buffer)
        except Exception:
            logger.debug("Could not read Windows media thumbnail", exc_info=True)
            return None
        finally:
            if reader is not None:
                try:
                    reader.close()
                except Exception:
                    pass
            if stream is not None:
                try:
                    stream.close()
                except Exception:
                    pass

    async def _album_art_for_song(
        self,
        title: str,
        artist: str,
        album: str | None,
        properties: Any,
    ) -> bytes | None:
        cache_key = f"{artist.casefold()}::{title.casefold()}::{(album or '').casefold()}"
        if cache_key in self._album_art_cache:
            return self._album_art_cache[cache_key]

        thumbnail = await self._read_thumbnail(properties)
        hd_art = fetch_hd_album_art(title, artist, album)
        self._album_art_cache[cache_key] = hd_art or thumbnail
        return self._album_art_cache[cache_key]

    def _friendly_app_name(self, app_user_model_id: str) -> str:
        if not app_user_model_id:
            return ""
        return app_user_model_id.split("!")[0].split(".")[-1].strip()
