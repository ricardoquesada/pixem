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
        self.setWindowTitle(self.tr("Font Selection"))

        # Create widgets
        self._text_label = QLabel(self.tr("Text:"))
        self._text_edit = QLineEdit()
        self._font_label = QLabel(self.tr("Font:"))
        self._font_combo = QComboBox()
        self._font_combo.addItem(
            self.tr("PETSCII (Commodore 8-bit)"), ":/fonts/petscii-charset.bin"
        )
        self._font_combo.addItem(self.tr("ATASCII (Atari 8-bit)"), ":/fonts/atascii-charset.bin")

        # Create QDialogButtonBox
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        # Create layouts
        main_layout = QVBoxLayout()
        text_layout = QHBoxLayout()
        text_layout.addWidget(self._text_label)
        text_layout.addWidget(self._text_edit)
        font_layout = QHBoxLayout()
        font_layout.addWidget(self._font_label)
        font_layout.addWidget(self._font_combo)

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
        text = self._text_edit.text()
        font_name = self._font_combo.currentData(Qt.UserRole)
        return text, font_name


if __name__ == "__main__":
    app = QApplication([])
    dialog = FontDialog()
    if dialog.exec() == QDialog.Accepted:
        text, font_name = dialog.get_data()
        print(f"Selected Text: {text}")
        print(f"Selected Font: {font_name}")
    app.exec()
