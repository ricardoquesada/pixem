import os
import sys

from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)


class ExportDialog(QDialog):
    def __init__(
        self,
        export_filename: str,
        pull_compensation: float,
        max_stitch_length: float = 1000.0,
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
