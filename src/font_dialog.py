# Pixem
# Copyright 2025 - Ricardo Quesada

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)


class FontDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Font Selection")

        # Create widgets
        self.text_label = QLabel("Text:")
        self.text_edit = QLineEdit()
        self.font_label = QLabel("Font:")
        self.font_combo = QComboBox()
        self.font_combo.addItem("PETSCII (Commodore 8-bit)", ":/res/fonts/petscii-charset.bin")
        self.font_combo.addItem("ATASCII (Atari 8-bit)", ":/res/fonts/atascii-charset.bin")

        # Create QDialogButtonBox
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        # Create layouts
        main_layout = QVBoxLayout()
        text_layout = QHBoxLayout()
        text_layout.addWidget(self.text_label)
        text_layout.addWidget(self.text_edit)
        font_layout = QHBoxLayout()
        font_layout.addWidget(self.font_label)
        font_layout.addWidget(self.font_combo)

        main_layout.addLayout(text_layout)
        main_layout.addLayout(font_layout)
        main_layout.addWidget(button_box)

        self.setLayout(main_layout)

    def get_data(self):
        """
        Returns the selected text and font.

        Returns:
            tuple: A tuple containing the text and font name.
        """
        text = self.text_edit.text()
        font_name = self.font_combo.currentData(Qt.UserRole)
        return text, font_name


if __name__ == "__main__":
    app = QApplication([])
    dialog = FontDialog()
    if dialog.exec_() == QDialog.Accepted:
        text, font_name = dialog.get_data()
        print(f"Selected Text: {text}")
        print(f"Selected Font: {font_name}")
    app.exec()
