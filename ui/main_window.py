from __future__ import annotations

from PySide6.QtCore import QThread, Qt, Slot
from PySide6.QtGui import (
    QAction,
    QColor,
    QCloseEvent,
    QFont,
    QIcon,
    QKeySequence,
    QPainter,
    QPixmap,
    QShortcut,
)
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from lyrics.parser import LyricLine, parse_lrc
from lyrics.sync import LyricsSynchronizer
from recognizer.media_controls import WindowsMediaControls
from recognizer.models import SongResult
from ui.karaoke_widget import KaraokeWidget
from ui.audio_worker import AudioMonitorUpdate, AudioMonitorWorker
from ui.lyrics_worker import LyricsLookupResult, LyricsLookupWorker
from ui.settings import SettingsDialog
from utils.display_power import keep_display_awake, release_display_awake
from utils.logging_config import get_logger
from utils.settings import AppSettings, save_settings

logger = get_logger(__name__)


class MainWindow(QMainWindow):
    def __init__(self, settings: AppSettings, start_services: bool = True) -> None:
        super().__init__()
        self.settings = settings
        self.setWindowTitle("Music Lyriz")
        self.resize(settings.ui.window_width, settings.ui.window_height)
        self.setMinimumSize(760, 480)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, settings.ui.always_on_top)
        self.setWindowOpacity(settings.ui.transparency)

        self.song_title = QLabel("No song recognized")
        self.song_title.setObjectName("songTitle")
        self.song_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.song_title.setWordWrap(True)
        self.song_title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.artist_label = QLabel("Start playback in any app; Music Lyriz will listen in the background.")
        self.artist_label.setObjectName("artistLabel")
        self.artist_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.artist_label.setWordWrap(True)
        self.artist_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.album_label = QLabel("Album art")
        self.album_label.setObjectName("albumArt")
        self.album_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._album_pixmap = self._album_placeholder()
        self.setWindowIcon(QIcon(self._album_pixmap))
        self.album_label.setPixmap(self._scaled_album_pixmap())

        self.karaoke_widget = KaraokeWidget()
        self.karaoke_widget.set_font_size(settings.ui.font_size)
        self.karaoke_widget.set_animation_mode(settings.ui.animation_mode)
        self.karaoke_widget.set_animation_speed(settings.ui.animation_speed_ms)
        self.status_label = QLabel("Recognition: idle | Audio: default system output | Cache: ready")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setWordWrap(True)

        self.settings_button = QPushButton("Settings")
        self.settings_button.clicked.connect(self.open_settings)
        self.hide_button = QPushButton("Hide")
        self.hide_button.clicked.connect(self.hide_to_tray)
        self.fullscreen_button = QPushButton("Full Screen")
        self.fullscreen_button.clicked.connect(self.toggle_fullscreen_mode)
        self.previous_button = QPushButton("Previous")
        self.previous_button.clicked.connect(self.previous_song)
        self.play_pause_button = QPushButton("Play / Pause")
        self.play_pause_button.clicked.connect(self.play_pause_song)
        self.next_button = QPushButton("Next")
        self.next_button.clicked.connect(self.next_song)
        self.previous_button.hide()
        self.play_pause_button.hide()
        self.next_button.hide()
        self.media_controls = WindowsMediaControls()

        self._build_layout()
        self._build_tray()
        self._build_shortcuts()
        self._audio_thread: QThread | None = None
        self._audio_worker: AudioMonitorWorker | None = None
        self._lyrics_threads: list[QThread] = []
        self._lyrics_workers: list[LyricsLookupWorker] = []
        self._active_song_key: str | None = None
        self._lyrics_song_key: str | None = None
        self._lyrics_status = "waiting"
        self._synced_lyric_lines: list[LyricLine] = []
        self._lyrics_synchronizer = LyricsSynchronizer()
        self._last_playback_seconds: float | None = None
        self._last_audio_active = False
        self._dynamic_background = QColor("#101214")
        self._dynamic_foreground = QColor("#F4F7FB")
        self._dynamic_muted = QColor("#AAB4C1")
        self._dynamic_accent = QColor("#E2B84D")
        self._fullscreen_mode = False
        self._shutdown_complete = False
        self._apply_dynamic_palette()
        if start_services:
            self._start_audio_monitor()

        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.shutdown_services)

    def _build_layout(self) -> None:
        self.root_widget = QWidget()
        self.root_widget.setObjectName("stageRoot")
        root_layout = QVBoxLayout(self.root_widget)
        root_layout.setContentsMargins(34, 30, 34, 28)
        root_layout.setSpacing(18)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(38)

        self.left_panel = QWidget()
        self.left_panel.setObjectName("leftPanel")
        self.left_panel.setMinimumWidth(320)
        self.left_panel.setMaximumWidth(430)
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        self.left_layout.setSpacing(18)

        self.album_label.setFixedSize(300, 300)
        self.left_layout.addStretch(1)
        self.left_layout.addWidget(self.album_label, 0, Qt.AlignmentFlag.AlignHCenter)
        self.left_layout.addSpacing(8)
        self.left_layout.addWidget(self.song_title)
        self.left_layout.addWidget(self.artist_label)

        button_row = QHBoxLayout()
        button_row.setSpacing(10)
        button_row.addStretch(1)
        button_row.addWidget(self.settings_button)
        button_row.addWidget(self.hide_button)
        button_row.addWidget(self.fullscreen_button)
        button_row.addWidget(self.previous_button)
        button_row.addWidget(self.play_pause_button)
        button_row.addWidget(self.next_button)
        button_row.addStretch(1)
        self.left_layout.addLayout(button_row)
        self.left_layout.addStretch(1)

        content_layout.addWidget(self.left_panel)
        content_layout.addWidget(self.karaoke_widget, 1)

        root_layout.addLayout(content_layout, 1)
        root_layout.addWidget(self.status_label)
        self.setCentralWidget(self.root_widget)

    def _build_tray(self) -> None:
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setToolTip("Music Lyriz")
        icon = self.windowIcon()
        if icon.isNull():
            icon = QIcon(self._album_pixmap)
        self.tray_icon.setIcon(icon)

        menu = QMenu(self)
        show_action = QAction("Show Music Lyriz", self)
        show_action.triggered.connect(self.show_from_tray)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        menu.addAction(show_action)
        menu.addSeparator()
        menu.addAction(quit_action)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon.show()

    def _build_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+,"), self, activated=self.open_settings)
        QShortcut(QKeySequence("Ctrl+H"), self, activated=self.hide_to_tray)
        QShortcut(QKeySequence("Ctrl+Q"), self, activated=QApplication.instance().quit)
        QShortcut(QKeySequence("F11"), self, activated=self.toggle_fullscreen_mode)
        QShortcut(QKeySequence("Esc"), self, activated=self.exit_fullscreen_mode)

    def _album_placeholder(self) -> QPixmap:
        pixmap = QPixmap(512, 512)
        pixmap.fill(QColor("#20252B"))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QColor("#E2B84D"))
        font = QFont("Segoe UI", 92, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "ML")
        painter.end()
        return pixmap

    def _scaled_album_pixmap(self) -> QPixmap:
        return self._album_pixmap.scaled(
            self.album_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    @Slot()
    def toggle_fullscreen_mode(self) -> None:
        if self._fullscreen_mode:
            self.exit_fullscreen_mode()
        else:
            self.enter_fullscreen_mode()

    @Slot()
    def enter_fullscreen_mode(self) -> None:
        if self._fullscreen_mode:
            return

        self._fullscreen_mode = True
        keep_display_awake()
        self.status_label.hide()
        self.settings_button.hide()
        self.hide_button.hide()
        self.fullscreen_button.setText("Exit")
        self.previous_button.show()
        self.play_pause_button.show()
        self.next_button.show()
        self.left_panel.setMaximumWidth(560)
        self.album_label.setFixedSize(460, 460)
        self.album_label.setPixmap(self._scaled_album_pixmap())
        self.karaoke_widget.set_font_size(42)
        self.karaoke_widget.set_animation_mode(self.settings.ui.animation_mode)
        self.karaoke_widget.set_animation_speed(self.settings.ui.animation_speed_ms)
        self.showFullScreen()

    @Slot()
    def exit_fullscreen_mode(self) -> None:
        if not self._fullscreen_mode:
            return

        self._fullscreen_mode = False
        release_display_awake()
        self.status_label.show()
        self.settings_button.show()
        self.hide_button.show()
        self.fullscreen_button.setText("Full Screen")
        self.previous_button.hide()
        self.play_pause_button.hide()
        self.next_button.hide()
        self.left_panel.setMaximumWidth(430)
        self.album_label.setFixedSize(300, 300)
        self.album_label.setPixmap(self._scaled_album_pixmap())
        self.karaoke_widget.set_font_size(self.settings.ui.font_size)
        self.karaoke_widget.set_animation_mode(self.settings.ui.animation_mode)
        self.karaoke_widget.set_animation_speed(self.settings.ui.animation_speed_ms)
        self.showNormal()

    def _set_album_art(self, album_art: bytes | None) -> None:
        if album_art:
            pixmap = QPixmap()
            if pixmap.loadFromData(album_art):
                self._album_pixmap = pixmap
                self._apply_album_palette(pixmap)
            else:
                self._album_pixmap = self._album_placeholder()
                self._reset_dynamic_palette()
        else:
            self._album_pixmap = self._album_placeholder()
            self._reset_dynamic_palette()

        self.album_label.setPixmap(self._scaled_album_pixmap())

    def _apply_album_palette(self, pixmap: QPixmap) -> None:
        image = pixmap.toImage().scaled(
            48,
            48,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        buckets: dict[tuple[int, int, int], int] = {}
        for x in range(image.width()):
            for y in range(image.height()):
                color = QColor(image.pixel(x, y))
                if color.alpha() < 16:
                    continue
                key = (
                    min(255, (color.red() // 24) * 24 + 12),
                    min(255, (color.green() // 24) * 24 + 12),
                    min(255, (color.blue() // 24) * 24 + 12),
                )
                buckets[key] = buckets.get(key, 0) + 1

        if not buckets:
            return

        light_color = self._dominant_bucket_color(buckets, prefer_light=True)
        dark_color = self._dominant_bucket_color(buckets, prefer_light=False)

        self._dynamic_background = self._ensure_light(
            self._mix_colors(light_color, QColor("#FFFFFF"), 0.58)
        )
        self._dynamic_foreground = self._ensure_dark(
            self._mix_colors(dark_color, QColor("#050607"), 0.48)
        )
        self._dynamic_muted = self._mix_colors(self._dynamic_foreground, self._dynamic_background, 0.36)
        self._dynamic_accent = self._ensure_dark(
            self._mix_colors(light_color, self._dynamic_foreground, 0.48)
        )
        self._apply_dynamic_palette()

    def _dominant_bucket_color(
        self,
        buckets: dict[tuple[int, int, int], int],
        prefer_light: bool,
    ) -> QColor:
        candidates: list[tuple[float, tuple[int, int, int]]] = []
        for key, count in buckets.items():
            color = QColor(*key)
            luminance = self._relative_luminance(color)
            saturation = color.hslSaturationF()
            if prefer_light and luminance < 0.52:
                continue
            if not prefer_light and luminance > 0.58:
                continue

            if prefer_light:
                score = count * (1.0 + saturation * 0.35 + luminance * 0.28)
            else:
                score = count * (1.0 + saturation * 0.45 + (1.0 - luminance) * 0.38)
            candidates.append((score, key))

        if not candidates:
            key = max(
                buckets,
                key=lambda item: self._relative_luminance(QColor(*item))
                if prefer_light
                else 1.0 - self._relative_luminance(QColor(*item)),
            )
            return QColor(*key)

        _, key = max(candidates, key=lambda item: item[0])
        return QColor(*key)

    def _relative_luminance(self, color: QColor) -> float:
        return (
            (0.2126 * color.redF())
            + (0.7152 * color.greenF())
            + (0.0722 * color.blueF())
        )

    def _ensure_light(self, color: QColor) -> QColor:
        while self._relative_luminance(color) < 0.78:
            color = self._mix_colors(color, QColor("#FFFFFF"), 0.18)
        return color

    def _ensure_dark(self, color: QColor) -> QColor:
        while self._relative_luminance(color) > 0.30:
            color = self._mix_colors(color, QColor("#000000"), 0.22)
        return color

    def _mix_colors(self, first: QColor, second: QColor, second_weight: float) -> QColor:
        first_weight = 1.0 - second_weight
        return QColor(
            int((first.red() * first_weight) + (second.red() * second_weight)),
            int((first.green() * first_weight) + (second.green() * second_weight)),
            int((first.blue() * first_weight) + (second.blue() * second_weight)),
        )

    def _apply_dynamic_palette(self) -> None:
        background = self._dynamic_background.name()
        foreground = self._dynamic_foreground.name()
        muted = self._dynamic_muted.name()
        accent = self._dynamic_accent.name()
        button_text = self._mix_colors(self._dynamic_foreground, QColor("#000000"), 0.35).name()

        self.root_widget.setStyleSheet(f"QWidget#stageRoot {{ background: {background}; }}")
        self.left_panel.setStyleSheet("QWidget#leftPanel { background: transparent; }")
        self.song_title.setStyleSheet(f"color: {foreground};")
        self.artist_label.setStyleSheet(f"color: {muted};")
        self.status_label.setStyleSheet(
            "QLabel#statusLabel { "
            f"color: {foreground}; "
            f"background: {self._mix_colors(self._dynamic_background, QColor('#FFFFFF'), 0.18).name()}; "
            f"border: 1px solid {self._mix_colors(self._dynamic_foreground, self._dynamic_background, 0.65).name()}; "
            "border-radius: 8px; "
            "padding: 10px 12px; "
            "}"
        )
        self.album_label.setStyleSheet(
            "QLabel#albumArt { "
            f"background: {self._mix_colors(self._dynamic_background, QColor('#FFFFFF'), 0.15).name()}; "
            f"border: 1px solid {self._mix_colors(self._dynamic_foreground, self._dynamic_background, 0.55).name()}; "
            "border-radius: 8px; "
            "}"
        )
        for button in (
            self.settings_button,
            self.hide_button,
            self.fullscreen_button,
            self.previous_button,
            self.play_pause_button,
            self.next_button,
        ):
            button.setStyleSheet(
                "QPushButton { "
                f"background: {accent}; "
                f"color: {button_text}; "
                "border: none; "
                "border-radius: 8px; "
                "padding: 8px 14px; "
                "font-weight: 700; "
                "}"
            )
        self.karaoke_widget.set_dynamic_colors(
            self._dynamic_foreground,
            self._dynamic_muted,
            self._dynamic_accent,
        )

    @Slot()
    def previous_song(self) -> None:
        if not self.media_controls.previous():
            self.status_label.setText("Media control unavailable: previous")

    @Slot()
    def play_pause_song(self) -> None:
        if not self.media_controls.play_pause():
            self.status_label.setText("Media control unavailable: play / pause")

    @Slot()
    def next_song(self) -> None:
        if not self.media_controls.next():
            self.status_label.setText("Media control unavailable: next")

    def _reset_dynamic_palette(self) -> None:
        self._dynamic_background = QColor("#101214")
        self._dynamic_foreground = QColor("#F4F7FB")
        self._dynamic_muted = QColor("#AAB4C1")
        self._dynamic_accent = QColor("#E2B84D")
        self._apply_dynamic_palette()

    def _start_audio_monitor(self) -> None:
        self._stop_audio_monitor()

        self._audio_thread = QThread(self)
        self._audio_worker = AudioMonitorWorker(self.settings.audio, self.settings.recognition)
        self._audio_worker.moveToThread(self._audio_thread)
        self._audio_thread.started.connect(self._audio_worker.run)
        self._audio_worker.status_changed.connect(self._on_audio_status_changed)
        self._audio_worker.error_changed.connect(self._on_audio_error)
        self._audio_worker.finished.connect(self._audio_thread.quit)
        self._audio_worker.finished.connect(self._audio_worker.deleteLater)
        self._audio_thread.finished.connect(self._audio_thread.deleteLater)
        self._audio_thread.start()

    def _stop_audio_monitor(self) -> None:
        if self._audio_worker is not None:
            self._audio_worker.stop()

        if self._audio_thread is not None and self._audio_thread.isRunning():
            self._audio_thread.quit()
            if not self._audio_thread.wait(3000):
                logger.warning("Audio monitor did not stop before shutdown timeout")

        self._audio_worker = None
        self._audio_thread = None

    @Slot(object)
    def _on_audio_status_changed(self, update: AudioMonitorUpdate) -> None:
        self._last_audio_active = update.active

        if update.song is not None:
            is_new_song = update.song.cache_key != self._active_song_key
            self._active_song_key = update.song.cache_key
            self._last_playback_seconds = update.song.position_seconds
            self.song_title.setText(update.song.title)
            self.artist_label.setText(update.song.artist)
            if is_new_song:
                self._set_album_art(update.song.album_art)
                self._clear_synced_lyrics()
                self._lyrics_status = "searching"
                self.karaoke_widget.set_lines(
                    "Song identified",
                    "Searching lyrics",
                    update.song.album or update.song.artist,
                )
                self._start_lyrics_lookup(update.song)
            elif self._synced_lyric_lines and update.song.position_seconds is not None:
                self._update_synced_lyrics_at(update.song.position_seconds)
        elif update.active:
            self._active_song_key = None
            self._lyrics_song_key = None
            self._lyrics_status = "waiting"
            self._last_playback_seconds = None
            self._clear_synced_lyrics()
            self._set_album_art(None)
            self.song_title.setText("System audio detected")
            self.artist_label.setText(
                "Music is playing. Waiting for Windows media metadata."
            )
            self.karaoke_widget.set_lines(
                "System audio is active",
                "Waiting for song metadata",
                "Use a player that exposes title and artist to Windows media controls",
            )
        elif not update.active:
            self._active_song_key = None
            self._lyrics_song_key = None
            self._lyrics_status = "waiting"
            self._last_playback_seconds = None
            self._clear_synced_lyrics()
            self._set_album_art(None)
            self.song_title.setText("No song recognized")
            self.artist_label.setText(
                "Start playback in any app; Music Lyriz will listen in the background."
            )
            self.karaoke_widget.set_lines(
                "Waiting for lyrics",
                "Music Lyriz",
                "Listening for system audio",
            )

        self.status_label.setText(
            f"{update.recognition_message} | {update.message} | "
            f"Lyrics: {self._lyrics_status} | Cache: ready"
        )

    @Slot(str)
    def _on_audio_error(self, message: str) -> None:
        self.status_label.setText(f"Recognition: waiting | Audio error: {message} | Cache: ready")
        self.song_title.setText("Audio capture unavailable")
        self.artist_label.setText("Open Settings and choose another audio device.")
        self.karaoke_widget.set_lines(
            "Audio capture unavailable",
            "Check Audio device in Settings",
            message,
        )

    def _start_lyrics_lookup(self, song: SongResult) -> None:
        if self._lyrics_song_key == song.cache_key:
            return

        self._lyrics_song_key = song.cache_key
        thread = QThread(self)
        worker = LyricsLookupWorker(song, self.settings.paths.cache_dir)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.result_ready.connect(self._on_lyrics_result)
        worker.error_changed.connect(self._on_lyrics_error)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda finished_thread=thread: self._forget_lyrics_thread(finished_thread))
        worker.finished.connect(lambda finished_worker=worker: self._forget_lyrics_worker(finished_worker))

        self._lyrics_threads.append(thread)
        self._lyrics_workers.append(worker)
        thread.start()

    @Slot(object)
    def _on_lyrics_result(self, result: LyricsLookupResult) -> None:
        if result.song.cache_key != self._lyrics_song_key:
            return

        if result.lyrics is None:
            self._lyrics_status = "not found"
            self.karaoke_widget.set_lines(
                "Song identified",
                "Lyrics not found",
                "Try another track or provider later",
            )
            self._refresh_lyrics_status_text()
            return

        cache_note = "cache" if result.from_cache else result.lyrics.source
        if result.lyrics.is_lrc:
            lines = [line for line in parse_lrc(result.lyrics.text) if line.text.strip()]
            if lines:
                self._lyrics_status = f"synced ({cache_note})"
                self._synced_lyric_lines = lines
                self._lyrics_synchronizer.set_lines(lines)
                self._update_synced_lyrics_at(self._last_playback_seconds or 0.0)
                self._refresh_lyrics_status_text()
                return

        self._lyrics_status = f"plain ({cache_note})"
        self._clear_synced_lyrics()
        self.karaoke_widget.set_plain_lyrics(result.lyrics.text)
        self._refresh_lyrics_status_text()

    @Slot(str)
    def _on_lyrics_error(self, message: str) -> None:
        self._lyrics_status = "error"
        self.karaoke_widget.set_lines("Song identified", "Lyrics error", message)
        self._refresh_lyrics_status_text()

    def _forget_lyrics_thread(self, thread: QThread) -> None:
        if thread in self._lyrics_threads:
            self._lyrics_threads.remove(thread)

    def _forget_lyrics_worker(self, worker: LyricsLookupWorker) -> None:
        if worker in self._lyrics_workers:
            self._lyrics_workers.remove(worker)

    def _update_synced_lyrics_at(self, playback_seconds: float) -> None:
        if not self._synced_lyric_lines:
            return

        index = self._lyrics_synchronizer.current_index_at(playback_seconds)
        if index is None:
            index = 0
        line_progress = self._line_progress_at(index, playback_seconds)
        self.karaoke_widget.set_synced_lyrics(
            [line.text for line in self._synced_lyric_lines],
            current_index=index,
            line_progress=line_progress,
        )

    def _line_progress_at(self, index: int, playback_seconds: float) -> float:
        if not self._synced_lyric_lines:
            return 0.0

        current_line = self._synced_lyric_lines[index]
        if index + 1 < len(self._synced_lyric_lines):
            next_timestamp = self._synced_lyric_lines[index + 1].timestamp
        else:
            next_timestamp = current_line.timestamp + 3.5

        duration = max(0.4, next_timestamp - current_line.timestamp)
        progress = (playback_seconds - current_line.timestamp) / duration
        return max(0.0, min(1.0, progress))

    def _clear_synced_lyrics(self) -> None:
        self._synced_lyric_lines = []
        self._lyrics_synchronizer.set_lines([])

    def _refresh_lyrics_status_text(self) -> None:
        parts = self.status_label.text().split(" | ")
        for index, part in enumerate(parts):
            if part.startswith("Lyrics:"):
                parts[index] = f"Lyrics: {self._lyrics_status}"
                self.status_label.setText(" | ".join(parts))
                return
        parts.insert(max(0, len(parts) - 1), f"Lyrics: {self._lyrics_status}")
        self.status_label.setText(" | ".join(parts))

    def open_settings(self) -> None:
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec():
            previous_audio_device = self.settings.audio.device_name
            self.settings = dialog.settings
            audio_device_changed = previous_audio_device != self.settings.audio.device_name
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, self.settings.ui.always_on_top)
            self.setWindowOpacity(self.settings.ui.transparency)
            self.karaoke_widget.set_font_size(self.settings.ui.font_size)
            self.karaoke_widget.set_animation_mode(self.settings.ui.animation_mode)
            self.karaoke_widget.set_animation_speed(self.settings.ui.animation_speed_ms)
            save_settings(self.settings)
            if audio_device_changed:
                self._show_audio_restarting_state()
            self._start_audio_monitor()
            self.show()
            logger.info("Settings updated from UI")

    def _show_audio_restarting_state(self) -> None:
        device_name = self.settings.audio.device_name or "Windows default"
        self._active_song_key = None
        self._lyrics_song_key = None
        self._lyrics_status = "waiting"
        self._last_playback_seconds = None
        self._clear_synced_lyrics()
        self.song_title.setText("Restarting audio capture")
        self.artist_label.setText(f"Listening device: {device_name}")
        self.karaoke_widget.set_lines(
            "Audio device changed",
            "Restarting listener",
            "Start playback after the status changes to listening",
        )
        self.status_label.setText(
            f"Recognition: waiting | Audio: restarting [{device_name}] | Lyrics: waiting | Cache: ready"
        )

    def hide_to_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            QMessageBox.information(self, "Music Lyriz", "System tray is not available.")
            return
        self.hide()
        self.tray_icon.showMessage("Music Lyriz", "Still listening in the background.")

    def show_from_tray(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_from_tray()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.settings.ui.window_width = self.width()
        self.settings.ui.window_height = self.height()
        save_settings(self.settings)
        self.shutdown_services()
        if hasattr(self, "tray_icon"):
            self.tray_icon.hide()
        event.accept()
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def resizeEvent(self, event) -> None:
        self.album_label.setPixmap(self._scaled_album_pixmap())
        super().resizeEvent(event)

    @Slot()
    def shutdown_services(self) -> None:
        if self._shutdown_complete:
            return

        self._shutdown_complete = True
        release_display_awake()
        self._stop_audio_monitor()
        for thread in list(self._lyrics_threads):
            if thread.isRunning():
                thread.quit()
                if not thread.wait(5000):
                    logger.warning("Lyrics lookup thread did not stop before shutdown timeout")
        self._lyrics_threads.clear()
        self._lyrics_workers.clear()
