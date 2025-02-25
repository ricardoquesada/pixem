import logging
from typing import Self

import toml

import preferences
from export import ExportToSVG
from layer import Layer

logger = logging.getLogger(__name__)  # __name__ gets the current module's name


class State:
    def __init__(self) -> None:
        self.project_filename = None
        self.export_filename = None
        self.scale_factor = 1.0
        self.hoop_visible = False
        self.layers: list[Layer] = []
        self.current_layer_key = None

    @classmethod
    def from_dict(cls, d: dict) -> Self:
        state = State()
        state.project_filename = d["project_filename"]
        if "export_filename" in d:
            state.export_filename = d["export_filename"]
        state.scale_factor = d["scale_factor"]
        state.hoop_visible = d["hoop_visible"]
        dict_layers = d["layers"]
        for dict_layer in dict_layers:
            layer = Layer.from_dict(dict_layer)
            state.layers.append(layer)
        if "current_layer_key" in d:
            state.current_layer_key = d["current_layer_key"]
        return state

    def to_dict(self) -> dict:
        project = {
            "project_filename": self.project_filename,
            "export_filename": self.export_filename,
            "scale_factor": self.scale_factor,
            "hoop_visible": self.hoop_visible,
            "layers": [],
            "current_layer_key": self.current_layer_key,
        }

        for layer in self.layers:
            layer_dict = layer.to_dict()
            project["layers"].append(layer_dict)

        project["current_layer_key"] = self.current_layer_key

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
        self.project_filename = filename

        d = self.to_dict()

        with open(filename, "w", encoding="utf-8") as f:
            toml.dump(d, f)

    def export_to_filename(self, filename: str) -> None:
        logger.info(f"Export project to filename {filename}")
        if len(self.layers) == 0:
            logger.warning("No layers found. Cannot export file")
            return

        export = ExportToSVG(
            preferences.global_preferences.get_hoop_size(),
            "satin_s",
        )

        for i, layer in enumerate(self.layers):
            export.add_layer(
                f"layer_{i}",
                layer.partitions,
                (layer.pixel_size.width(), layer.pixel_size.height()),
                (layer.position.x(), layer.position.y()),
                (1.0, 1.0),
                (
                    layer.rotation,  # degrees
                    layer.image.width() * layer.pixel_size.width() / 2,  # anchor point x
                    layer.image.height() * layer.pixel_size.height() / 2,  # anchor point y
                ),
            )
        export.write_to_svg(filename)
        self.export_filename = filename

    def add_layer(self, layer: Layer) -> None:
        self.layers.append(layer)
        self.current_layer_key = layer.name

    def delete_layer(self, layer: Layer) -> None:
        try:
            self.layers.remove(layer)
        except ValueError:
            logger.warning(f"Failed to remove layer, not  found {layer.name}")

        # if there are no elements left, idx = -1
        if len(self.layers) > 0:
            self.current_layer_key = self.layers[-1].name
        else:
            self.current_layer_key = None

    def get_selected_layer(self) -> Layer | None:
        if self.current_layer_key is None:
            return None
        for layer in self.layers:
            if layer.name == self.current_layer_key:
                return layer
        logger.info(f"layers: {self.layers}")
        logger.warning(f"get_selected_layer. Layer '{self.current_layer_key}' not found")
