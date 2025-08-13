# Pixem
# Copyright 2025 - Ricardo Quesada

"""
A dialog for selecting text, a font, and a color to create a text-based layer.

This module provides a FontDialog class that allows users to input text,
choose from a predefined list of 8-bit fonts, and select a color. It displays
a live preview of the rendered text.
"""


from PySide6.QtCore import QSize, Qt, Slot
from PySide6.QtGui import QColor, QImage, QPainter, QPaintEvent
from PySide6.QtWidgets import (
    QApplication,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import image_utils

DEFAULT_SCALE_FACTOR = 5


class FontCanvas(QWidget):
    """A widget that displays a preview of the rendered text."""

    def __init__(self, parent: QWidget = None):
        """
        Initializes the FontCanvas widget.

        Args:
            parent: The parent widget.
        """
        super().__init__(parent)
        self._image: QImage | None = None

    def paintEvent(self, event: QPaintEvent) -> None:
        """Handles the paint event to draw the preview image."""
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("white"))  # fill the widget with white.
        painter.scale(DEFAULT_SCALE_FACTOR, DEFAULT_SCALE_FACTOR)
        if self._image is not None:
            painter.drawImage(0, 0, self._image)
        painter.end()

    def sizeHint(self) -> QSize:
        """Provides a recommended size for the widget based on the image size."""
        if self._image is None:
            return QSize(40 * DEFAULT_SCALE_FACTOR, 8 * DEFAULT_SCALE_FACTOR)
        return QSize(
            self._image.width() * DEFAULT_SCALE_FACTOR + 2,
            self._image.height() * DEFAULT_SCALE_FACTOR + 2,
        )

    def set_image(self, image: QImage):
        """
        Sets the image to be displayed on the canvas and updates the widget's geometry.

        Args:
            image: The QImage to display.
        """
        self._image = image
        self.updateGeometry()
        new_size = self.sizeHint()
        self.setFixedSize(new_size)
        self.update()


class FontDialog(QDialog):
    """
    A dialog for users to enter text, select a font, and choose a color.

    It provides a live preview of the text as the user changes the options.
    The selected data can be retrieved to create a new text-based layer.
    """

    def __init__(
        self,
        text: str | None = None,
        font_name: str | None = None,
        color_name: str | None = None,
        parent=None,
    ):
        """
        Initializes the FontDialog.

        Args:
            text: The initial text to display.
            font_name: The resource path of the initial font to select.
            color_name: The name of the initial color (e.g., '#RRGGBB').
            parent: The parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle(self.tr("Font Selection"))

        # Create widgets
        self._canvas = FontCanvas()
        self._text_label = QLabel(self.tr("Text:"))
        self._text_edit = QLineEdit()
        if text is not None:
            self._text_edit.setText(text)
        self._text_edit.textChanged.connect(self._on_text_changed)

        self._font_label = QLabel(self.tr("Font:"))
        self._font_combo = QComboBox()
        items = (
            (self.tr("PETSCII (Commodore 8-bit)"), ":/fonts/petscii-charset.bin"),
            (self.tr("ATASCII (Atari 8-bit)"), ":/fonts/atascii-charset.bin"),
        )
        for item in items:
            self._font_combo.addItem(item[0], item[1])
            if font_name == item[1]:
                self._font_combo.setCurrentIndex(self._font_combo.count() - 1)
        self._font_combo.currentIndexChanged.connect(self._current_index_changed_combobox)

        self._color_button = QPushButton()
        self._color_button.clicked.connect(self._on_choose_color)
        if color_name is not None:
            self._color = QColor(color_name)
        else:
            self._color = QColor(Qt.black)
        self._color_label = QLabel(self.tr("Color:"))
        self._update_color_label()

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

        color_layout = QHBoxLayout()
        color_layout.addWidget(self._color_label)
        color_layout.addWidget(self._color_button)

        main_layout.addWidget(self._canvas)
        main_layout.addLayout(text_layout)
        main_layout.addLayout(font_layout)
        main_layout.addLayout(color_layout)
        main_layout.addWidget(button_box)

        if text is not None:
            self._regenerate_image()

        self.setLayout(main_layout)

    def _update_color_label(self):
        """Updates the color button's text and background color."""
        self._color_button.setText(self.tr(f"{self._color.name()}"))
        self._color_button.setStyleSheet(f"background-color: {self._color.name()};")

    def _regenerate_image(self):
        """
        Renders the current text with the selected font and color,
        and updates the canvas preview.
        """
        image = image_utils.text_to_qimage(
            self._text_edit.text(), self._font_combo.currentData(), self._color.name()
        )
        self._canvas.set_image(image)

    @Slot()
    def _on_choose_color(self):
        """
        Slot that opens a color dialog when the color button is clicked
        and updates the preview if a valid color is chosen.
        """
        color = QColorDialog.getColor()
        if color.isValid():
            self._color = color
            self._update_color_label()
            self._regenerate_image()

    @Slot()
    def _on_text_changed(self, txt: str):
        """
        Slot that regenerates the preview image when the text is changed.

        Args:
            txt: The new text from the QLineEdit widget (unused).
        """
        self._regenerate_image()

    @Slot()
    def _current_index_changed_combobox(self):
        """Slot that regenerates the preview image when the font selection changes."""
        self._regenerate_image()

    def get_data(self) -> tuple[str, str, str]:
        """
        Returns the selected text, font, and color.

        Returns:
            A tuple containing the text (str), font resource name (str),
            and color name (str).
        """
        text = self._text_edit.text()
        font_name = self._font_combo.currentData(Qt.UserRole)
        color = self._color.name()
        return text, font_name, color


if __name__ == "__main__":
    app = QApplication([])
    dialog = FontDialog()
    if dialog.exec() == QDialog.Accepted:
        text, font_name = dialog.get_data()
        print(f"Selected Text: {text}")
        print(f"Selected Font: {font_name}")
    app.exec()
