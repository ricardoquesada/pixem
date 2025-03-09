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

from export import ExportParameters


class ExportDialog(QDialog):
    def __init__(self, export_parameters: ExportParameters, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Export As Dialog")

        layout = QVBoxLayout()

        # File Name
        file_layout = QHBoxLayout()
        file_label = QLabel("File Name:")
        self._file_edit = QLineEdit()
        self._file_edit.setText(export_parameters.filename)
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
            if export_parameters.fill_method == item:
                self._fill_method_combo.setCurrentIndex(self._fill_method_combo.count() - 1)
        fill_method_layout.addWidget(fill_method_label)
        fill_method_layout.addWidget(self._fill_method_combo)
        layout.addLayout(fill_method_layout)

        # Pull Compensation
        pull_layout = QHBoxLayout()
        pull_label = QLabel("Pull Compensation (mm):")
        self._pull_spinbox = QDoubleSpinBox()
        self._pull_spinbox.setValue(export_parameters.pull_compensation_mm)
        pull_layout.addWidget(pull_label)
        pull_layout.addWidget(self._pull_spinbox)
        layout.addLayout(pull_layout)

        # Max Stitch Length
        max_stitch_layout = QHBoxLayout()
        max_stitch_label = QLabel("Max Stitch Length (mm):")
        self._max_stitch_spinbox = QDoubleSpinBox()
        self._max_stitch_spinbox.setRange(0.1, 2000.0)
        self._max_stitch_spinbox.setValue(export_parameters.max_stitch_length_mm)
        max_stitch_layout.addWidget(max_stitch_label)
        max_stitch_layout.addWidget(self._max_stitch_spinbox)
        layout.addLayout(max_stitch_layout)

        # Angle
        angle_layout = QHBoxLayout()
        angle_label = QLabel("Initial Angle (degrees):")
        self._angle_spinbox = QSpinBox()
        self._angle_spinbox.setRange(0, 89)
        self._angle_spinbox.setValue(export_parameters.initial_angle_degrees)
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
            _, ext = os.path.splitext(filename)
            if ext != ".svg":
                filename = filename + ".svg"
            self._file_edit.setText(filename)

    def get_export_parameters(self) -> ExportParameters:
        return ExportParameters(
            filename=self._file_edit.text(),
            pull_compensation_mm=self._pull_spinbox.value(),
            max_stitch_length_mm=self._max_stitch_spinbox.value(),
            fill_method=self._fill_method_combo.currentData(),
            initial_angle_degrees=self._angle_spinbox.value(),
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    params = ExportParameters(
        filename="test filename",
        pull_compensation_mm=10.0,
        max_stitch_length_mm=100,
        fill_method="auto_fill",
        initial_angle_degrees=0,
    )
    dialog = ExportDialog(params)

    if dialog.exec() == QDialog.Accepted:
        params = dialog.get_export_parameters()
        print(params)
    else:
        print("Dialog canceled.")
    sys.exit(app.exec())
