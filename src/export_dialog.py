# Pixem
# Copyright 2025 Ricardo Quesada

import os
import sys

from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)


class ExportDialog(QDialog):
    def __init__(
        self,
        export_filename: str,
        pull_compensation: float,
        max_stitch_length: float = 1000.0,
        fill_method: str = "auto_fill",
        angle: int = 0,
        parent=None,
    ):
        super().__init__(parent)

        self.setWindowTitle("Export As Dialog")

        layout = QVBoxLayout()

        # File Name
        file_layout = QHBoxLayout()
        file_label = QLabel("File Name:")
        self._file_edit = QLineEdit()
        self._file_edit.setText(export_filename)
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self._on_browse_file)

        file_layout.addWidget(file_label)
        file_layout.addWidget(self._file_edit)
        file_layout.addWidget(browse_button)
        layout.addLayout(file_layout)

        # Fill method
        fill_method_layout = QHBoxLayout()
        fill_method_label = QLabel("Fill Method:")
        self._fill_method_combo = QComboBox()

        items = {
            "auto_fill": "Auto Fill",
            "legacy_fill": "Legacy Fill",
        }
        for item in items:
            self._fill_method_combo.addItem(items[item], item)
            if fill_method == item:
                self._fill_method_combo.setCurrentIndex(self._fill_method_combo.count() - 1)
        fill_method_layout.addWidget(fill_method_label)
        fill_method_layout.addWidget(self._fill_method_combo)
        layout.addLayout(fill_method_layout)

        # Pull Compensation
        pull_layout = QHBoxLayout()
        pull_label = QLabel("Pull Compensation (mm):")
        self._pull_spinbox = QDoubleSpinBox()
        self._pull_spinbox.setValue(pull_compensation)
        pull_layout.addWidget(pull_label)
        pull_layout.addWidget(self._pull_spinbox)
        layout.addLayout(pull_layout)

        # Max Stitch Length
        max_stitch_layout = QHBoxLayout()
        max_stitch_label = QLabel("Max Stitch Length (mm):")
        self._max_stitch_spinbox = QDoubleSpinBox()
        self._max_stitch_spinbox.setRange(0.1, 2000.0)
        self._max_stitch_spinbox.setValue(max_stitch_length)
        max_stitch_layout.addWidget(max_stitch_label)
        max_stitch_layout.addWidget(self._max_stitch_spinbox)
        layout.addLayout(max_stitch_layout)

        # Angle
        angle_layout = QHBoxLayout()
        angle_label = QLabel("Initial Angle (degrees):")
        self._angle_spinbox = QSpinBox()
        self._angle_spinbox.setRange(0, 89)
        self._angle_spinbox.setValue(angle)
        angle_layout.addWidget(angle_label)
        angle_layout.addWidget(self._angle_spinbox)
        layout.addLayout(angle_layout)

        # Create QDialogButtonBox
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def _on_browse_file(self):
        dirname = os.path.dirname(self._file_edit.text())
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Project", dirname, "SVG (*.svg);;All files (*)"
        )
        if filename:
            self._file_edit.setText(filename)

    def get_file_name(self):
        return self._file_edit.text()

    def get_pull_compensation(self):
        return self._pull_spinbox.value()

    def get_max_stitch_length(self):
        return self._max_stitch_spinbox.value()

    def get_initial_angle(self):
        return self._angle_spinbox.value()

    def get_fill_method(self):
        return self._fill_method_combo.currentData()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = ExportDialog("test filename", 10.0, 100)

    if dialog.exec() == QDialog.Accepted:
        file_name = dialog.get_file_name()
        pull_compensation = dialog.get_pull_compensation()
        print(f"File Name: {file_name}")
        print(f"Pull Compensation: {pull_compensation}")
    else:
        print("Dialog canceled.")
    sys.exit(app.exec())
