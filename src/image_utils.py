# Pixem
# Copyright 2024 - Ricardo Quesada

import base64
import logging
from typing import Optional

from PySide6.QtCore import QBuffer, QByteArray, QFile, QIODevice, Qt
from PySide6.QtGui import QColor, QImage

logger = logging.getLogger(__name__)  # __name__ gets the current module's name


def qimage_to_base64_string(image: QImage, fmt: str = "PNG") -> str | None:
    """
    Encodes a QImage to a Base64 string representing the image in the specified format.

    Args:
        image: The QImage to encode.
        fmt: The image format to use (e.g., "PNG", "JPEG", "BMP"). Defaults to "PNG".

    Returns:
        A Base64 string representing the encoded image, or an empty string if an error occurs.
    """
    if image is None:
        logger.info("Image is None, returning empty Image")
        return None

    try:
        byte_array = QByteArray()
        buffer = QBuffer(byte_array)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        image.save(buffer, fmt)
        encoded_string = base64.b64encode(byte_array.data()).decode("utf-8")
        return encoded_string
    except Exception as e:
        logger.error(f"Error encoding QImage: {e}")
        return ""


def base64_string_to_qimage(base64_string: str) -> QImage:
    """
    Decodes a Base64 string to a QImage.

    Args:
        base64_string: The Base64 string representing the image.

    Returns:
        A QImage, or a null QImage if an error occurs.
    """
    try:
        image_bytes = base64.b64decode(base64_string)
        qimage = QImage()
        qimage.loadFromData(QByteArray(image_bytes))
        return qimage
    except Exception as e:
        logger.error(f"Error decoding Base64 string: {e}")
        return QImage()  # Return a null QImage on error


def _paint_row(image: QImage, data: int, offset_x: int, offset_y: int) -> None:
    for b in range(8):
        if data & (1 << (8 - b)):
            image.setPixel(offset_x + b, offset_y, QColor(Qt.black).rgb())


def text_to_qimage(text: str, font_path: str) -> Optional[QImage]:
    if text is None or len(text) == 0:
        return None
    if font_path is None or len(font_path) == 0:
        return None

    width = len(text) * 8
    height = 8
    image = QImage(width, height, QImage.Format_ARGB32)
    image.fill(Qt.transparent)

    file = QFile(font_path)
    if not file.open(QIODevice.OpenModeFlag.ReadOnly):
        logger.warning(f"Invalid file {font_path}")
        return None

    data = file.readAll()
    offset_x = 0
    for char_idx, c in enumerate(text):
        o = ord(c)
        data_offset = o * 8
        for i in range(8):
            row = data[data_offset + i][0]
            _paint_row(image, row, offset_x + char_idx * 8, i)
    return image
