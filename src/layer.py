# Pixem
# Copyright 2025 - Ricardo Quesada

import logging
from enum import Enum
from typing import Optional, Self, overload

from PySide6.QtCore import QPointF, QRectF, QSizeF
from PySide6.QtGui import QImage, QTransform

import image_utils
from partition import Partition

logger = logging.getLogger(__name__)

INCHES_TO_MM = 25.4


class LayerAlign(Enum):
    HORIZONTAL_LEFT = 1
    HORIZONTAL_CENTER = 2
    HORIZONTAL_RIGHT = 3

    VERTICAL_TOP = 4
    VERTICAL_CENTER = 5
    VERTICAL_BOTTOM = 6


class Layer:
    def __init__(self, name: str, image: QImage):
        self._image: QImage = image
        self._name: str = name
        self._position: QPointF = QPointF(0.0, 0.0)
        self._rotation: float = 0.0
        self._pixel_size: QSizeF = QSizeF(2.5, 2.5)
        self._visible: bool = True
        self._opacity: float = 1.0
        self._partitions: dict[str, Partition] = {}
        self._current_partition_key = None

    #
    # Public methods
    #
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
            "layer_type": self.__class__.__name__,
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

    def is_point_inside(self, point: QPointF) -> bool:
        rect = QRectF(
            self._position.x(),
            self._position.y(),
            self._image.width() * self._pixel_size.width(),
            self._image.height() * self._pixel_size.height(),
        )

        transform = QTransform()
        transform.translate(rect.center().x(), rect.center().y())
        transform.rotate(self._rotation)
        transform.translate(-rect.center().x(), -rect.center().y())

        inverse_transform, invertible = transform.inverted()
        if not invertible:
            return False

        transformed_point = inverse_transform.map(point)
        return rect.contains(transformed_point)

    def align(self, align_mode: LayerAlign, hoop_size: tuple[float, float]):
        # FIXME: anchor point needs to be taken into account when the image is rotated
        w, h = image_utils.rotated_rectangle_dimensions(
            self._image.width() * self.pixel_size.width(),
            self._image.height() * self._pixel_size.height(),
            self._rotation,
        )
        match align_mode:
            case LayerAlign.HORIZONTAL_LEFT:
                self.position = QPointF(0.0, self.position.y())
            case LayerAlign.HORIZONTAL_CENTER:
                self.position = QPointF((hoop_size[0] * INCHES_TO_MM - w) / 2, self.position.y())
            case LayerAlign.HORIZONTAL_RIGHT:
                self.position = QPointF((hoop_size[0] * INCHES_TO_MM - w), self.position.y())
            case LayerAlign.VERTICAL_TOP:
                self.position = QPointF(self.position.x(), 0.0)
            case LayerAlign.VERTICAL_CENTER:
                self.position = QPointF(self.position.x(), (hoop_size[1] * INCHES_TO_MM - h) / 2)
            case LayerAlign.VERTICAL_BOTTOM:
                self.position = QPointF(self.position.x(), (hoop_size[1] * INCHES_TO_MM - h))


class ImageLayer(Layer):
    @overload
    def __init__(self, layer_name: str, filename: str): ...

    @overload
    def __init__(self, layer_name: str, image: QImage): ...

    def __init__(self, layer_name, filename_or_image):
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
        return d


class TextLayer(Layer):
    @overload
    def __init__(self, layer_name: str, text: str, font_name): ...

    @overload
    def __init__(self, layer_name: str, image: QImage): ...

    def __init__(self, layer_name, text_or_image, font_name=None):
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
        return d
