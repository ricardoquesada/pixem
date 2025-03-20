# Pixem
# Copyright 2025 - Ricardo Quesada

import logging
from dataclasses import asdict
from typing import Self

import toml
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QUndoStack

from export import ExportToSVG
from layer import Layer, LayerProperties
from preferences import get_global_preferences
from state_properties import StateProperties, StatePropertyFlags
from undo_commands import (
    AddLayerCommand,
    DeleteLayerCommand,
    UpdateLayerNameCommand,
    UpdateLayerOpacityCommand,
    UpdateLayerPixelSizeCommand,
    UpdateLayerPositionCommand,
    UpdateLayerRotationCommand,
    UpdateLayerVisibleCommand,
    UpdateStateHoopSizeCommand,
    UpdateStateZoomFactorCommand,
)

logger = logging.getLogger(__name__)


class State(QObject):
    # Triggered when a layer is added. Emitted by Undo Commands
    # FIXME: Not implemented
    layer_added = Signal(Layer)
    # Triggered when a layer is removed. Emitted by Undo Commands
    # FIXME: Not implemented
    layer_removed = Signal(Layer)
    # Triggered when LayerProperties (e.g: pixel_size) changes. Emitted by Undo Commands.
    layer_property_changed = Signal(Layer)
    # Triggered when StateProperties (e.g: hoop_size) changes. Emitted by Undo Commands.
    # FIXME: Should pass State as parameter? but failed using forward refs, including "State"
    state_property_changed = Signal(StatePropertyFlags, StateProperties)

    def __init__(self):
        super().__init__()
        self._project_filename = None
        self._properties = StateProperties(
            hoop_size=get_global_preferences().get_hoop_size(),
            zoom_factor=1.0,
            current_layer_uuid=None,
            export_filename=None,
        )
        self._layers: list[Layer] = []

        self._undo_stack = QUndoStack()

    @classmethod
    def from_dict(cls, d: dict) -> Self:
        state = State()
        dict_layers = d["layers"]
        for dict_layer in dict_layers:
            layer = Layer.from_dict(dict_layer)
            state._layers.append(layer)
        if "properties" in d:
            state._properties = StateProperties(**d["properties"])
        return state

    def to_dict(self) -> dict:
        project = {
            "properties": asdict(self._properties),
            "layers": [],
        }

        for layer in self._layers:
            layer_dict = layer.to_dict()
            project["layers"].append(layer_dict)

        return project

    @classmethod
    def load_from_filename(cls, filename: str) -> Self | None:
        logger.info(f"Loading project from filename {filename}")
        try:
            with open(filename, "r", encoding="utf-8") as f:
                d = toml.load(f)
                state = cls.from_dict(d)
                state._project_filename = filename
                return state
        except FileNotFoundError as e:
            logger.error(f"Could not load file from {filename}, error: {e}")
            return None

    def save_to_filename(self, filename: str) -> None:
        logger.info(f"Saving project to filename {filename}")
        if filename is None:
            return
        self._project_filename = filename

        d = self.to_dict()

        try:
            with open(filename, "w", encoding="utf-8") as f:
                toml.dump(d, f)
                self._undo_stack.setClean()
        except FileNotFoundError as e:
            logger.error(f"Could not save file to {filename}, error: {e}")
        except Exception:
            logging.exception("An unexpected error occurred:")

    def export_to_filename(self, filename: str) -> None:
        if len(self._layers) == 0:
            logger.warning("No layers found. Cannot export file")
            return

        export = ExportToSVG(filename, self._properties.hoop_size)

        for i, layer in enumerate(self._layers):
            export.add_layer(layer)
        export.write_to_svg()
        self._properties.export_filename = filename

    def _add_layer(self, layer: Layer) -> None:
        self._layers.append(layer)
        self._properties.current_layer_uuid = layer.uuid

    def add_layer(self, layer: Layer) -> None:
        self._undo_stack.push(AddLayerCommand(self, layer, None))

    def _delete_layer(self, layer: Layer) -> None:
        try:
            self._layers.remove(layer)
        except ValueError:
            logger.warning(f"Failed to remove layer, not  found {layer.name}")

        # if there are no elements left, idx = -1
        if len(self._layers) > 0:
            self._properties.current_layer_uuid = self._layers[-1].uuid
        else:
            self._properties.current_layer_uuid = None

    def delete_layer(self, layer: Layer) -> None:
        self._undo_stack.push(DeleteLayerCommand(self, layer, None))

    def get_layer_for_uuid(self, layer_uuid: str) -> Layer | None:
        for layer in self._layers:
            if layer.uuid == layer_uuid:
                return layer
        return None

    def set_layer_properties(self, layer: Layer, properties: LayerProperties):
        if properties == layer.properties:
            return

        # To make it easier for the user, we split the Undo Commands in multiple ones.
        # Easier to create "mergeables"
        if properties.rotation != layer.properties.rotation:
            self._undo_stack.push(
                UpdateLayerRotationCommand(self, layer, properties.rotation, None)
            )
        if properties.position != layer.properties.position:
            self._undo_stack.push(
                UpdateLayerPositionCommand(self, layer, properties.position, None)
            )
        if properties.pixel_size != layer.properties.pixel_size:
            self._undo_stack.push(
                UpdateLayerPixelSizeCommand(self, layer, properties.pixel_size, None)
            )
        if properties.visible != layer.properties.visible:
            self._undo_stack.push(UpdateLayerVisibleCommand(self, layer, properties.visible, None))
        if properties.opacity != layer.properties.opacity:
            self._undo_stack.push(UpdateLayerOpacityCommand(self, layer, properties.opacity, None))
        if properties.name != layer.properties.name:
            self._undo_stack.push(UpdateLayerNameCommand(self, layer, properties.name, None))

    @property
    def undo_stack(self) -> QUndoStack:
        return self._undo_stack

    @property
    def selected_layer(self) -> Layer | None:
        if self._properties.current_layer_uuid is None:
            return None
        for layer in self._layers:
            if layer.uuid == self._properties.current_layer_uuid:
                return layer
        logger.warning(f"selected_layer. Layer '{self._properties.current_layer_uuid}' not found")
        # Should it return valid one ? No, Let it fail, and fix the root cause
        # return self._layers[0]
        return None

    @property
    def layers(self) -> list[Layer]:
        return self._layers

    @layers.setter
    def layers(self, layers: list[Layer]) -> None:
        # Must be a re-order of the existing list
        # FIXME: add checks, or rename function, or add a proper "reorder layers" method
        self._layers = layers

    @property
    def properties(self) -> StateProperties:
        return self._properties

    @properties.setter
    def properties(self, properties: StateProperties):
        self._properties = properties

    @property
    def zoom_factor(self) -> float:
        return self._properties.zoom_factor

    @zoom_factor.setter
    def zoom_factor(self, zoom_factor: float):
        if self._properties.zoom_factor != zoom_factor:
            self._undo_stack.push(UpdateStateZoomFactorCommand(self, zoom_factor, None))

    @property
    def current_layer_uuid(self) -> str:
        return self._properties.current_layer_uuid

    @current_layer_uuid.setter
    def current_layer_uuid(self, uuid: str | None):
        if uuid is None:
            self._properties.current_layer_uuid = uuid
            return
        found = False
        for layer in self._layers:
            if layer.uuid == uuid:
                found = True
                break
        if not found:
            logger.error(
                f"Failed to change current_layer_uuid. Layer UUID '{uuid}' not found in state layers: {self._layers}"
            )
            return
        self._properties.current_layer_uuid = uuid

    @property
    def project_filename(self) -> str:
        return self._project_filename

    @property
    def hoop_size(self) -> tuple[float, float]:
        return self._properties.hoop_size

    @hoop_size.setter
    def hoop_size(self, hoop_size: tuple[float, float]) -> None:
        if self._properties.hoop_size != hoop_size:
            self._undo_stack.push(UpdateStateHoopSizeCommand(self, hoop_size, None))
