from __future__ import annotations

import unittest

from lyrics.parser import parse_lrc


class ParseLrcTest(unittest.TestCase):
    def test_parses_basic_lrc_lines(self) -> None:
        lines = parse_lrc("[00:12.10]Hello\n[01:45.50]World")

        self.assertEqual(len(lines), 2)
        self.assertAlmostEqual(lines[0].timestamp, 12.1)
        self.assertEqual(lines[0].text, "Hello")
        self.assertAlmostEqual(lines[1].timestamp, 105.5)
        self.assertEqual(lines[1].text, "World")

    def test_parses_repeated_timestamps(self) -> None:
        lines = parse_lrc("[00:01.00][00:02.00]Again")

        self.assertEqual([line.text for line in lines], ["Again", "Again"])
        self.assertEqual([line.timestamp for line in lines], [1.0, 2.0])


if __name__ == "__main__":
    unittest.main()
