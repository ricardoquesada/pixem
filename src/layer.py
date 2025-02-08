import image_utils

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

    def __str__(self) -> str:
        return (
            f"name: {self.name}, visible: {self.visible}, opacity: {self.opacity}, "
            f"pixel size: {self.pixel_size}, position: {self.position}, rotation: {self.rotation}"
        )

    def get_dict(self) -> dict:
        """Converts to Layer to a dictionary"""
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
