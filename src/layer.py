import image_utils
from typing import Self

from PySide6.QtCore import (
    QPointF,
    QSizeF,
)
from PySide6.QtGui import (
    QImage,
)


class Layer:
    def __init__(self, image: QImage, name: str) -> None:
        self.image = image
        self.name = name
        self.position = QPointF(0.0, 0.0)
        self.rotation = 0.0
        self.pixel_size = QSizeF(2.5, 2.5)
        self.visible = True
        self.opacity = 1.0

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
        }
        return d


class ImageLayer(Layer):
    def __init__(self, file_name: str, layer_name: str) -> None:
        image = QImage(file_name)
        if image is None:
            raise ValueError(f"Invalid image: {file_name}")
        super().__init__(image, layer_name)


class TextLayer(Layer):
    def __init__(self, font: str, text: str, layer_name: str) -> None:
        pass
