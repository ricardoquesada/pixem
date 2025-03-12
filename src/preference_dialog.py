# Pixem
# Copyright 2025 - Ricardo Quesada

import sys

from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QRadioButton,
    QVBoxLayout,
)

import preferences


class PreferenceDialog(QDialog):
    def __init__(self, hoop_size: tuple[float, float]):
        super().__init__()

        self.setWindowTitle("Preference Dialog")

        hoop_group_box = QGroupBox("Hoop Size (inches)")
        self._hoop_group = QVBoxLayout()
        self._hoop_4_4_radio = QRadioButton("4x4")
        self._hoop_5_7_radio = QRadioButton("5x7")
        self._hoop_7_5_radio = QRadioButton("7x5")
        self._hoop_6_10_radio = QRadioButton("6x10")
        self._hoop_10_6_radio = QRadioButton("10x6")
        self._hoop_custom_radio = QRadioButton("Custom:")
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

        self._visibility_checkbox = QCheckBox("Show Hoop Frame")
        self._hoop_group.addWidget(self._visibility_checkbox)

        hoop_group_box.setLayout(self._hoop_group)  # Set the layout to the group box

        self._open_file_startup_checkbox = QCheckBox("Open file on startup")

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(hoop_group_box)  # Add the group box to the main layout
        main_layout.addWidget(self._open_file_startup_checkbox)
        main_layout.addWidget(button_box)

        self.setLayout(main_layout)

        # Populate from global preferences
        hoop_visible = preferences.global_preferences.get_hoop_visible()

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
            preferences.global_preferences.get_open_file_on_startup()
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
        preferences.global_preferences.set_hoop_size(hoop_size)
        preferences.global_preferences.set_hoop_visible(hoop_visible)
        preferences.global_preferences.set_open_file_on_startup(
            self._open_file_startup_checkbox.isChecked()
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = PreferenceDialog()
    if dialog.exec() == QDialog.Accepted:
        print("Dialog was accepted")
    elif dialog.exec() == QDialog.Rejected:
        print("Dialog was rejected")
    sys.exit(app.exec())
