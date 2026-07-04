from __future__ import annotations

from pathlib import Path
import json
import tempfile
import unittest

from utils.settings import AppSettings, load_settings, save_settings


class SettingsTest(unittest.TestCase):
    def test_saves_and_loads_settings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "settings.json"
            settings = AppSettings()
            settings.audio.sample_rate = 48_000
            settings.ui.always_on_top = True

            save_settings(settings, settings_path)
            loaded = load_settings(settings_path)

        self.assertEqual(loaded.audio.sample_rate, 48_000)
        self.assertTrue(loaded.ui.always_on_top)

    def test_creates_default_settings_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "missing.json"
            loaded = load_settings(settings_path)

        self.assertIsInstance(loaded, AppSettings)

    def test_repairs_invalid_saved_settings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "settings.json"
            settings_path.write_text(
                json.dumps(
                    {
                        "audio": {"sample_rate": "bad", "buffer_size": -1},
                        "recognition": {"interval_seconds": 999},
                        "ui": {
                            "font_size": 999,
                            "animation_mode": "removed_mode",
                            "transparency": 0.1,
                            "window_width": 10,
                            "window_height": 10,
                        },
                        "paths": {"cache_dir": ["not", "a", "path"]},
                    }
                ),
                encoding="utf-8",
            )
            loaded = load_settings(settings_path)

        self.assertEqual(loaded.audio.sample_rate, 44_100)
        self.assertEqual(loaded.audio.buffer_size, 256)
        self.assertEqual(loaded.recognition.interval_seconds, 120)
        self.assertEqual(loaded.ui.font_size, 72)
        self.assertEqual(loaded.ui.animation_mode, "current_glow")
        self.assertEqual(loaded.ui.transparency, 0.6)
        self.assertEqual(loaded.ui.window_width, 760)
        self.assertEqual(loaded.ui.window_height, 480)


if __name__ == "__main__":
    unittest.main()
