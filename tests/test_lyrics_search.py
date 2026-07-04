from __future__ import annotations

import unittest

from lyrics.search import LyricsSearch
from recognizer.models import SongResult


class FakeResponse:
    def __init__(
        self,
        payload: object | None = None,
        text: str = "",
        status_code: int = 200,
    ) -> None:
        self._payload = payload
        self.text = text
        self.status_code = status_code

    def json(self) -> object | None:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class LyricsSearchTest(unittest.TestCase):
    def test_prefers_synced_lyrics_when_available(self) -> None:
        search = LyricsSearch()

        result = search._result_from_record(
            {
                "plainLyrics": "plain lyric",
                "syncedLyrics": "[00:01.00]synced lyric",
            }
        )

        self.assertIsNotNone(result)
        self.assertTrue(result.is_lrc)
        self.assertEqual(result.text, "[00:01.00]synced lyric")

    def test_falls_back_to_plain_lyrics(self) -> None:
        search = LyricsSearch()

        result = search._result_from_record(
            {
                "plainLyrics": "plain lyric",
                "syncedLyrics": None,
            }
        )

        self.assertIsNotNone(result)
        self.assertFalse(result.is_lrc)
        self.assertEqual(result.text, "plain lyric")

    def test_uses_genius_when_lrclib_has_no_result(self) -> None:
        calls: list[str] = []

        def fake_get(url: str, **kwargs) -> FakeResponse:
            calls.append(url)
            if "lrclib.net/api/get" in url:
                return FakeResponse(status_code=404)
            if "lrclib.net/api/search" in url:
                return FakeResponse([])
            if "genius.com/api/search/multi" in url:
                return FakeResponse(
                    {
                        "response": {
                            "sections": [
                                {
                                    "hits": [
                                        {
                                            "result": {
                                                "title": "Test Song",
                                                "primary_artist": {"name": "Test Artist"},
                                                "url": "https://genius.com/test-artist-test-song-lyrics",
                                            }
                                        }
                                    ]
                                }
                            ]
                        }
                    }
                )
            return FakeResponse(
                text=(
                    '<div data-lyrics-container="true">'
                    "First line<br/>Second line"
                    "</div>"
                    '<div data-lyrics-container="true">Third line</div>'
                )
            )

        result = LyricsSearch(request_get=fake_get).search(SongResult("Test Song", "Test Artist"))

        self.assertIsNotNone(result)
        self.assertFalse(result.is_lrc)
        self.assertEqual(result.source, "Genius")
        self.assertEqual(result.text, "First line\nSecond line\nThird line")
        self.assertTrue(any("lrclib.net" in call for call in calls))
        self.assertTrue(any("genius.com/api/search/multi" in call for call in calls))

    def test_ignores_low_confidence_genius_match(self) -> None:
        def fake_get(url: str, **kwargs) -> FakeResponse:
            if "lrclib.net/api/get" in url:
                return FakeResponse(status_code=404)
            if "lrclib.net/api/search" in url:
                return FakeResponse([])
            return FakeResponse(
                {
                    "response": {
                        "sections": [
                            {
                                "hits": [
                                    {
                                        "result": {
                                            "title": "Different Song",
                                            "primary_artist": {"name": "Other Artist"},
                                            "url": "https://genius.com/other-artist-different-song-lyrics",
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                }
            )

        result = LyricsSearch(request_get=fake_get).search(SongResult("Test Song", "Test Artist"))

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
