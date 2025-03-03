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


class SaveFileDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Save File Dialog")

        layout = QVBoxLayout()

        # File Name
        file_layout = QHBoxLayout()
        file_label = QLabel("File Name:")
        self.file_edit = QLineEdit()
        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self.browse_file)

        file_layout.addWidget(file_label)
        file_layout.addWidget(self.file_edit)
        file_layout.addWidget(self.browse_button)
        layout.addLayout(file_layout)

        # Pull Compensation
        pull_layout = QHBoxLayout()
        pull_label = QLabel("Pull Compensation (mm):")
        self.pull_spinbox = QDoubleSpinBox()
        pull_layout.addWidget(pull_label)
        pull_layout.addWidget(self.pull_spinbox)
        layout.addLayout(pull_layout)

        # Create QDialogButtonBox
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def browse_file(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Save File")
        if file_name:
            self.file_edit.setText(file_name)

    def get_file_name(self):
        return self.file_edit.text()

    def get_pull_compensation(self):
        return self.pull_spinbox.value()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = SaveFileDialog()

    if dialog.exec() == QDialog.Accepted:
        file_name = dialog.get_file_name()
        pull_compensation = dialog.get_pull_compensation()
        print(f"File Name: {file_name}")
        print(f"Pull Compensation: {pull_compensation}")
    else:
        print("Dialog canceled.")
    sys.exit(app.exec())
