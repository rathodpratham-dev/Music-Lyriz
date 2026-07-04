from __future__ import annotations

import unittest

from recognizer.artwork import _best_artwork_url, _hd_artwork_url


class ArtworkTest(unittest.TestCase):
    def test_upgrades_itunes_artwork_url_to_hd(self) -> None:
        url = "https://example.test/image/100x100bb.jpg"

        self.assertEqual(_hd_artwork_url(url), "https://example.test/image/1000x1000bb.jpg")

    def test_selects_best_matching_artwork_url(self) -> None:
        url = _best_artwork_url(
            "LALISA",
            "LISA",
            [
                {
                    "trackName": "Other Song",
                    "artistName": "Other Artist",
                    "artworkUrl100": "https://example.test/other/100x100bb.jpg",
                },
                {
                    "trackName": "LALISA",
                    "artistName": "LISA",
                    "artworkUrl100": "https://example.test/lalisa/100x100bb.jpg",
                },
            ],
        )

        self.assertEqual(url, "https://example.test/lalisa/100x100bb.jpg")


if __name__ == "__main__":
    unittest.main()
