# Pixem
# Copyright 2025 - Ricardo Quesada

import functools
import logging
import sys
from enum import IntEnum, auto

from PySide6.QtCore import Slot
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)

from preferences import get_global_preferences

logger = logging.getLogger(__name__)  # __name__ gets the current module's name


class ColorType(IntEnum):
    FOREGROUND = auto()
    BACKGROUND = auto()


class PreferenceDialog(QDialog):
    def __init__(self, hoop_size: tuple[float, float]):
        super().__init__()

        self._colors = {ColorType.FOREGROUND: {}, ColorType.BACKGROUND: {}}
        self._colors[ColorType.FOREGROUND]["color"] = QColor(
            get_global_preferences().get_partition_foreground_color()
        )
        self._colors[ColorType.BACKGROUND]["color"] = QColor(
            get_global_preferences().get_partition_background_color()
        )

        self.setWindowTitle(self.tr("Preference Dialog"))

        hoop_group_box = QGroupBox(self.tr("Hoop Size (inches)"))
        self._hoop_group = QVBoxLayout()
        self._hoop_4_4_radio = QRadioButton(self.tr("4x4"))
        self._hoop_5_7_radio = QRadioButton(self.tr("5x7"))
        self._hoop_7_5_radio = QRadioButton(self.tr("7x5"))
        self._hoop_6_10_radio = QRadioButton(self.tr("6x10"))
        self._hoop_10_6_radio = QRadioButton(self.tr("10x6"))
        self._hoop_custom_radio = QRadioButton(self.tr("Custom:"))
        self._custom_size_x_spinbox = QDoubleSpinBox()
        self._custom_size_x_spinbox.setValue(10.0)
        self._custom_size_x_spinbox.setEnabled(False)
        self._custom_size_y_spinbox = QDoubleSpinBox()
        self._custom_size_y_spinbox.setValue(10.0)
        self._custom_size_y_spinbox.setEnabled(False)
        self._hoop_custom_radio.toggled.connect(self._custom_size_x_spinbox.setEnabled)
        self._hoop_custom_radio.toggled.connect(self._custom_size_y_spinbox.setEnabled)

        custom_layout = QHBoxLayout()
        custom_layout.addWidget(self._hoop_custom_radio)
        custom_layout.addWidget(self._custom_size_x_spinbox)
        custom_layout.addWidget(self._custom_size_y_spinbox)

        self._hoop_group.addWidget(self._hoop_4_4_radio)
        self._hoop_group.addWidget(self._hoop_5_7_radio)
        self._hoop_group.addWidget(self._hoop_7_5_radio)
        self._hoop_group.addWidget(self._hoop_6_10_radio)
        self._hoop_group.addWidget(self._hoop_10_6_radio)
        self._hoop_group.addLayout(custom_layout)

        self._visibility_checkbox = QCheckBox(self.tr("Show Hoop Frame"))
        self._hoop_group.addWidget(self._visibility_checkbox)

        hoop_group_box.setLayout(self._hoop_group)  # Set the layout to the group box

        partition_color_group = QGroupBox(self.tr("Partition Color"))
        partition_color_vlayout = QVBoxLayout()
        partition_color_hlayout1 = QHBoxLayout()
        partition_color_hlayout2 = QHBoxLayout()
        label = QLabel(self.tr("Border color"))
        button = QPushButton()
        button.clicked.connect(functools.partial(self._on_choose_color, ColorType.FOREGROUND))
        partition_color_hlayout1.addWidget(label)
        partition_color_hlayout1.addWidget(button)
        self._colors[ColorType.FOREGROUND]["label"] = label
        self._colors[ColorType.FOREGROUND]["button"] = button
        self._update_color_label(ColorType.FOREGROUND)

        label = QLabel(self.tr("Background color"))
        button = QPushButton()
        button.clicked.connect(functools.partial(self._on_choose_color, ColorType.BACKGROUND))
        partition_color_hlayout2.addWidget(label)
        partition_color_hlayout2.addWidget(button)
        self._colors[ColorType.BACKGROUND]["label"] = label
        self._colors[ColorType.BACKGROUND]["button"] = button
        self._update_color_label(ColorType.BACKGROUND)

        partition_color_vlayout.addLayout(partition_color_hlayout1)
        partition_color_vlayout.addLayout(partition_color_hlayout2)
        partition_color_group.setLayout(partition_color_vlayout)

        self._open_file_startup_checkbox = QCheckBox(self.tr("Open latest file on startup"))

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(hoop_group_box)  # Add the group box to the main layout
        main_layout.addWidget(partition_color_group)
        main_layout.addWidget(self._open_file_startup_checkbox)
        main_layout.addWidget(button_box)

        self.setLayout(main_layout)

        # Populate from global preferences
        hoop_visible = get_global_preferences().get_hoop_visible()

        # Pre-defined, convert it to integers so it is easier to match them
        hoop_size_i = (int(hoop_size[0]), int(hoop_size[1]))
        self._visibility_checkbox.setChecked(hoop_visible)

        d = {
            (4, 4): self._hoop_4_4_radio,
            (5, 7): self._hoop_5_7_radio,
            (7, 5): self._hoop_7_5_radio,
            (6, 10): self._hoop_6_10_radio,
            (10, 6): self._hoop_10_6_radio,
        }
        radio_button = None
        if hoop_size_i in d:
            radio_button = d[hoop_size_i]
        else:
            # FIXME: Preferences should save the custom hoop size in a different "bucket"
            # so that it should remember both things: which predefined is used, and the
            # custom value
            radio_button = self._hoop_custom_radio
            self._custom_size_x_spinbox.setValue(hoop_size[0])
            self._custom_size_y_spinbox.setValue(hoop_size[1])

        radio_button.setChecked(True)

        self._open_file_startup_checkbox.setChecked(
            get_global_preferences().get_open_file_on_startup()
        )

    def accept(self) -> None:
        super().accept()

        hoop_size = (0, 0)
        if self._hoop_4_4_radio.isChecked():
            hoop_size = (4, 4)
        elif self._hoop_5_7_radio.isChecked():
            hoop_size = (5, 7)
        elif self._hoop_7_5_radio.isChecked():
            hoop_size = (7, 5)
        elif self._hoop_6_10_radio.isChecked():
            hoop_size = (6, 10)
        elif self._hoop_10_6_radio.isChecked():
            hoop_size = (10, 6)
        elif self._hoop_custom_radio.isChecked():
            hoop_size = (
                self._custom_size_x_spinbox.value(),
                self._custom_size_y_spinbox.value(),
            )
        hoop_visible = self._visibility_checkbox.isChecked()
        prefs = get_global_preferences()
        prefs.set_hoop_size(hoop_size)
        prefs.set_hoop_visible(hoop_visible)
        prefs.set_open_file_on_startup(self._open_file_startup_checkbox.isChecked())
        prefs.set_partition_foreground_color(
            self._colors[ColorType.FOREGROUND]["color"].name(QColor.HexArgb)
        )
        prefs.set_partition_background_color(
            self._colors[ColorType.BACKGROUND]["color"].name(QColor.HexArgb)
        )

    @Slot()
    def _on_choose_color(self, color_type: ColorType):
        color = QColorDialog.getColor(options=QColorDialog.ShowAlphaChannel)
        if color.isValid():
            self._colors[color_type]["color"] = color
            self._update_color_label(color_type)

    def _update_color_label(self, color_type: ColorType):
        self._colors[color_type]["button"].setStyleSheet(
            f"background-color: {self._colors[color_type]['color'].name()};"
        )
        self._colors[color_type]["button"].setText(
            self._colors[color_type]["color"].name(QColor.HexArgb)
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = PreferenceDialog()
    if dialog.exec() == QDialog.Accepted:
        print("Dialog was accepted")
    elif dialog.exec() == QDialog.Rejected:
        print("Dialog was rejected")
    sys.exit(app.exec())
