from __future__ import annotations

from PySide6.QtWidgets import QApplication


def apply_dark_theme(app: QApplication, theme_name: str = "dark") -> None:
    if theme_name != "dark":
        theme_name = "dark"

    app.setStyleSheet(
        """
        QWidget {
            background: #101214;
            color: #F4F7FB;
            font-family: "Segoe UI", "Inter", sans-serif;
            font-size: 15px;
        }
        QLabel {
            background: transparent;
        }
        QMainWindow {
            background: #101214;
        }
        QLabel#songTitle {
            font-size: 30px;
            font-weight: 700;
            color: #FFFFFF;
        }
        QLabel#artistLabel {
            font-size: 16px;
            color: #AAB4C1;
        }
        QLabel#albumArt {
            background: #20252B;
            border: 1px solid #313943;
            border-radius: 8px;
            color: #768292;
        }
        QLabel#previousLyric {
            color: #748091;
        }
        QLabel#currentLyric {
            color: #FFFFFF;
        }
        QLabel#nextLyric {
            color: #9BA6B5;
        }
        QTextBrowser#plainLyrics {
            background: transparent;
            color: #F4F7FB;
            border: none;
            font-size: 24px;
            line-height: 150%;
            padding: 8px 14px;
        }
        QLabel#statusLabel {
            color: #96A2B0;
            padding: 10px 12px;
            background: #171B20;
            border: 1px solid #2A313A;
            border-radius: 8px;
        }
        QPushButton {
            background: #E2B84D;
            color: #111315;
            border: none;
            border-radius: 8px;
            padding: 8px 14px;
            font-weight: 700;
        }
        QPushButton:hover {
            background: #F0C95D;
        }
        QPushButton:pressed {
            background: #CFA33A;
        }
        QDialog {
            background: #12161A;
        }
        QDialog QLabel {
            color: #F4F7FB;
            background: transparent;
        }
        QLineEdit, QSpinBox, QComboBox {
            background: #1A1F25;
            color: #F4F7FB;
            border: 1px solid #303843;
            border-radius: 6px;
            padding: 6px 8px;
            min-height: 28px;
            selection-background-color: #E2B84D;
            selection-color: #111315;
        }
        QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
            border-color: #E2B84D;
        }
        QSpinBox::up-button, QSpinBox::down-button {
            background: #20262E;
            border-left: 1px solid #303843;
            width: 22px;
        }
        QComboBox::drop-down {
            background: #20262E;
            border-left: 1px solid #303843;
            width: 26px;
        }
        QCheckBox {
            spacing: 8px;
            color: #F4F7FB;
            background: transparent;
        }
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
            border-radius: 5px;
            border: 1px solid #303843;
            background: #151A20;
        }
        QCheckBox::indicator:checked {
            background: #E2B84D;
            border-color: #E2B84D;
        }
        QSlider::groove:horizontal {
            height: 6px;
            background: #303843;
            border-radius: 3px;
        }
        QSlider::handle:horizontal {
            background: #E2B84D;
            width: 18px;
            margin: -6px 0;
            border-radius: 9px;
        }
        """
    )
