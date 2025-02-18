import logging
import toml
from layer import Layer
from typing import Self
from PySide6.QtCore import (
    Qt,
)
from PySide6.QtGui import (
    QColor,
)

logger = logging.getLogger(__name__)  # __name__ gets the current module's name


class State:
    def __init__(self) -> None:
        self.filename = None
        self.pen_color = QColor(Qt.black)
        self.scale_factor = 1.0
        self.hoop_visible = False
        self.layers: list[Layer] = []
        self.current_layer_idx: int = -1
        self.current_nodes_path: [] = None

    @classmethod
    def from_dict(cls, d: dict) -> Self:
        state = State()
        state.filename = d["filename"]
        pen_color = d["pen_color"]
        state.pen_color = QColor(pen_color["r"], pen_color["g"], pen_color["b"], pen_color["a"])
        state.scale_factor = d["scale_factor"]
        state.hoop_visible = d["hoop_visible"]
        dict_layers = d["layers"]
        for dict_layer in dict_layers:
            layer = Layer.from_dict(dict_layer)
            state.layers.append(layer)
        state.current_layer_idx = d["current_layer_idx"]
        return state

    def to_dict(self) -> dict:
        project = {
            "filename": self.filename,
            "pen_color": {
                "r": self.pen_color.red(),
                "g": self.pen_color.green(),
                "b": self.pen_color.blue(),
                "a": self.pen_color.alpha(),
            },
            "scale_factor": self.scale_factor,
            "hoop_visible": self.hoop_visible,
            "layers": [],
            "current_layer_idx": self.current_layer_idx,
        }

        for layer in self.layers:
            layer_dict = layer.to_dict()
            project["layers"].append(layer_dict)

        project["current_layer_idx"] = self.current_layer_idx

        return project

    @classmethod
    def load_from_filename(cls, filename: str) -> Self | None:
        logger.info(f"Loading project from filename {filename}")
        with open(filename, "r", encoding="utf-8") as f:
            d = toml.load(f)
            return cls.from_dict(d)

    def save_to_filename(self, filename: str) -> None:
        logger.info(f"Saving project to filename {filename}")
        if filename is None:
            return
        self.filename = filename

        d = self.to_dict()

        with open(filename, "w", encoding="utf-8") as f:
            toml.dump(d, f)

    def add_layer(self, layer: Layer) -> None:
        self.layers.append(layer)
        self.current_layer_idx = len(self.layers) - 1

    def delete_layer(self, layer: Layer) -> None:
        try:
            self.layers.remove(layer)
        except ValueError:
            logger.warning(f"Failed to remove layer, not  found {layer.name}")

        # if there are no elements left, idx = -1
        self.current_layer_idx = len(self.layers) - 1

    def get_selected_layer(self) -> Layer | None:
        if self.current_layer_idx == -1:
            return None
        return self.layers[self.current_layer_idx]
