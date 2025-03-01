# Pixem
# Copyright 2024 - Ricardo Quesada

import base64
import logging

from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QImage

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
