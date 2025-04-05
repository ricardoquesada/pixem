# Pixem
# Copyright 2025 - Ricardo Quesada

import functools
import logging
import sys
from enum import IntEnum, auto
from typing import override

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
    PARTITION_FOREGROUND = auto()
    PARTITION_BACKGROUND = auto()
    CANVAS_BACKGROUND = auto()
    HOOP_FOREGROUND = auto()


class PreferenceDialog(QDialog):
    def __init__(self, hoop_size: tuple[float, float]):
        super().__init__()

        self._colors = {
            ColorType.PARTITION_FOREGROUND: {},
            ColorType.PARTITION_BACKGROUND: {},
            ColorType.CANVAS_BACKGROUND: {},
            ColorType.HOOP_FOREGROUND: {},
        }
        self._colors[ColorType.PARTITION_FOREGROUND]["color"] = QColor(
            get_global_preferences().get_partition_foreground_color_name()
        )
        self._colors[ColorType.PARTITION_BACKGROUND]["color"] = QColor(
            get_global_preferences().get_partition_background_color_name()
        )
        self._colors[ColorType.CANVAS_BACKGROUND]["color"] = QColor(
            get_global_preferences().get_canvas_background_color_name()
        )
        self._colors[ColorType.HOOP_FOREGROUND]["color"] = QColor(
            get_global_preferences().get_hoop_color_name()
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

        canvas_color_group = QGroupBox(self.tr("Canvas Color"))
        canvas_color_vlayout = QVBoxLayout()
        canvas_color_hlayout1 = QHBoxLayout()
        canvas_color_hlayout2 = QHBoxLayout()
        label = QLabel(self.tr("Background color"))
        button = QPushButton()
        button.clicked.connect(
            functools.partial(self._on_choose_color, ColorType.CANVAS_BACKGROUND)
        )
        canvas_color_hlayout1.addWidget(label)
        canvas_color_hlayout1.addWidget(button)
        self._colors[ColorType.CANVAS_BACKGROUND]["label"] = label
        self._colors[ColorType.CANVAS_BACKGROUND]["button"] = button
        self._update_color_label(ColorType.CANVAS_BACKGROUND)

        label = QLabel(self.tr("Hoop color"))
        button = QPushButton()
        button.clicked.connect(functools.partial(self._on_choose_color, ColorType.HOOP_FOREGROUND))
        canvas_color_hlayout2.addWidget(label)
        canvas_color_hlayout2.addWidget(button)
        self._colors[ColorType.HOOP_FOREGROUND]["label"] = label
        self._colors[ColorType.HOOP_FOREGROUND]["button"] = button
        self._update_color_label(ColorType.HOOP_FOREGROUND)

        canvas_color_vlayout.addLayout(canvas_color_hlayout1)
        canvas_color_vlayout.addLayout(canvas_color_hlayout2)
        canvas_color_group.setLayout(canvas_color_vlayout)

        partition_color_group = QGroupBox(self.tr("Partition Color"))
        partition_color_vlayout = QVBoxLayout()
        partition_color_hlayout1 = QHBoxLayout()
        partition_color_hlayout2 = QHBoxLayout()
        label = QLabel(self.tr("Foreground color"))
        button = QPushButton()
        button.clicked.connect(
            functools.partial(self._on_choose_color, ColorType.PARTITION_FOREGROUND)
        )
        partition_color_hlayout1.addWidget(label)
        partition_color_hlayout1.addWidget(button)
        self._colors[ColorType.PARTITION_FOREGROUND]["label"] = label
        self._colors[ColorType.PARTITION_FOREGROUND]["button"] = button
        self._update_color_label(ColorType.PARTITION_FOREGROUND)

        label = QLabel(self.tr("Background color"))
        button = QPushButton()
        button.clicked.connect(
            functools.partial(self._on_choose_color, ColorType.PARTITION_BACKGROUND)
        )
        partition_color_hlayout2.addWidget(label)
        partition_color_hlayout2.addWidget(button)
        self._colors[ColorType.PARTITION_BACKGROUND]["label"] = label
        self._colors[ColorType.PARTITION_BACKGROUND]["button"] = button
        self._update_color_label(ColorType.PARTITION_BACKGROUND)

        partition_color_vlayout.addLayout(partition_color_hlayout1)
        partition_color_vlayout.addLayout(partition_color_hlayout2)
        partition_color_group.setLayout(partition_color_vlayout)

        self._open_file_startup_checkbox = QCheckBox(self.tr("Open latest file on startup"))

        # Buttons
        self._button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply
        )
        self._button_box.accepted.connect(self.accept)
        self._button_box.rejected.connect(self.reject)
        self._button_box.clicked.connect(self._on_buttonbox_button_clicked)

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(hoop_group_box)  # Add the group box to the main layout
        main_layout.addWidget(canvas_color_group)
        main_layout.addWidget(partition_color_group)
        main_layout.addWidget(self._open_file_startup_checkbox)
        main_layout.addWidget(self._button_box)

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

    def _apply(self) -> None:
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
        prefs.set_partition_foreground_color_name(
            self._colors[ColorType.PARTITION_FOREGROUND]["color"].name(QColor.HexArgb)
        )
        prefs.set_partition_background_color_name(
            self._colors[ColorType.PARTITION_BACKGROUND]["color"].name(QColor.HexArgb)
        )
        prefs.set_canvas_background_color_name(
            self._colors[ColorType.CANVAS_BACKGROUND]["color"].name(QColor.HexArgb)
        )
        prefs.set_hoop_color_name(
            self._colors[ColorType.HOOP_FOREGROUND]["color"].name(QColor.HexArgb)
        )

    def _update_color_label(self, color_type: ColorType):
        self._colors[color_type]["button"].setStyleSheet(
            f"background-color: {self._colors[color_type]['color'].name()};"
        )
        self._colors[color_type]["button"].setText(
            self._colors[color_type]["color"].name(QColor.HexArgb)
        )

    @override
    def accept(self) -> None:
        self._apply()
        super().accept()

    @Slot()
    def _on_buttonbox_button_clicked(self, button: QPushButton):
        # Ignore "Cancel" and "Ok" which have their own slots
        if button == self._button_box.button(QDialogButtonBox.Apply):
            self._apply()

    @Slot()
    def _on_choose_color(self, color_type: ColorType):
        color = QColorDialog.getColor(options=QColorDialog.ShowAlphaChannel)
        if color.isValid():
            self._colors[color_type]["color"] = color
            self._update_color_label(color_type)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = PreferenceDialog((4, 4))
    if dialog.exec() == QDialog.Accepted:
        print("Dialog was accepted")
    elif dialog.exec() == QDialog.Rejected:
        print("Dialog was rejected")
    sys.exit(app.exec())
