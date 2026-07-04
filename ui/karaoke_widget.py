from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QLabel,
    QSizePolicy,
    QStackedLayout,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from lyrics.sync import SyncState


class KaraokeWidget(QWidget):
    """Displays previous, current, and next lyric lines."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("karaokeWidget")
        self.previous_label = QLabel("Waiting for lyrics")
        self.current_label = QLabel("Music Lyriz")
        self.next_label = QLabel("Listening for system audio")
        self.plain_lyrics_view = QTextBrowser()
        self.plain_lyrics_view.setObjectName("plainLyrics")
        self.plain_lyrics_view.setReadOnly(True)
        self.plain_lyrics_view.setVisible(False)

        for label in (self.previous_label, self.current_label, self.next_label):
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setWordWrap(True)
            label.setMinimumHeight(48)
            label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self.previous_label.setObjectName("previousLyric")
        self.current_label.setObjectName("currentLyric")
        self.next_label.setObjectName("nextLyric")

        self._current_size = 42
        self._animation_mode = "current_glow"
        self._animation_speed_ms = 260
        self._current_animation_key = ""
        self._foreground = QColor("#F4F7FB")
        self._muted = QColor("#AAB4C1")
        self._accent = QColor("#E2B84D")
        self._current_glow = QGraphicsDropShadowEffect(self.current_label)
        self._current_glow.setBlurRadius(18)
        self._current_glow.setOffset(0, 0)
        self._current_glow.setColor(QColor(226, 184, 77, 190))
        self.current_label.setGraphicsEffect(self._current_glow)

        self._glow_animation = QPropertyAnimation(self._current_glow, b"blurRadius", self)
        self._glow_animation.setDuration(520)
        self._glow_animation.setStartValue(42)
        self._glow_animation.setKeyValueAt(0.55, 24)
        self._glow_animation.setEndValue(18)
        self._glow_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._size_animation = QVariantAnimation(self)
        self._size_animation.setDuration(360)
        self._size_animation.setEasingCurve(QEasingCurve.Type.OutBack)
        self._size_animation.valueChanged.connect(self._set_current_font_size)

        self.karaoke_page = QWidget()
        self.karaoke_page.setObjectName("karaokePage")
        karaoke_layout = QVBoxLayout(self.karaoke_page)
        karaoke_layout.setContentsMargins(0, 0, 0, 0)
        karaoke_layout.setSpacing(18)
        karaoke_layout.addStretch(1)
        karaoke_layout.addWidget(self.previous_label)
        karaoke_layout.addWidget(self.current_label)
        karaoke_layout.addWidget(self.next_label)
        karaoke_layout.addStretch(1)

        self.stack = QStackedLayout(self)
        self.stack.addWidget(self.karaoke_page)
        self.stack.addWidget(self.plain_lyrics_view)
        self.stack.setCurrentWidget(self.karaoke_page)

    def set_animation_mode(self, mode: str) -> None:
        valid_modes = {
            "current_glow",
            "line_by_line",
        }
        self._animation_mode = mode if mode in valid_modes else "current_glow"

    def set_animation_speed(self, speed_ms: int) -> None:
        self._animation_speed_ms = max(50, min(speed_ms, 1200))
        self._glow_animation.setDuration(max(180, self._animation_speed_ms * 2))
        self._size_animation.setDuration(max(160, int(self._animation_speed_ms * 1.4)))

    def set_font_size(self, current_size: int) -> None:
        current_size = max(18, min(current_size, 72))
        self._current_size = current_size
        previous_size = max(16, int(current_size * 0.55))
        next_size = max(16, int(current_size * 0.6))

        for label, size, weight in (
            (self.previous_label, previous_size, QFont.Weight.Normal),
            (self.current_label, current_size, QFont.Weight.ExtraBold),
            (self.next_label, next_size, QFont.Weight.Normal),
        ):
            font = label.font()
            font.setPointSize(size)
            font.setWeight(weight)
            label.setFont(font)
        self._apply_label_styles()

    def set_dynamic_colors(self, foreground: QColor, muted: QColor, accent: QColor) -> None:
        self._foreground = foreground
        self._muted = muted
        self._accent = accent
        self.setStyleSheet(
            "QWidget#karaokeWidget, QWidget#karaokePage { background: transparent; }"
        )
        self._apply_label_styles()
        self.plain_lyrics_view.setStyleSheet(
            "QTextBrowser#plainLyrics { "
            "background: transparent; "
            f"color: {self._foreground.name()}; "
            "border: none; "
            "font-size: 24px; "
            "line-height: 150%; "
            "padding: 8px 14px; "
            "}"
        )
        self._current_glow.setColor(
            QColor(self._accent.red(), self._accent.green(), self._accent.blue(), 190)
        )

    def _apply_label_styles(self) -> None:
        previous_size = max(16, int(self._current_size * 0.55))
        next_size = max(16, int(self._current_size * 0.6))
        self.previous_label.setStyleSheet(
            f"color: {self._muted.name()}; font-size: {previous_size}pt; font-weight: 400;"
        )
        self.current_label.setStyleSheet(
            f"color: {self._foreground.name()}; font-size: {self._current_size}pt; "
            "font-weight: 800;"
        )
        self.next_label.setStyleSheet(
            f"color: {self._muted.name()}; font-size: {next_size}pt; font-weight: 400;"
        )

    def set_state(self, state: SyncState) -> None:
        self._show_karaoke_labels()
        previous = state.previous_line.text if state.previous_line else ""
        current = state.current_line.text if state.current_line else "No synchronized lyric yet"
        next_line = state.next_line.text if state.next_line else ""
        self.set_lines(previous, current, next_line)

    def set_lines(self, previous: str, current: str, next_line: str) -> None:
        self._show_karaoke_labels(show_lyrics_list=False)
        self._set_label_texts(previous, current, next_line)

    def set_synced_lyrics(
        self,
        lyric_lines: list[str],
        current_index: int = 0,
        line_progress: float = 0.0,
    ) -> None:
        visible_lines = [line.strip() for line in lyric_lines if line.strip()]
        if not visible_lines:
            self.set_lines("Song identified", "No displayable synced lyrics", "")
            return

        current_index = max(0, min(current_index, len(visible_lines) - 1))
        previous = visible_lines[current_index - 1] if current_index > 0 else ""
        current = visible_lines[current_index]
        next_line = visible_lines[current_index + 1] if current_index + 1 < len(visible_lines) else ""

        self._show_karaoke_labels(show_lyrics_list=False)
        if self._animation_mode == "line_by_line":
            self._set_label_texts("", current, "", animate_key=f"{current_index}:{current}")
            return

        self._set_label_texts(previous, current, next_line, animate_key=f"{current_index}:{current}")

    def _set_label_texts(
        self,
        previous: str,
        current: str,
        next_line: str,
        animate_key: str | None = None,
    ) -> None:
        animate_key = animate_key or current
        should_animate = self._current_animation_key != animate_key

        self.previous_label.setText(previous)
        self.current_label.setTextFormat(Qt.TextFormat.PlainText)
        self.current_label.setText(current)
        self.next_label.setText(next_line)

        if should_animate:
            self._current_animation_key = animate_key
            self._play_current_line_effect()

    def _play_current_line_effect(self) -> None:
        if self._animation_mode == "current_glow":
            self._glow_animation.stop()
            self._glow_animation.start()

            self._size_animation.stop()
            self._size_animation.setStartValue(max(18, self._current_size - 4))
            self._size_animation.setEndValue(self._current_size)
            self._size_animation.start()

    def _set_current_font_size(self, size: int | float) -> None:
        font = self.current_label.font()
        font.setPointSize(int(size))
        font.setWeight(QFont.Weight.ExtraBold)
        self.current_label.setFont(font)

    def set_plain_lyrics(self, lyrics_text: str) -> None:
        self.stack.setCurrentWidget(self.plain_lyrics_view)
        self.plain_lyrics_view.setPlainText(lyrics_text.strip())
        self.plain_lyrics_view.verticalScrollBar().setValue(0)

    def _show_karaoke_labels(self, show_lyrics_list: bool = False) -> None:
        self.stack.setCurrentWidget(self.karaoke_page)
