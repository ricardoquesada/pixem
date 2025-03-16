# Pixem
# Copyright 2025 Ricardo Quesada

import os
import sys

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from export import ExportParameters


class ExportDialog(QDialog):
    def __init__(self, filename: str, parent=None):
        super().__init__(parent)

        self.setWindowTitle(self.tr("Export As Dialog"))

        layout = QVBoxLayout()

        # File Name
        file_layout = QHBoxLayout()
        file_label = QLabel(self.tr("File Name:"))
        self._file_edit = QLineEdit()
        self._file_edit.setText(filename)
        browse_button = QPushButton(self.tr("Browse"))
        browse_button.clicked.connect(self._on_browse_file)

        file_layout.addWidget(file_label)
        file_layout.addWidget(self._file_edit)
        file_layout.addWidget(browse_button)
        layout.addLayout(file_layout)

        # Create QDialogButtonBox
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

    @Slot()
    def _on_browse_file(self):
        dirname = os.path.dirname(self._file_edit.text())
        filename, _ = QFileDialog.getSaveFileName(
            self, self.tr("Export Project"), dirname, self.tr("SVG (*.svg);;All files (*)")
        )
        if filename:
            _, ext = os.path.splitext(filename)
            if ext != ".svg":
                filename = filename + ".svg"
            self._file_edit.setText(filename)

    def get_filename(self) -> str:
        return self._file_edit.text()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    params = ExportParameters(
        filename="test filename",
        pull_compensation_mm=10.0,
        max_stitch_length_mm=100,
        fill_method="auto_fill",
        initial_angle_degrees=0,
    )
    dialog = ExportDialog("test.svg")

    if dialog.exec() == QDialog.Accepted:
        params = dialog.get_filename()
        print(params)
    else:
        print("Dialog canceled.")
    sys.exit(app.exec())
