# Pixem
# Copyright 2025 - Ricardo Quesada


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
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self._image: QImage | None = None

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("white"))  # fill the widget with white.
        painter.scale(DEFAULT_SCALE_FACTOR, DEFAULT_SCALE_FACTOR)
        if self._image is not None:
            painter.drawImage(0, 0, self._image)
        painter.end()

    def sizeHint(self) -> QSize:
        if self._image is None:
            return QSize(40 * DEFAULT_SCALE_FACTOR, 8 * DEFAULT_SCALE_FACTOR)
        return QSize(
            self._image.width() * DEFAULT_SCALE_FACTOR + 2,
            self._image.height() * DEFAULT_SCALE_FACTOR + 2,
        )

    def set_image(self, image: QImage):
        self._image = image
        self.updateGeometry()
        new_size = self.sizeHint()
        self.setFixedSize(new_size)
        self.update()


class FontDialog(QDialog):
    def __init__(
        self,
        text: str | None = None,
        font_name: str | None = None,
        color_name: str | None = None,
        parent=None,
    ):
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
        self._color_button.clicked.connect(self._choose_color)
        if color_name is not None:
            self._color = QColor(color_name)
        else:
            self._color = QColor(Qt.black)
        self._color_label = QLabel()
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
        color_layout.addWidget(self._color_button)
        color_layout.addWidget(self._color_label)

        main_layout.addWidget(self._canvas)
        main_layout.addLayout(text_layout)
        main_layout.addLayout(font_layout)
        main_layout.addLayout(color_layout)
        main_layout.addWidget(button_box)

        if text is not None:
            self._regenerate_image()

        self.setLayout(main_layout)

    def _update_color_label(self):
        self._color_button.setText(self.tr(f"Choose Color: {self._color.name()}"))
        self._color_label.setStyleSheet(f"background-color: {self._color.name()};")

    def _choose_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self._color = color
            self._update_color_label()
            self._regenerate_image()

    def _regenerate_image(self):
        image = image_utils.text_to_qimage(
            self._text_edit.text(), self._font_combo.currentData(), self._color.name()
        )
        self._canvas.set_image(image)

    @Slot()
    def _on_text_changed(self, txt: str):
        self._regenerate_image()

    @Slot()
    def _current_index_changed_combobox(self):
        self._regenerate_image()

    def get_data(self):
        """
        Returns the selected text, font, color.

        Returns:
            tuple: A tuple containing the text, font name, color.
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
