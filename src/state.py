import logging
from typing import Self

import toml

import preferences
from export import ExportToSVG
from layer import Layer

logger = logging.getLogger(__name__)  # __name__ gets the current module's name


class State:
    def __init__(self) -> None:
        self._project_filename = None
        self._export_filename = None
        self._zoom_factor = 1.0
        self._layers: list[Layer] = []
        self._current_layer_key = None

    @classmethod
    def from_dict(cls, d: dict) -> Self:
        state = State()
        state._project_filename = d["project_filename"]
        if "export_filename" in d:
            state._export_filename = d["export_filename"]
        if "zoom_factor" in d:
            state._zoom_factor = d["zoom_factor"]
        dict_layers = d["layers"]
        for dict_layer in dict_layers:
            layer = Layer.from_dict(dict_layer)
            state._layers.append(layer)
        if "current_layer_key" in d:
            state._current_layer_key = d["current_layer_key"]
        return state

    def to_dict(self) -> dict:
        project = {
            "project_filename": self._project_filename,
            "export_filename": self._export_filename,
            "zoom_factor": self._zoom_factor,
            "layers": [],
            "current_layer_key": self._current_layer_key,
        }

        for layer in self._layers:
            layer_dict = layer.to_dict()
            project["layers"].append(layer_dict)

        project["current_layer_key"] = self._current_layer_key

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
        self._project_filename = filename

        d = self.to_dict()

        with open(filename, "w", encoding="utf-8") as f:
            toml.dump(d, f)

    def export_to_filename(self, filename: str) -> None:
        logger.info(f"Export project to filename {filename}")
        if len(self._layers) == 0:
            logger.warning("No layers found. Cannot export file")
            return

        export = ExportToSVG(
            preferences.global_preferences.get_hoop_size(),
            "satin_s",
        )

        for i, layer in enumerate(self._layers):
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
        self._export_filename = filename

    def add_layer(self, layer: Layer) -> None:
        self._layers.append(layer)
        self._current_layer_key = layer.name

    def delete_layer(self, layer: Layer) -> None:
        try:
            self._layers.remove(layer)
        except ValueError:
            logger.warning(f"Failed to remove layer, not  found {layer.name}")

        # if there are no elements left, idx = -1
        if len(self._layers) > 0:
            self._current_layer_key = self._layers[-1].name
        else:
            self._current_layer_key = None

    def get_selected_layer(self) -> Layer | None:
        if self._current_layer_key is None:
            return None
        for layer in self._layers:
            if layer.name == self._current_layer_key:
                return layer
        logger.info(f"layers: {self._layers}")
        logger.warning(f"get_selected_layer. Layer '{self._current_layer_key}' not found")

    @property
    def layers(self):
        return self._layers

    @property
    def zoom_factor(self):
        return self._zoom_factor

    @zoom_factor.setter
    def zoom_factor(self, value: float):
        self._zoom_factor = value

    @property
    def current_layer_key(self):
        return self._current_layer_key

    @current_layer_key.setter
    def current_layer_key(self, value: str):
        self._current_layer_key = value

    @property
    def export_filename(self):
        return self._export_filename

    @property
    def project_filename(self):
        return self._project_filename
