from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from audio.devices import list_system_audio_devices
from utils.settings import AppSettings


ANIMATION_MODE_LABELS = {
    "current_glow": "Current glow",
    "line_by_line": "Line by line",
}


class SettingsDialog(QDialog):
    def __init__(self, settings: AppSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(540)
        self.resize(580, 520)
        self.settings = settings

        self.device_input = QComboBox()
        self.device_input.setToolTip(
            "Default follows your Windows output device. Other entries use that output's WASAPI loopback."
        )
        self.device_input.setMinimumWidth(320)
        self._populate_audio_devices(settings.audio.device_name)
        self.refresh_devices_button = QPushButton("Refresh")
        self.refresh_devices_button.clicked.connect(self._refresh_audio_devices)
        self.interval_input = QSpinBox()
        self.interval_input.setRange(5, 120)
        self.interval_input.setSuffix(" s")
        self.interval_input.setValue(settings.recognition.interval_seconds)

        self.theme_input = QComboBox()
        self.theme_input.addItems(["dark"])
        self.theme_input.setCurrentText(settings.ui.theme)

        self.font_size_input = QSpinBox()
        self.font_size_input.setRange(18, 72)
        self.font_size_input.setValue(settings.ui.font_size)

        self.animation_speed_input = QSpinBox()
        self.animation_speed_input.setRange(50, 1000)
        self.animation_speed_input.setSuffix(" ms")
        self.animation_speed_input.setValue(settings.ui.animation_speed_ms)

        self.animation_mode_input = QComboBox()
        for mode_key, label in ANIMATION_MODE_LABELS.items():
            self.animation_mode_input.addItem(label, mode_key)
        selected_index = self.animation_mode_input.findData(settings.ui.animation_mode)
        self.animation_mode_input.setCurrentIndex(max(0, selected_index))

        self.cache_location_input = QLineEdit(str(settings.paths.cache_dir))
        self.cache_location_input.setMinimumWidth(320)
        self.cache_location_input.setToolTip(str(settings.paths.cache_dir))
        self.browse_cache_button = QPushButton("Browse")
        self.browse_cache_button.clicked.connect(self._choose_cache_location)
        self.always_on_top_input = QCheckBox("Always on top")
        self.always_on_top_input.setChecked(settings.ui.always_on_top)
        self.transparency_input = QSlider(Qt.Orientation.Horizontal)
        self.transparency_input.setRange(60, 100)
        self.transparency_input.setValue(int(settings.ui.transparency * 100))
        self.transparency_label = QLabel(f"{self.transparency_input.value()}%")
        self.transparency_input.valueChanged.connect(
            lambda value: self.transparency_label.setText(f"{value}%")
        )

        self._build_layout()

    def _build_layout(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 18)
        layout.setSpacing(14)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(12)

        audio_device_row = QHBoxLayout()
        audio_device_row.setSpacing(8)
        audio_device_row.addWidget(self.device_input, 1)
        audio_device_row.addWidget(self.refresh_devices_button)
        form.addRow("Audio device", audio_device_row)
        form.addRow("Recognition interval", self.interval_input)
        form.addRow("Theme", self.theme_input)
        form.addRow("Font size", self.font_size_input)
        form.addRow("Animation speed", self.animation_speed_input)
        form.addRow("Lyric animation", self.animation_mode_input)

        cache_row = QHBoxLayout()
        cache_row.setSpacing(8)
        cache_row.addWidget(self.cache_location_input, 1)
        cache_row.addWidget(self.browse_cache_button)
        form.addRow("Cache location", cache_row)

        form.addRow("", self.always_on_top_input)

        transparency_row = QVBoxLayout()
        transparency_row.setSpacing(6)
        transparency_row.addWidget(self.transparency_input)
        transparency_row.addWidget(self.transparency_label)
        form.addRow("Transparency", transparency_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        reset_button = QPushButton("Reset Defaults")
        reset_button.clicked.connect(self._reset_defaults)

        layout.addLayout(form)
        layout.addWidget(reset_button)
        layout.addWidget(buttons)

    def _choose_cache_location(self) -> None:
        current_path = self.cache_location_input.text().strip()
        selected_path = QFileDialog.getExistingDirectory(
            self,
            "Choose cache location",
            current_path or str(self.settings.paths.cache_dir),
        )
        if selected_path:
            self.cache_location_input.setText(selected_path)
            self.cache_location_input.setToolTip(selected_path)

    def _accept(self) -> None:
        cache_dir = Path(self.cache_location_input.text().strip() or self.settings.paths.cache_dir)
        self.settings = replace(
            self.settings,
            audio=replace(
                self.settings.audio,
                device_name=self._selected_audio_device_name(),
            ),
            recognition=replace(
                self.settings.recognition,
                interval_seconds=self.interval_input.value(),
            ),
            ui=replace(
                self.settings.ui,
                theme=self.theme_input.currentText(),
                font_size=self.font_size_input.value(),
                animation_speed_ms=self.animation_speed_input.value(),
                animation_mode=str(self.animation_mode_input.currentData()),
                always_on_top=self.always_on_top_input.isChecked(),
                transparency=self.transparency_input.value() / 100,
            ),
            paths=replace(
                self.settings.paths,
                cache_dir=cache_dir,
            ),
        )
        self.accept()

    def _reset_defaults(self) -> None:
        defaults = AppSettings()
        self._populate_audio_devices(defaults.audio.device_name)
        self.interval_input.setValue(defaults.recognition.interval_seconds)
        self.theme_input.setCurrentText(defaults.ui.theme)
        self.font_size_input.setValue(defaults.ui.font_size)
        self.animation_speed_input.setValue(defaults.ui.animation_speed_ms)
        self.animation_mode_input.setCurrentIndex(
            max(0, self.animation_mode_input.findData(defaults.ui.animation_mode))
        )
        self.cache_location_input.setText(str(defaults.paths.cache_dir))
        self.cache_location_input.setToolTip(str(defaults.paths.cache_dir))
        self.always_on_top_input.setChecked(defaults.ui.always_on_top)
        self.transparency_input.setValue(int(defaults.ui.transparency * 100))

    def _populate_audio_devices(self, selected_device_name: str | None) -> None:
        self.device_input.clear()
        choices = list_system_audio_devices()
        for choice in choices:
            self.device_input.addItem(choice.label, choice.device_name)

        selected_index = self.device_input.findData(selected_device_name)
        if selected_index == -1 and selected_device_name:
            self.device_input.addItem(
                f"{selected_device_name} (saved, not currently active)",
                selected_device_name,
            )
            selected_index = self.device_input.count() - 1
        self.device_input.setCurrentIndex(max(0, selected_index))

    def _selected_audio_device_name(self) -> str | None:
        device_name = self.device_input.currentData()
        return str(device_name) if device_name else None

    def _refresh_audio_devices(self) -> None:
        self._populate_audio_devices(self._selected_audio_device_name())
