import logging
from typing import Optional, Self

from PySide6.QtCore import QPointF, QSizeF
from PySide6.QtGui import QImage

import image_utils

logger = logging.getLogger(__name__)  # __name__ gets the current module's name


class Layer:
    def __init__(self, image: QImage, name: str) -> None:
        self._image: QImage = image
        self._name: str = name
        self._position: QPointF = QPointF(0.0, 0.0)
        self._rotation: float = 0.0
        self._pixel_size: QSizeF = QSizeF(2.5, 2.5)
        self._visible: bool = True
        self._opacity: float = 1.0
        self._partitions: dict = {}
        self._current_partition_key = None

    def __repr__(self) -> str:
        return (
            f"Layer(name: {self._name}, visible: {self._visible}, opacity: {self._opacity}, "
            f"pixel size: {self._pixel_size}, position: {self._position}, rotation: {self._rotation})"
        )

    @classmethod
    def from_dict(cls, d: dict) -> Self:
        """Creates a Layer from a dict"""
        name = d["name"]
        image = image_utils.base64_string_to_qimage(d["image"])
        layer = Layer(image, name)

        pos = d["position"]
        layer._position = QPointF(pos["x"], pos["y"])
        layer._rotation = d["rotation"]
        pixel_size = d["pixel_size"]
        layer._pixel_size = QSizeF(pixel_size["width"], pixel_size["height"])
        layer._visible = d["visible"]
        layer._opacity = d["opacity"]
        if "partitions" in d:
            layer._partitions = d["partitions"]
        if "current_partition_key" in d:
            layer._current_partition_key = d["current_partition_key"]
        return layer

    def to_dict(self) -> dict:
        """Returns a dictionary that represents the Layer"""
        d = {
            "name": self._name,
            "position": {"x": self._position.x(), "y": self._position.y()},
            "rotation": self._rotation,
            "pixel_size": {"width": self._pixel_size.width(), "height": self._pixel_size.height()},
            "visible": self._visible,
            "opacity": self._opacity,
            "image": image_utils.qimage_to_base64_string(self._image),
            "partitions": self._partitions,
            "current_partition_key": self._current_partition_key,
        }
        return d

    @property
    def selected_partition(self) -> Optional[dict]:
        if self._current_partition_key is None:
            return None

        if self._current_partition_key not in self._partitions:
            logger.warning(f"partition {self._current_partition_key} not found")
            return None
        return self._partitions[self._current_partition_key]

    @property
    def image(self) -> QImage:
        return self._image

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str):
        self._name = value

    @property
    def visible(self) -> bool:
        return self._visible

    @visible.setter
    def visible(self, value: bool):
        self._visible = value

    @property
    def current_partition_key(self) -> str:
        return self._current_partition_key

    @current_partition_key.setter
    def current_partition_key(self, value: str):
        logger.info(f"Layer.current_partition_key = {value}")
        self._current_partition_key = value

    @property
    def partitions(self) -> dict:
        return self._partitions

    @partitions.setter
    def partitions(self, value: dict):
        self._partitions = value

    @property
    def opacity(self) -> float:
        return self._opacity

    @opacity.setter
    def opacity(self, value: float):
        self._opacity = value

    @property
    def pixel_size(self) -> QSizeF:
        return self._pixel_size

    @pixel_size.setter
    def pixel_size(self, value: QSizeF):
        self._pixel_size = value

    @property
    def position(self) -> QPointF:
        return self._position

    @position.setter
    def position(self, value: QPointF):
        self._position = value

    @property
    def rotation(self) -> float:
        return self._rotation

    @rotation.setter
    def rotation(self, value: float):
        self._rotation = value


class ImageLayer(Layer):
    def __init__(self, file_name: str, layer_name: str) -> None:
        image = QImage(file_name)
        if image is None:
            raise ValueError(f"Invalid image: {file_name}")
        super().__init__(image, layer_name)


class TextLayer(Layer):
    def __init__(self, font: str, text: str, layer_name: str) -> None:
        pass
