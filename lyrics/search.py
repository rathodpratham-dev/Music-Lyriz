from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from html import unescape
from html.parser import HTMLParser
import re
from typing import Any
from urllib.parse import urljoin

from recognizer.models import SongResult
from utils.logging_config import get_logger

logger = get_logger(__name__)

GENIUS_BASE_URL = "https://genius.com"
GENIUS_SEARCH_URL = "https://genius.com/api/search/multi"
LRCLIB_BASE_URL = "https://lrclib.net/api"
USER_AGENT = "MusicLyriz/0.1"


@dataclass(frozen=True, slots=True)
class LyricsResult:
    text: str
    is_lrc: bool
    source: str


class LyricsSearch:
    """Search LRCLIB for synced LRC first, then Genius for plain lyrics."""

    def __init__(self, request_get: Any | None = None) -> None:
        self._request_get = request_get

    def search(self, song: SongResult) -> LyricsResult | None:
        logger.info("Lyrics lookup requested for %s - %s", song.artist, song.title)
        try:
            exact_result = self._get_exact(song)
            if exact_result is not None:
                return exact_result

            best_match = self._search_best_match(song)
            if best_match is not None:
                return best_match
        except Exception:
            logger.exception("LRCLIB lookup failed for %s - %s", song.artist, song.title)

        try:
            return self._search_genius(song)
        except Exception:
            logger.exception("Genius lookup failed for %s - %s", song.artist, song.title)
            return None

    def _get_exact(self, song: SongResult) -> LyricsResult | None:
        response = self._request(
            "get",
            {
                "track_name": song.title,
                "artist_name": song.artist,
            },
        )
        if not isinstance(response, dict):
            return None
        return self._result_from_record(response)

    def _search_best_match(self, song: SongResult) -> LyricsResult | None:
        response = self._request("search", {"q": f"{song.artist} {song.title}"})
        if not isinstance(response, list):
            return None

        candidates: list[tuple[float, dict[str, Any]]] = []
        for record in response:
            if not isinstance(record, dict):
                continue
            result = self._result_from_record(record)
            if result is None:
                continue
            candidates.append((self._score_record(song, record), record))

        if not candidates:
            return None

        _, best_record = max(candidates, key=lambda item: item[0])
        return self._result_from_record(best_record)

    def _request(self, endpoint: str, params: dict[str, str]) -> Any:
        response = self._get(
            f"{LRCLIB_BASE_URL}/{endpoint}",
            params=params,
            timeout=12,
            headers={"User-Agent": USER_AGENT},
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    def _search_genius(self, song: SongResult) -> LyricsResult | None:
        candidate = self._genius_best_match(song)
        if candidate is None:
            return None

        page_url, score = candidate
        if score < 0.52:
            return None

        response = self._get(page_url, timeout=12, headers={"User-Agent": USER_AGENT})
        response.raise_for_status()
        lyrics_text = self._lyrics_from_genius_html(response.text)
        if not lyrics_text:
            return None
        return LyricsResult(text=lyrics_text, is_lrc=False, source="Genius")

    def _genius_best_match(self, song: SongResult) -> tuple[str, float] | None:
        response = self._get(
            GENIUS_SEARCH_URL,
            params={"q": f"{song.artist} {song.title}"},
            timeout=10,
            headers={"User-Agent": USER_AGENT},
        )
        response.raise_for_status()
        payload = response.json()
        response_payload = payload.get("response") if isinstance(payload, dict) else None
        sections = response_payload.get("sections") if isinstance(response_payload, dict) else None
        if not isinstance(sections, list):
            return None

        candidates: list[tuple[float, str]] = []
        for section in sections:
            if not isinstance(section, dict):
                continue
            for hit in section.get("hits") or []:
                if not isinstance(hit, dict):
                    continue
                result = hit.get("result")
                if not isinstance(result, dict):
                    continue

                title = str(result.get("title") or result.get("full_title") or "")
                artist = self._genius_artist_name(result)
                page_url = str(result.get("url") or "")
                path = str(result.get("path") or "")
                if not page_url and path:
                    page_url = urljoin(GENIUS_BASE_URL, path)
                if not page_url:
                    continue

                score = (self._similarity(song.title, title) * 0.72) + (
                    self._similarity(song.artist, artist) * 0.28
                )
                candidates.append((score, page_url))

        if not candidates:
            return None

        score, page_url = max(candidates, key=lambda item: item[0])
        return page_url, score

    def _result_from_record(self, record: dict[str, Any]) -> LyricsResult | None:
        synced_lyrics = (record.get("syncedLyrics") or "").strip()
        if synced_lyrics:
            return LyricsResult(text=synced_lyrics, is_lrc=True, source="LRCLIB")

        plain_lyrics = (record.get("plainLyrics") or "").strip()
        if plain_lyrics:
            return LyricsResult(text=plain_lyrics, is_lrc=False, source="LRCLIB")

        return None

    def _score_record(self, song: SongResult, record: dict[str, Any]) -> float:
        title = str(record.get("trackName") or record.get("name") or "")
        artist = str(record.get("artistName") or "")
        title_score = self._similarity(song.title, title)
        artist_score = self._similarity(song.artist, artist)
        synced_bonus = 0.1 if record.get("syncedLyrics") else 0.0
        return (title_score * 0.65) + (artist_score * 0.25) + synced_bonus

    def _similarity(self, left: str, right: str) -> float:
        return SequenceMatcher(None, self._normalize(left), self._normalize(right)).ratio()

    def _normalize(self, text: str) -> str:
        text = re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", text)
        return " ".join(text.casefold().replace("&", "and").split())

    def _get(self, url: str, **kwargs: Any) -> Any:
        if self._request_get is not None:
            return self._request_get(url, **kwargs)

        import requests

        return requests.get(url, **kwargs)

    def _genius_artist_name(self, result: dict[str, Any]) -> str:
        artist = result.get("primary_artist")
        if isinstance(artist, dict):
            return str(artist.get("name") or "")
        return str(result.get("artist_names") or "")

    def _lyrics_from_genius_html(self, html_text: str) -> str:
        parser = _GeniusLyricsParser()
        parser.feed(html_text)
        parser.close()
        return self._clean_genius_lyrics(parser.lyrics_text())

    def _clean_genius_lyrics(self, lyrics_text: str) -> str:
        lines: list[str] = []
        for raw_line in lyrics_text.splitlines():
            line = unescape(raw_line).strip()
            line = re.sub(r"\s+", " ", line)
            if not line:
                if lines and lines[-1]:
                    lines.append("")
                continue
            if line.casefold() in {"embed", "you might also like"}:
                continue
            line = re.sub(r"\d+\s*embed$", "", line, flags=re.IGNORECASE).strip()
            if line:
                lines.append(line)

        while lines and not lines[-1]:
            lines.pop()
        return "\n".join(lines).strip()


class _GeniusLyricsParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._depth = 0
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if attributes.get("data-lyrics-container") == "true":
            self._depth += 1
            if self._parts and not self._parts[-1].endswith("\n"):
                self._parts.append("\n")
            return

        if self._depth > 0:
            if tag == "br":
                self._parts.append("\n")
                return
            self._depth += 1

    def handle_endtag(self, tag: str) -> None:
        if self._depth <= 0:
            return
        self._depth -= 1
        if self._depth == 0:
            self._parts.append("\n")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._depth > 0 and tag == "br":
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._depth > 0:
            self._parts.append(data)

    def lyrics_text(self) -> str:
        return "".join(self._parts)
