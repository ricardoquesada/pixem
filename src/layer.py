# Pixem
# Copyright 2025 - Ricardo Quesada

import logging
from typing import Optional, Self, overload

from PySide6.QtCore import QPointF, QSizeF
from PySide6.QtGui import QImage

import image_utils
from partition import Partition

logger = logging.getLogger(__name__)  # __name__ gets the current module's name


class Layer:
    def __init__(self, name: str, image: QImage) -> None:
        self._image: QImage = image
        self._name: str = name
        self._position: QPointF = QPointF(0.0, 0.0)
        self._rotation: float = 0.0
        self._pixel_size: QSizeF = QSizeF(2.5, 2.5)
        self._visible: bool = True
        self._opacity: float = 1.0
        self._partitions: dict[str, Partition] = {}
        self._current_partition_key = None

    def __repr__(self) -> str:
        return (
            f"Layer(name: {self._name}, visible: {self._visible}, opacity: {self._opacity}, "
            f"pixel size: {self._pixel_size}, position: {self._position}, rotation: {self._rotation}, current partition: {self._current_partition_key}"
            ")"
        )

    @classmethod
    def from_dict(cls, d: dict) -> Self:
        """Creates a Layer from a dict"""
        name = d["name"]
        image = image_utils.base64_string_to_qimage(d["image"])
        layer_type = "Layer"
        if "layer_type" in d:
            layer_type = d["layer_type"]

        if layer_type == "ImageLayer":
            layer = ImageLayer(name, image)
        elif layer_type == "TextLayer":
            layer = TextLayer(name, image)
        else:
            layer = Layer(name, image)
        layer.populate_from_dict(d)
        return layer

    def populate_from_dict(self, d: dict) -> None:
        pos = d["position"]
        self._position = QPointF(pos["x"], pos["y"])
        self._rotation = d["rotation"]
        pixel_size = d["pixel_size"]
        self._pixel_size = QSizeF(pixel_size["width"], pixel_size["height"])
        self._visible = d["visible"]
        self._opacity = d["opacity"]
        if "partitions" in d:
            for p in d["partitions"]:
                part_dict = d["partitions"][p]
                part = Partition.from_dict(part_dict)
                self._partitions[p] = part
        if "current_partition_key" in d:
            self._current_partition_key = d["current_partition_key"]

    def to_dict(self) -> dict:
        """Returns a dictionary that represents the Layer"""
        d = {
            "name": self._name,
            "position": {"x": self._position.x(), "y": self._position.y()},
            "rotation": self._rotation,
            "pixel_size": {"width": self._pixel_size.width(), "height": self._pixel_size.height()},
            "visible": self._visible,
            "opacity": self._opacity,
            "partitions": {},
            "image": image_utils.qimage_to_base64_string(self._image),
            "current_partition_key": self._current_partition_key,
        }
        for p in self._partitions:
            part = self._partitions[p].to_dict()
            d["partitions"][p] = part
        return d

    @property
    def selected_partition(self) -> Optional[Partition]:
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
        self._current_partition_key = value

    @property
    def partitions(self) -> dict[str, Partition]:
        return self._partitions

    @partitions.setter
    def partitions(self, value: dict[str, Partition]):
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
    @overload
    def __init__(self, layer_name: str, filename: str): ...

    @overload
    def __init__(self, layer_name: str, image: QImage): ...

    def __init__(self, layer_name: str, filename_or_image: str | QImage) -> None:
        self._image_file_name = None
        if isinstance(filename_or_image, QImage):
            image = filename_or_image
        elif isinstance(filename_or_image, str):
            self._image_file_name = filename_or_image
            image = QImage(filename_or_image)
            if image is None:
                raise ValueError(f"Invalid image: {filename_or_image}")
        else:
            raise ValueError(f"Invalid image type: {filename_or_image}")
        super().__init__(layer_name, image)

    def populate_from_dict(self, d: dict) -> None:
        super().populate_from_dict(d)
        if "image_file_name" in d:
            self._image_file_name = d["image_file_name"]

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["image_file_name"] = self._image_file_name
        d["layer_type"] = "ImageLayer"
        return d


class TextLayer(Layer):
    @overload
    def __init__(self, layer_name: str, text: str, font_name): ...

    @overload
    def __init__(self, layer_name: str, image: QImage): ...

    def __init__(
        self, layer_name: str, text_or_image: str | QImage, font_name: Optional[str] = None
    ) -> None:
        self._text = None
        self._font_name = None
        if isinstance(text_or_image, QImage):
            image = text_or_image
        elif isinstance(text_or_image, str):
            image = image_utils.text_to_qimage(text_or_image, font_name)
            if image is None:
                raise ValueError(f"Invalid font: {font_name}")
            self._text = text_or_image
            self._font_name = font_name
        else:
            raise ValueError(f"Invalid type for text_or_image: {text_or_image}")

        super().__init__(layer_name, image)

    def populate_from_dict(self, d: dict) -> None:
        super().populate_from_dict(d)
        if "text" in d:
            self._text = d["text"]
        if "font_name" in d:
            self._font_name = d["font_name"]

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["text"] = self._text
        d["font_name"] = self._font_name
        d["layer_type"] = "TextLayer"
        return d
