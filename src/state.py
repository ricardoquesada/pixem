from layer import Layer
from PySide6.QtCore import (
    Qt,
)

from PySide6.QtGui import (
    QColor,
)


class State:
    def __init__(self) -> None:
        self.layers: list[Layer] = []
        self.current_layer: Layer | None = None
        self.pen_color = QColor(Qt.black)
        self.scale_factor = 1.0
        self.hoop_visible = False
        self.filename = None

    def save_to_filename(self, filename: str) -> None:
        if filename is None:
            return
        self.filename = filename

    def load_from_filename(self, filename: str) -> None:
        pass
