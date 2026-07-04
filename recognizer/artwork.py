from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

from utils.logging_config import get_logger

logger = get_logger(__name__)

ITUNES_SEARCH_URL = "https://itunes.apple.com/search"
USER_AGENT = "MusicLyriz/0.1"


def fetch_hd_album_art(title: str, artist: str, album: str | None = None) -> bytes | None:
    """Fetch high-resolution album artwork from iTunes Search when available."""

    query = " ".join(part for part in (artist, title, album or "") if part).strip()
    if not query:
        return None

    try:
        import requests

        response = requests.get(
            ITUNES_SEARCH_URL,
            params={"term": query, "entity": "song", "limit": 8},
            headers={"User-Agent": USER_AGENT},
            timeout=5,
        )
        response.raise_for_status()
        results = response.json().get("results", [])
        artwork_url = _best_artwork_url(title, artist, results)
        if not artwork_url:
            return None

        artwork_response = requests.get(
            _hd_artwork_url(artwork_url),
            headers={"User-Agent": USER_AGENT},
            timeout=8,
        )
        artwork_response.raise_for_status()
        content_type = artwork_response.headers.get("content-type", "")
        if "image" not in content_type.casefold():
            return None
        return artwork_response.content
    except Exception:
        logger.debug("Could not fetch HD album art for %s - %s", artist, title, exc_info=True)
        return None


def _best_artwork_url(title: str, artist: str, results: list[dict[str, Any]]) -> str | None:
    best_score = 0.0
    best_url: str | None = None
    for item in results:
        url = item.get("artworkUrl100")
        if not isinstance(url, str):
            continue

        track_score = _similarity(title, str(item.get("trackName") or ""))
        artist_score = _similarity(artist, str(item.get("artistName") or ""))
        score = (track_score * 0.7) + (artist_score * 0.3)
        if score > best_score:
            best_score = score
            best_url = url

    if best_score < 0.45:
        return None
    return best_url


def _hd_artwork_url(url: str) -> str:
    return (
        url.replace("100x100bb", "1000x1000bb")
        .replace("100x100-75", "1000x1000-75")
        .replace("/100x100", "/1000x1000")
    )


def _similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, _normalize(left), _normalize(right)).ratio()


def _normalize(text: str) -> str:
    return " ".join(text.casefold().replace("&", "and").split())
