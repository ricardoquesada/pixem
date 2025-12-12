# Pixem
# Copyright 2025 - Ricardo Quesada

import copy
import logging
import uuid
from dataclasses import asdict, dataclass
from enum import IntEnum, auto
from typing import Self, overload

from PySide6.QtCore import QPointF, QRectF, QSizeF
from PySide6.QtGui import QColor, QImage, QTransform

import image_utils
from image_parser import ImageParser
from partition import Partition

logger = logging.getLogger(__name__)

INCHES_TO_MM = 25.4


class LayerAlign(IntEnum):
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
    fill_method: str = "contour_fill"
    odd_pixel_angle_degrees: int = 0
    even_pixel_angle_degrees: int = 90
    min_jump_stitch_length_mm: float = 0.0
    fill_underlay: bool = True


@dataclass
class LayerProperties:
    """Mutable properties only. Immutables, like UUID, should not be here."""

    position: tuple[float, float] = (0.0, 0.0)
    rotation: int = 0
    pixel_size: tuple[float, float] = (2.5, 2.5)
    visible: bool = True
    opacity: float = 1.0
    name: str | None = None
    pixel_aspect_ratio_mode: str = "Square"


class Layer:
    def __init__(self, image: QImage):
        self._image: QImage = image
        self._uuid = str(uuid.uuid4())
        self._properties = LayerProperties()
        self._partitions: dict[str, Partition] = {}
        self._selected_partition_uuid = None
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
            # FIXME: Should be cleaner code.
            # Clean possible old partitions created from constructor.
            self._partitions = {}
            for k, v in d["partitions"].items():
                part = Partition.from_dict(v)
                for kk, vv in self._partitions.items():
                    if part.name == vv.name:
                        del self._partitions[kk]
                        break
                self._partitions[k] = part
        if "selected_partition_uuid" in d:
            self._selected_partition_uuid = d["selected_partition_uuid"]
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
            "selected_partition_uuid": self._selected_partition_uuid,
            "layer_type": self.__class__.__name__,
        }
        for k, v in self._partitions.items():
            part = v.to_dict()
            d["partitions"][k] = part
        return d

    def create_partitions(self, background_color: QColor | None = None):
        parser = ImageParser(self._image, background_color)
        self._partitions = parser.partitions

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
    def selected_partition(self) -> Partition | None:
        if self._selected_partition_uuid is None:
            return None

        if self._selected_partition_uuid not in self._partitions:
            logger.warning(f"partition {self._selected_partition_uuid} not found")
            return None
        return self._partitions[self._selected_partition_uuid]

    @property
    def selected_partition_uuid(self) -> str:
        return self._selected_partition_uuid

    @selected_partition_uuid.setter
    def selected_partition_uuid(self, value: str):
        if value is not None and value not in self.partitions:
            raise ValueError(f"Invalid partition uuid: {value} for layer {self.uuid}")
        self._selected_partition_uuid = value

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

    def clone(self) -> "Layer":
        # Create a new instance using the constructor
        new_layer = Layer(self._image.copy())

        # Copy common Layer attributes
        new_layer._properties = copy.deepcopy(self._properties)
        new_layer._embroidery_params = copy.deepcopy(self._embroidery_params)

        # Deep copy partitions
        new_layer._partitions = {k: copy.deepcopy(v) for k, v in self._partitions.items()}

        return new_layer

    def calculate_fit_to_hoop_properties(
        self, hoop_size_inches: tuple[float, float]
    ) -> LayerProperties:
        """
        Calculates new properties (position and pixel_size) to fit the layer within the hoop.
        Preserves aspect ratio and rotation.
        """
        hoop_w_mm = hoop_size_inches[0] * INCHES_TO_MM
        hoop_h_mm = hoop_size_inches[1] * INCHES_TO_MM

        # Current dimensions (physical mm)
        curr_pixel_size = self._properties.pixel_size
        orig_w = self._image.width() * curr_pixel_size[0]
        orig_h = self._image.height() * curr_pixel_size[1]

        # Rotated bounding box dimensions
        rot_w, rot_h = image_utils.rotated_rectangle_dimensions(
            orig_w, orig_h, self._properties.rotation
        )

        # Calculate scale factor to fit
        # Avoid division by zero
        if rot_w == 0 or rot_h == 0:
            return copy.deepcopy(self._properties)

        scale_w = hoop_w_mm / rot_w
        scale_h = hoop_h_mm / rot_h
        scale = min(scale_w, scale_h)

        # Apply scale to pixel size
        new_pixel_size = (curr_pixel_size[0] * scale, curr_pixel_size[1] * scale)

        # Calculate new position to center
        # We need to re-calculate rotated dimensions with new scale
        new_orig_w = self._image.width() * new_pixel_size[0]
        new_orig_h = self._image.height() * new_pixel_size[1]
        new_rot_w, new_rot_h = image_utils.rotated_rectangle_dimensions(
            new_orig_w, new_orig_h, self._properties.rotation
        )

        # Center logic same as align center
        diff_w = (new_orig_w - new_rot_w) / 2
        diff_h = (new_orig_h - new_rot_h) / 2

        new_x = (hoop_w_mm - new_rot_w) / 2 - diff_w
        new_y = (hoop_h_mm - new_rot_h) / 2 - diff_h

        # Create new properties
        new_props = copy.deepcopy(self._properties)
        new_props.pixel_size = new_pixel_size
        new_props.position = (new_x, new_y)

        return new_props


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

    def clone(self) -> "ImageLayer":
        # Create a new instance using the constructor
        new_layer = ImageLayer(self._image.copy())

        # Manually copy ImageLayer specific attributes
        new_layer._image_file_name = self._image_file_name

        # Copy common Layer attributes
        new_layer._properties = copy.deepcopy(self._properties)
        new_layer._embroidery_params = copy.deepcopy(self._embroidery_params)

        # Deep copy partitions
        new_layer._partitions = {k: copy.deepcopy(v) for k, v in self._partitions.items()}

        return new_layer


class TextLayer(Layer):
    @overload
    def __init__(self, text: str, font_name, color_name): ...

    @overload
    def __init__(self, image: QImage): ...

    def __init__(self, text_or_image, font_name: str | None = None, color_name: str | None = None):
        self._text = None
        self._font_name = font_name
        self._color_name = color_name

        if isinstance(text_or_image, QImage):
            image = text_or_image
        elif isinstance(text_or_image, str):
            image = image_utils.text_to_qimage(text_or_image, font_name, color_name)
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
        if "color_name" in d:
            self._color_name = d["color_name"]

    @property
    def text(self) -> str | None:
        return self._text

    @property
    def font_name(self) -> str | None:
        return self._font_name

    @property
    def color_name(self) -> str | None:
        return self._color_name

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["text"] = self._text
        d["font_name"] = self._font_name
        d["color_name"] = self._color_name
        return d

    def clone(self) -> "TextLayer":
        # Create a new instance using the constructor
        # We pass the image directly to avoid re-rendering text
        new_layer = TextLayer(self._image.copy())

        # Manually copy TextLayer specific attributes
        new_layer._text = self._text
        new_layer._font_name = self._font_name
        new_layer._color_name = self._color_name

        # Copy common Layer attributes
        # Properties and EmbroideryParams are data classes, so we can copy them
        new_layer._properties = copy.deepcopy(self._properties)
        new_layer._embroidery_params = copy.deepcopy(self._embroidery_params)

        # Deep copy partitions
        new_layer._partitions = {k: copy.deepcopy(v) for k, v in self._partitions.items()}

        return new_layer
