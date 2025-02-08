import logging
from layer import Layer
from PySide6.QtCore import (
    Qt,
)

from PySide6.QtGui import (
    QColor,
)

logger = logging.getLogger(__name__)  # __name__ gets the current module's name


class State:
    def __init__(self) -> None:
        self.layers: list[Layer] = []
        self.current_layer: Layer | None = None
        self.pen_color = QColor(Qt.black)
        self.scale_factor = 1.0
        self.hoop_visible = False
        self.filename = None

    def save_to_filename(self, filename: str) -> None:
        logger.info(f"Saving project to filename {filename}")
        if filename is None:
            return
        self.filename = filename

    def load_from_filename(self, filename: str) -> None:
        pass
