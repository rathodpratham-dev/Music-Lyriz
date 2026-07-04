from __future__ import annotations

import unittest

from lyrics.parser import LyricLine
from lyrics.sync import LyricsSynchronizer


class LyricsSynchronizerTest(unittest.TestCase):
    def test_current_index_tracks_playback_time(self) -> None:
        synchronizer = LyricsSynchronizer(
            [
                LyricLine(3.0, "first"),
                LyricLine(10.0, "second"),
                LyricLine(20.0, "third"),
            ]
        )

        self.assertIsNone(synchronizer.current_index_at(1.0))
        self.assertEqual(synchronizer.current_index_at(3.0), 0)
        self.assertEqual(synchronizer.current_index_at(14.0), 1)
        self.assertEqual(synchronizer.current_index_at(25.0), 2)


if __name__ == "__main__":
    unittest.main()
