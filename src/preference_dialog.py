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
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Preference Dialog")

        hoop_group_box = QGroupBox("Hoop Size (inches)")
        self.hoop_group = QVBoxLayout()
        self.hoop_4_4_radio = QRadioButton("4x4")
        self.hoop_5_7_radio = QRadioButton("5x7")
        self.hoop_7_5_radio = QRadioButton("7x5")
        self.hoop_6_10_radio = QRadioButton("6x10")
        self.hoop_10_6_radio = QRadioButton("10x6")
        self.hoop_custom_radio = QRadioButton("Custom:")
        self.custom_size_x_spinbox = QDoubleSpinBox()
        self.custom_size_x_spinbox.setEnabled(False)
        self.custom_size_x_spinbox.setValue(8.0)
        self.custom_size_y_spinbox = QDoubleSpinBox()
        self.custom_size_y_spinbox.setEnabled(False)
        self.custom_size_y_spinbox.setValue(8.0)
        self.hoop_custom_radio.toggled.connect(self.custom_size_x_spinbox.setEnabled)
        self.hoop_custom_radio.toggled.connect(self.custom_size_y_spinbox.setEnabled)

        custom_layout = QHBoxLayout()
        custom_layout.addWidget(self.hoop_custom_radio)
        custom_layout.addWidget(self.custom_size_x_spinbox)
        custom_layout.addWidget(self.custom_size_y_spinbox)

        self.hoop_group.addWidget(self.hoop_4_4_radio)
        self.hoop_group.addWidget(self.hoop_5_7_radio)
        self.hoop_group.addWidget(self.hoop_7_5_radio)
        self.hoop_group.addWidget(self.hoop_6_10_radio)
        self.hoop_group.addWidget(self.hoop_10_6_radio)
        self.hoop_group.addLayout(custom_layout)

        hoop_group_box.setLayout(self.hoop_group)  # Set the layout to the group box

        self.visibility_checkbox = QCheckBox("Show Hoop Frame")

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(hoop_group_box)  # Add the group box to the main layout
        main_layout.addWidget(self.visibility_checkbox)
        main_layout.addWidget(button_box)

        self.setLayout(main_layout)

        # Populate from global preferences
        hoop_visible = preferences.global_preferences.get_hoop_visible()
        hoop_size = preferences.global_preferences.get_hoop_size()
        self.visibility_checkbox.setChecked(hoop_visible)

        d = {
            (4, 4): self.hoop_4_4_radio,
            (5, 7): self.hoop_5_7_radio,
            (7, 5): self.hoop_7_5_radio,
            (6, 10): self.hoop_6_10_radio,
            (10, 6): self.hoop_10_6_radio,
        }
        radio_button = None
        if hoop_size in d:
            radio_button = d[hoop_size]
        else:
            radio_button = self.hoop_custom_radio
        radio_button.setChecked(True)

    def accept(self) -> None:
        super().accept()

        hoop_size = (0, 0)
        if self.hoop_4_4_radio.isChecked():
            hoop_size = (4, 4)
        elif self.hoop_5_7_radio.isChecked():
            hoop_size = (5, 7)
        elif self.hoop_7_5_radio.isChecked():
            hoop_size = (7, 5)
        elif self.hoop_6_10_radio.isChecked():
            hoop_size = (6, 10)
        elif self.hoop_10_6_radio.isChecked():
            hoop_size = (10, 6)
        elif self.hoop_custom_radio.isChecked():
            hoop_size = (
                self.custom_size_x_spinbox.value(),
                self.custom_size_y_spinbox.value(),
            )
        hoop_visible = self.visibility_checkbox.isChecked()
        preferences.global_preferences.set_hoop_size(hoop_size)
        preferences.global_preferences.set_hoop_visible(hoop_visible)
        print(hoop_visible)
        print(hoop_size)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = PreferenceDialog()
    if dialog.exec() == QDialog.DialogCode.Accepted:
        print("Dialog was accepted")
    elif dialog.exec() == QDialog.DialogCode.Rejected:
        print("Dialog was rejected")
    sys.exit(app.exec())
