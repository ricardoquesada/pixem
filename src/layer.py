# Pixem
# Copyright 2025 - Ricardo Quesada

import logging
import uuid
from dataclasses import asdict, dataclass
from enum import Enum, auto
from typing import Self, overload

from PySide6.QtCore import QPointF, QRectF, QSizeF
from PySide6.QtGui import QImage, QTransform

import image_utils
from partition import Partition

logger = logging.getLogger(__name__)

INCHES_TO_MM = 25.4


class LayerAlign(int, Enum):
    INVALID = auto()

    HORIZONTAL_LEFT = auto()
    HORIZONTAL_CENTER = auto()
    HORIZONTAL_RIGHT = auto()

    VERTICAL_TOP = auto()
    VERTICAL_CENTER = auto()
    VERTICAL_BOTTOM = auto()


@dataclass
class EmbroideryParameters:
    pull_compensation_mm: float = 0.0
    max_stitch_length_mm: float = 1000.0
    fill_method: str = "auto_fill"
    initial_angle_degrees: int = 0
    min_jump_stitch_length_mm: float = 0.0


@dataclass
class LayerProperties:
    """Mutable properties for the class. Immutables, like UUID, should not be in this class"""

    position: tuple[float, float] = (0.0, 0.0)
    rotation: int = 0
    pixel_size: tuple[float, float] = (2.5, 2.5)
    visible: bool = True
    opacity: float = 1.0
    name: str | None = None


class Layer:
    def __init__(self, image: QImage):
        self._image: QImage = image
        self._uuid = str(uuid.uuid4())
        self._properties = LayerProperties()
        self._partitions: dict[str, Partition] = {}
        self._current_partition_uuid = None
        self._embroidery_params = EmbroideryParameters()

    #
    # Public methods
    #
    @classmethod
    def from_dict(cls, d: dict) -> Self:
        """Creates a Layer from a dict"""
        image = image_utils.base64_string_to_qimage(d["image"])
        layer_type = "Layer"
        if "layer_type" in d:
            layer_type = d["layer_type"]
        if layer_type == "ImageLayer":
            layer = ImageLayer(image)
        elif layer_type == "TextLayer":
            layer = TextLayer(image)
        else:
            layer = Layer(image)
        layer.populate_from_dict(d)
        return layer

    def populate_from_dict(self, d: dict) -> None:
        if "properties" in d:
            self._properties = LayerProperties(**d["properties"])
        if "embroidery_params" in d:
            self._embroidery_params = EmbroideryParameters(**d["embroidery_params"])
        # Convert list to tuple. Needed for some comparisons.
        self._properties.position = (
            self._properties.position[0],
            self._properties.position[1],
        )
        self._properties.pixel_size = (
            self._properties.pixel_size[0],
            self._properties.pixel_size[1],
        )
        if "partitions" in d:
            for k, v in d["partitions"].items():
                part = Partition.from_dict(v)
                self._partitions[k] = part
        if "current_partition_uuid" in d:
            self._current_partition_uuid = d["current_partition_uuid"]
        if "uuid" in d:
            self._uuid = d["uuid"]

    def to_dict(self) -> dict:
        """Returns a dictionary that represents the Layer"""
        d = {
            "uuid": self._uuid,
            "properties": asdict(self._properties),
            "embroidery_params": asdict(self._embroidery_params),
            "partitions": {},
            "image": image_utils.qimage_to_base64_string(self._image),
            "current_partition_uuid": self._current_partition_uuid,
            "layer_type": self.__class__.__name__,
        }
        for k, v in self._partitions.items():
            part = v.to_dict()
            d["partitions"][k] = part
        return d

    @property
    def selected_partition(self) -> Partition | None:
        if self._current_partition_uuid is None:
            return None

        if self._current_partition_uuid not in self._partitions:
            logger.warning(f"partition {self._current_partition_uuid} not found")
            return None
        return self._partitions[self._current_partition_uuid]

    @property
    def image(self) -> QImage:
        return self._image

    @property
    def properties(self) -> LayerProperties:
        return self._properties

    @properties.setter
    def properties(self, value: LayerProperties):
        self._properties = value

    @property
    def uuid(self) -> str:
        return self._uuid

    @property
    def name(self) -> str:
        return self._properties.name

    @name.setter
    def name(self, value: str):
        self._properties.name = value

    @property
    def visible(self) -> bool:
        return self._properties.visible

    @visible.setter
    def visible(self, value: bool):
        self._properties.visible = value

    @property
    def opacity(self) -> float:
        return self._properties.opacity

    @opacity.setter
    def opacity(self, value: float):
        self._properties.opacity = value

    @property
    def pixel_size(self) -> QSizeF:
        return QSizeF(self._properties.pixel_size[0], self._properties.pixel_size[1])

    @pixel_size.setter
    def pixel_size(self, value: QSizeF):
        self._properties.pixel_size = (value.width(), value.height())

    @property
    def position(self) -> QPointF:
        return QPointF(self._properties.position[0], self._properties.position[1])

    @position.setter
    def position(self, value: QPointF):
        self._properties.position = (value.x(), value.y())

    @property
    def rotation(self) -> int:
        return self._properties.rotation

    @rotation.setter
    def rotation(self, value: int):
        self._properties.rotation = value

    @property
    def current_partition_uuid(self) -> str:
        return self._current_partition_uuid

    @current_partition_uuid.setter
    def current_partition_uuid(self, value: str):
        if value not in self.partitions:
            logger.error(f"Invalid partition uuid: {value} for layer {self.uuid}")
            return
        self._current_partition_uuid = value

    @property
    def partitions(self) -> dict[str, Partition]:
        return self._partitions

    @partitions.setter
    def partitions(self, value: dict[str, Partition]):
        self._partitions = value

    @property
    def embroidery_params(self) -> EmbroideryParameters:
        return self._embroidery_params

    @embroidery_params.setter
    def embroidery_params(self, value: EmbroideryParameters):
        self._embroidery_params = value

    def is_point_inside(self, point: QPointF) -> bool:
        rect = QRectF(
            self._properties.position[0],
            self._properties.position[1],
            self._image.width() * self._properties.pixel_size[0],
            self._image.height() * self._properties.pixel_size[1],
        )

        transform = QTransform()
        transform.translate(rect.center().x(), rect.center().y())
        transform.rotate(self._properties.rotation)
        transform.translate(-rect.center().x(), -rect.center().y())

        inverse_transform, invertible = transform.inverted()
        if not invertible:
            return False

        transformed_point = inverse_transform.map(point)
        return rect.contains(transformed_point)

    def calculate_pos_for_align(
        self, align_mode: LayerAlign, hoop_size: tuple[float, float]
    ) -> tuple[float, float]:
        orig_w = self._image.width() * self._properties.pixel_size[0]
        orig_h = self._image.height() * self._properties.pixel_size[1]
        rot_w, rot_h = image_utils.rotated_rectangle_dimensions(
            orig_w, orig_h, self._properties.rotation
        )

        # Compensates anchor point issues.
        # Rotation is done from center, but position is from top-left
        diff_w = (orig_w - rot_w) / 2
        diff_h = (orig_h - rot_h) / 2

        # shorter, easier to type
        new_pos = (0, 0)
        old_pos = self._properties.position
        match align_mode:
            case LayerAlign.HORIZONTAL_LEFT:
                new_pos = (0 - diff_w, old_pos[1])
            case LayerAlign.HORIZONTAL_CENTER:
                new_pos = ((hoop_size[0] * INCHES_TO_MM - rot_w) / 2 - diff_w, old_pos[1])
            case LayerAlign.HORIZONTAL_RIGHT:
                new_pos = ((hoop_size[0] * INCHES_TO_MM - rot_w - diff_w), old_pos[1])
            case LayerAlign.VERTICAL_TOP:
                new_pos = (old_pos[0], 0.0 - diff_h)
            case LayerAlign.VERTICAL_CENTER:
                new_pos = (old_pos[0], (hoop_size[1] * INCHES_TO_MM - rot_h) / 2 - diff_h)
            case LayerAlign.VERTICAL_BOTTOM:
                new_pos = (old_pos[0], (hoop_size[1] * INCHES_TO_MM - rot_h - diff_h))

        return new_pos


class ImageLayer(Layer):
    @overload
    def __init__(self, filename: str): ...

    @overload
    def __init__(self, image: QImage): ...

    def __init__(self, filename_or_image):
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
        super().__init__(image)

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
    def __init__(self, text: str, font_name): ...

    @overload
    def __init__(self, image: QImage): ...

    def __init__(self, text_or_image, font_name=None):
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

        super().__init__(image)

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
