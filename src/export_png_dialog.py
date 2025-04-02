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


class ExportPngDialog(QDialog):
    def __init__(self, filename: str, parent=None):
        super().__init__(parent)

        self.setWindowTitle(self.tr("Export PNG As Dialog"))

        layout = QVBoxLayout()

        # File Name
        file_layout = QHBoxLayout()
        file_label = QLabel(self.tr("File Name:"))
        self._file_edit = QLineEdit()
        self._file_edit.setText(filename)
        browse_button = QPushButton(self.tr("Browse..."))
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
            self, self.tr("Export Project"), dirname, self.tr("PNG (*.png);;All files (*)")
        )
        if filename:
            _, ext = os.path.splitext(filename)
            if ext != ".png":
                filename = filename + ".png"
            self._file_edit.setText(filename)

    def get_filename(self) -> str:
        return self._file_edit.text()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = ExportPngDialog("test.png")

    if dialog.exec() == QDialog.Accepted:
        filename = dialog.get_filename()
        print(filename)
    else:
        print("Dialog canceled.")
    sys.exit(app.exec())
