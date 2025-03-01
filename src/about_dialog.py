# Pixem
# Copyright 2025 - Ricardo Quesada

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QDialog, QDialogButtonBox, QLabel, QVBoxLayout

import resources_rc  # noqa: F401


class AboutDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("About Pixel Editor")

        # Create an icon label
        icon_label = QLabel()
        pixmap = QPixmap(":/res/logo512.png")  # Replace with your icon path
        icon_label.setPixmap(pixmap)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Center the icon

        # Create a label for the description
        description_label = QLabel(
            """
            <p><b>Pixem</b></p>
            <p>A simple and fun pixel editor application.</p>
            <p>Version 1.0</p>
            <p>Copyright (c) 2024 Ricardo Quesada</p>
            """
        )
        description_label.setWordWrap(True)  # Enable word wrap

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
