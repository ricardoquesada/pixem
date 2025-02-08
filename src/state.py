import logging
import tomlkit
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

    def get_dict(self) -> dict:
        project = {
            "filename": self.filename,
            "current_layer": None,
            "pen_color": {
                "r": self.pen_color.red(),
                "g": self.pen_color.green(),
                "b": self.pen_color.blue(),
                "a": self.pen_color.alpha(),
            },
            "scale_factor": self.scale_factor,
            "layers": [],
            "hoop_visible": self.hoop_visible,
        }

        for layer in self.layers:
            layer_dict = layer.get_dict()
            project["layers"].append(layer_dict)

        if self.current_layer is not None:
            project["current_layer"] = self.current_layer.name

        return project

    def save_to_filename(self, filename: str) -> None:
        logger.info(f"Saving project to filename {filename}")
        if filename is None:
            return
        self.filename = filename

        d = self.get_dict()

        with open(filename, "w", encoding="utf-8") as f:  # Use utf-8 encoding
            tomlkit.dump(d, f)


def load_from_filename(self, filename: str) -> None:
    pass
