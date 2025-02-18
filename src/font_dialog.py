from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
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
        self.font_combo.addItems(["PETSCII (Commodore 8-bit)", "ATASCII (Atari 8-bit)"])
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")

        # Connect signals
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        # Create layouts
        main_layout = QVBoxLayout()
        text_layout = QHBoxLayout()
        text_layout.addWidget(self.text_label)
        text_layout.addWidget(self.text_edit)
        font_layout = QHBoxLayout()
        font_layout.addWidget(self.font_label)
        font_layout.addWidget(self.font_combo)
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)

        main_layout.addLayout(text_layout)
        main_layout.addLayout(font_layout)
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

    def get_data(self):
        """
        Returns the selected text and font.

        Returns:
            tuple: A tuple containing the text and font name.
        """
        text = self.text_edit.text()
        font_name = self.font_combo.currentText()
        return text, font_name


if __name__ == "__main__":
    app = QApplication([])
    dialog = FontDialog()
    if dialog.exec_() == QDialog.Accepted:
        text, font_name = dialog.get_data()
        print(f"Selected Text: {text}")
        print(f"Selected Font: {font_name}")
    app.exec()
