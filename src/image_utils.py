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


# Table taken from Contiki OS
# https://github.com/contiki-os/contiki/blob/master/core/lib/petsciiconv.c
_ascii2petscii_table = [
    0x00,
    0x01,
    0x02,
    0x03,
    0x04,
    0x05,
    0x06,
    0x07,
    0x14,
    0x09,
    0x0D,
    0x11,
    0x93,
    0x0A,
    0x0E,
    0x0F,
    0x10,
    0x0B,
    0x12,
    0x13,
    0x08,
    0x15,
    0x16,
    0x17,
    0x18,
    0x19,
    0x1A,
    0x1B,
    0x1C,
    0x1D,
    0x1E,
    0x1F,
    0x20,
    0x21,
    0x22,
    0x23,
    0x24,
    0x25,
    0x26,
    0x27,
    0x28,
    0x29,
    0x2A,
    0x2B,
    0x2C,
    0x2D,
    0x2E,
    0x2F,
    0x30,
    0x31,
    0x32,
    0x33,
    0x34,
    0x35,
    0x36,
    0x37,
    0x38,
    0x39,
    0x3A,
    0x3B,
    0x3C,
    0x3D,
    0x3E,
    0x3F,
    0x40,
    0xC1,
    0xC2,
    0xC3,
    0xC4,
    0xC5,
    0xC6,
    0xC7,
    0xC8,
    0xC9,
    0xCA,
    0xCB,
    0xCC,
    0xCD,
    0xCE,
    0xCF,
    0xD0,
    0xD1,
    0xD2,
    0xD3,
    0xD4,
    0xD5,
    0xD6,
    0xD7,
    0xD8,
    0xD9,
    0xDA,
    0x5B,
    0x5C,
    0x5D,
    0x5E,
    0x5F,
    0xC0,
    0x41,
    0x42,
    0x43,
    0x44,
    0x45,
    0x46,
    0x47,
    0x48,
    0x49,
    0x4A,
    0x4B,
    0x4C,
    0x4D,
    0x4E,
    0x4F,
    0x50,
    0x51,
    0x52,
    0x53,
    0x54,
    0x55,
    0x56,
    0x57,
    0x58,
    0x59,
    0x5A,
    0xDB,
    0xDD,
    0xDD,
    0x5E,
    0xDF,
]


def _ascii_to_petscii_screencode(ascii_chr: chr) -> Optional[int]:
    """
    Converts ASCII to Commodore 8-bit screen code.

    Args:
        ascii_val: The ASCII character (chr).

    Returns:
        The Commodore 8-bit screen code (int).
    """
    if len(ascii_chr) != 1:
        logger.warning(f"Invalid ASCII value: {ascii_chr}")
        return None

    ascii_val = ord(ascii_chr)
    if ascii_val >= 128:
        return None

    petscii = _ascii2petscii_table[ascii_val]

    # Convert to screen code
    # http://sta.c64.org/cbm64pettoscr.html
    if petscii <= 31:
        petscii += 128
    elif petscii <= 63:
        pass  # petscii += 0 (no change)
    elif petscii <= 95:
        petscii -= 64
    elif petscii <= 127:
        petscii -= 32
    elif petscii <= 159:
        petscii += 64
    elif petscii <= 191:
        petscii -= 64
    elif petscii <= 223:
        petscii -= 128
    elif petscii <= 254:
        petscii -= 128
    else:  # petscii = 255
        petscii = 94

    return petscii


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
        o = _ascii_to_petscii_screencode(c)
        if o is None:
            continue
        data_offset = o * 8
        for i in range(8):
            row = data[data_offset + i][0]
            _paint_row(image, row, offset_x + char_idx * 8, i)
    return image
