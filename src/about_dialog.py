# Pixem
# Copyright 2025 - Ricardo Quesada

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QDialog, QDialogButtonBox, QLabel, QVBoxLayout

VERSION = "0.1.0"


class AboutDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("About Pixem")

        # Create an icon label
        icon_label = QLabel()
        pixmap = QPixmap(":/logo512.png")  # Replace with your icon path
        icon_label.setPixmap(pixmap)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Center the icon

        # Create a label for the description
        description_label = QLabel(
            f"""
            <p><b>Pixem</b></p>
            <p>A pixel-art to machine-embroidery application</p>
            <p>Version {VERSION}</p>
            <p>Copyright (c) 2024-2025 Ricardo Quesada</p>
            <a href="https://github.com/ricardoquesada/pixem">https://github.com/ricardoquesada/pixem</a>
            """
        )
        description_label.setWordWrap(True)  # Enable word wrap
        description_label.setTextFormat(Qt.RichText)
        description_label.setOpenExternalLinks(True)

        # Create an "OK" button
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(self.accept)

        # Create layout and add widgets
        layout = QVBoxLayout()
        layout.addWidget(icon_label)
        layout.addWidget(description_label)
        layout.addWidget(button_box)

        self.setLayout(layout)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = AboutDialog()
    dialog.exec()
    sys.exit(app.exec())
