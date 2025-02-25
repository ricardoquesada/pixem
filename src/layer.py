import logging
from typing import Self

from PySide6.QtCore import QPointF, QSizeF
from PySide6.QtGui import QImage

import image_utils

logger = logging.getLogger(__name__)  # __name__ gets the current module's name


class Layer:
    def __init__(self, image: QImage, name: str) -> None:
        self.image: QImage = image
        self.name: str = name
        self.position: QPointF = QPointF(0.0, 0.0)
        self.rotation: float = 0.0
        self.pixel_size: QSizeF = QSizeF(2.5, 2.5)
        self.visible: bool = True
        self.opacity: float = 1.0
        self.groups: dict = {}
        self.current_group_key = None

    def __repr__(self) -> str:
        return (
            f"Layer(name: {self.name}, visible: {self.visible}, opacity: {self.opacity}, "
            f"pixel size: {self.pixel_size}, position: {self.position}, rotation: {self.rotation})"
        )

    @classmethod
    def from_dict(cls, d: dict) -> Self:
        """Creates a Layer from a dict"""
        name = d["name"]
        image = image_utils.base64_string_to_qimage(d["image"])
        layer = Layer(image, name)

        pos = d["position"]
        layer.position = QPointF(pos["x"], pos["y"])
        layer.rotation = d["rotation"]
        pixel_size = d["pixel_size"]
        layer.pixel_size = QSizeF(pixel_size["width"], pixel_size["height"])
        layer.visible = d["visible"]
        layer.opacity = d["opacity"]
        if "groups" in d:
            layer.groups = d["groups"]
        if "current_group_key" in d:
            layer.current_group_key = d["current_group_key"]
        return layer

    def to_dict(self) -> dict:
        """Returns a dictionary that represents the Layer"""
        d = {
            "name": self.name,
            "position": {"x": self.position.x(), "y": self.position.y()},
            "rotation": self.rotation,
            "pixel_size": {"width": self.pixel_size.width(), "height": self.pixel_size.height()},
            "visible": self.visible,
            "opacity": self.opacity,
            "image": image_utils.qimage_to_base64_string(self.image),
            "groups": self.groups,
            "current_group_key": self.current_group_key,
        }
        return d

    def get_selected_group(self) -> dict | None:
        if self.current_group_key is None:
            return None

        if self.current_group_key not in self.groups:
            logger.warning(f"Group {self.current_group_key} not found")
            return None
        return self.groups[self.current_group_key]


class ImageLayer(Layer):
    def __init__(self, file_name: str, layer_name: str) -> None:
        image = QImage(file_name)
        if image is None:
            raise ValueError(f"Invalid image: {file_name}")
        super().__init__(image, layer_name)


class TextLayer(Layer):
    def __init__(self, font: str, text: str, layer_name: str) -> None:
        pass
