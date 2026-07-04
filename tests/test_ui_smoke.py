from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtGui import QColor, QCloseEvent, QPixmap
    from PySide6.QtWidgets import QApplication
except ImportError:  # pragma: no cover - depends on local GUI dependencies
    QApplication = None  # type: ignore[assignment]
    QColor = None  # type: ignore[assignment]
    QCloseEvent = None  # type: ignore[assignment]
    QPixmap = None  # type: ignore[assignment]


@unittest.skipIf(QApplication is None, "PySide6 is not installed")
class UiSmokeTest(unittest.TestCase):
    def test_main_window_and_settings_dialog_construct(self) -> None:
        from ui.main_window import MainWindow
        from ui.lyrics_worker import LyricsLookupResult
        from ui.settings import SettingsDialog
        from ui.theme import apply_dark_theme
        from lyrics.search import LyricsResult
        from recognizer.models import SongResult
        from utils.settings import AppSettings

        app = QApplication.instance() or QApplication([])
        settings = AppSettings()
        apply_dark_theme(app, settings.ui.theme)

        window = MainWindow(settings, start_services=False)
        dialog = SettingsDialog(settings, window)

        self.assertGreaterEqual(dialog.minimumWidth(), 540)
        self.assertEqual(window.windowTitle(), "Music Lyriz")
        self.assertFalse(window.windowIcon().isNull())
        self.assertFalse(window.tray_icon.icon().isNull())
        self.assertIn("Audio: default system output", window.status_label.text())
        self.assertGreaterEqual(dialog.device_input.count(), 1)
        self.assertIsNone(dialog.device_input.itemData(0))
        self.assertIn("Default system output", dialog.device_input.itemText(0))
        self.assertEqual(dialog.refresh_devices_button.text(), "Refresh")
        self.assertEqual(dialog.animation_mode_input.count(), 2)
        self.assertFalse(hasattr(dialog, "minimize_to_tray_input"))
        for removed_mode in (
            "smooth",
            "word_by_word",
            "fade_word_by_word",
            "roll",
            "kinetic",
        ):
            self.assertEqual(dialog.animation_mode_input.findData(removed_mode), -1)

        window.karaoke_widget.set_plain_lyrics("First line\nSecond line")
        self.assertFalse(window.karaoke_widget.plain_lyrics_view.isHidden())
        self.assertIn("First line", window.karaoke_widget.plain_lyrics_view.toPlainText())

        poster = QPixmap(24, 24)
        poster.fill(QColor("#F0C86A"))
        window._apply_album_palette(poster)
        self.assertNotEqual(window._dynamic_background.name(), "#101214")
        self.assertGreater(window._relative_luminance(window._dynamic_background), 0.78)
        self.assertLess(window._relative_luminance(window._dynamic_foreground), 0.31)

        window.enter_fullscreen_mode()
        self.assertTrue(window._fullscreen_mode)
        self.assertTrue(window.status_label.isHidden())
        self.assertTrue(window.settings_button.isHidden())
        self.assertEqual(window.fullscreen_button.text(), "Exit")
        self.assertFalse(window.previous_button.isHidden())
        self.assertFalse(window.play_pause_button.isHidden())
        self.assertFalse(window.next_button.isHidden())

        window.exit_fullscreen_mode()
        self.assertFalse(window._fullscreen_mode)
        self.assertFalse(window.status_label.isHidden())
        self.assertEqual(window.fullscreen_button.text(), "Full Screen")
        self.assertTrue(window.previous_button.isHidden())
        self.assertTrue(window.play_pause_button.isHidden())
        self.assertTrue(window.next_button.isHidden())

        window.karaoke_widget.set_synced_lyrics(["Whoa", "", "And so we pray", "I pray that I do my best"])
        self.assertTrue(window.karaoke_widget.plain_lyrics_view.isHidden())
        self.assertEqual(window.karaoke_widget.current_label.text(), "Whoa")
        self.assertEqual(window.karaoke_widget.next_label.text(), "And so we pray")

        window.karaoke_widget.set_animation_mode("line_by_line")
        window.karaoke_widget.set_synced_lyrics(["Previous", "Current", "Next"], current_index=1)
        self.assertEqual(window.karaoke_widget.previous_label.text(), "")
        self.assertEqual(window.karaoke_widget.current_label.text(), "Current")
        self.assertEqual(window.karaoke_widget.next_label.text(), "")

        window.karaoke_widget.set_animation_mode("kinetic")
        window.karaoke_widget.set_synced_lyrics(["Previous", "Current", "Next"], current_index=1)
        self.assertEqual(window.karaoke_widget.previous_label.text(), "Previous")
        self.assertEqual(window.karaoke_widget.current_label.text(), "Current")
        self.assertEqual(window.karaoke_widget.next_label.text(), "Next")

        window.karaoke_widget.set_animation_mode(settings.ui.animation_mode)
        song = SongResult("Test Song", "Test Artist", position_seconds=10.0)
        window._lyrics_song_key = song.cache_key
        window._last_playback_seconds = 10.0
        window._on_lyrics_result(
            LyricsLookupResult(
                song,
                LyricsResult("[00:03.00]First line\n[00:10.00]Current line", True, "test"),
                False,
            )
        )
        self.assertEqual(window.karaoke_widget.current_label.text(), "Current line")

        window.settings.audio.device_name = "Test Output"
        window._show_audio_restarting_state()
        self.assertEqual(window.song_title.text(), "Restarting audio capture")
        self.assertIn("Test Output", window.artist_label.text())
        self.assertIn("Audio: restarting [Test Output]", window.status_label.text())

        close_event = QCloseEvent()
        window.closeEvent(close_event)
        self.assertTrue(close_event.isAccepted())

        dialog.close()


if __name__ == "__main__":
    unittest.main()
