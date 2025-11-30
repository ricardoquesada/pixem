# Pixem
# Copyright 2025 - Ricardo Quesada

import logging
from dataclasses import asdict
from typing import Self

import toml
from PySide6.QtCore import QByteArray, QObject, Signal
from PySide6.QtGui import QImage, QImageWriter, QUndoStack

from export_svg import ExportToSvg
from layer import Layer, LayerProperties
from partition import Partition
from preferences import get_global_preferences
from shape import Shape
from state_properties import StateProperties, StatePropertyFlags
from undo_commands import (
    AddLayerCommand,
    DeleteLayerCommand,
    UpdateLayerNameCommand,
    UpdateLayerOpacityCommand,
    UpdateLayerPartitionsCommand,
    UpdateLayerPixelSizeCommand,
    UpdateLayerPositionCommand,
    UpdateLayerRotationCommand,
    UpdateLayerVisibleCommand,
    UpdatePartitionPathCommand,
    UpdateStateHoopSizeCommand,
    UpdateStateZoomFactorCommand,
    UpdateTextLayerCommand,
)
from undo_commands_properties import (
    UpdateStateCanvasBackgroundColorCommand,
    UpdateStateHoopColorCommand,
    UpdateStateHoopVisibleCommand,
    UpdateStatePartitionBackgroundColorCommand,
    UpdateStatePartitionForegroundColorCommand,
)

logger = logging.getLogger(__name__)


class State(QObject):
    # Triggered when a layer is added.
    layer_added = Signal(Layer)
    # Triggered when a layer is removed.
    layer_removed = Signal(Layer)
    # Triggered when LayerProperties (e.g: pixel_size) changes.
    layer_property_changed = Signal(Layer)
    # Triggered when a Layer changes its pixels.
    layer_pixels_changed = Signal(Layer)
    # Triggered when StateProperties (e.g: hoop_size) changes.
    # FIXME: Should pass State as parameter? but failed using forward refs, including "State"
    state_property_changed = Signal(StatePropertyFlags, StateProperties)
    # Triggered when a partition'path gets updated.
    partition_path_updated = Signal(Layer, Partition)
    # Triggered when a layer's partitions are reordered.
    layer_partitions_changed = Signal(Layer)

    def __init__(self):
        super().__init__()
        self._project_filename = None
        prefs = get_global_preferences()
        self._properties = StateProperties(
            hoop_size=prefs.get_hoop_size(),
            zoom_factor=1.0,
            selected_layer_uuid=None,
            hoop_visible=prefs.get_hoop_visible(),
            hoop_color=prefs.get_hoop_color_name(),
            canvas_background_color=prefs.get_canvas_background_color_name(),
            partition_foreground_color=prefs.get_partition_foreground_color_name(),
            partition_background_color=prefs.get_partition_background_color_name(),
            export_filename=None,
        )
        self._layers: dict[str, Layer] = {}

        self._undo_stack = QUndoStack()

    @classmethod
    def from_dict(cls, d: dict) -> Self:
        state = State()
        dict_layers = d["layers"]
        for key, value in dict_layers.items():
            layer = Layer.from_dict(value)
            state._layers[layer.uuid] = layer
            if key != layer.uuid:
                logger.error(f"Dictionary key {key} does not match layer UUID {layer.uuid}")
        if "properties" in d:
            # Handle backward compatibility:
            # Old files might miss some properties.
            # We start with the defaults (initialized in __init__) and update them with the loaded values.
            props_data = asdict(state._properties)
            props_data.update(d["properties"])

            state._properties = StateProperties(**props_data)
            # Covert to tuple, not list since it is being compared
            state._properties.hoop_size = tuple(state._properties.hoop_size)
        return state

    def to_dict(self) -> dict:
        project = {
            "properties": asdict(self._properties),
            "layers": {},
        }

        for uuid, layer in self._layers.items():
            layer_dict = layer.to_dict()
            project["layers"][uuid] = layer_dict

        return project

    @classmethod
    def load_from_filename(cls, filename: str) -> Self | None:
        logger.info(f"Loading project from filename {filename}")
        try:
            with open(filename, "r", encoding="utf-8") as f:
                d = toml.load(f)
                if not d:
                    logger.error(f"Failed to load project from {filename}")
                    return None
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

    def export_to_svg(self, filename: str) -> None:
        if len(self._layers) == 0:
            logger.warning("No layers found. Cannot export file")
            return

        export = ExportToSvg(filename, self._properties.hoop_size)

        for i, layer in enumerate(self._layers.values()):
            export.add_layer(layer)
        export.write_to_svg()
        self._properties.export_filename = filename

    def export_to_png(self, filename: str, image: QImage) -> None:
        # FIXME: Ideally the state should be able to create the QImage itself.
        # But easier if it gets passed since, Canvas creates one easily.
        writer = QImageWriter(filename)
        writer.setFormat(QByteArray("PNG"))
        success = writer.write(image)

        if success:
            logger.info(f"QImage saved successfully to {filename}")
        else:
            error_string = writer.errorString()
            logger.error(f"Failed to save QImage to {filename}. Error: {error_string}")

    def add_layer(self, layer: Layer) -> None:
        self._undo_stack.push(AddLayerCommand(self, layer, None))

    def delete_layer(self, layer: Layer) -> None:
        self._undo_stack.push(DeleteLayerCommand(self, layer, None))

    def get_layer_for_uuid(self, layer_uuid: str) -> Layer | None:
        if layer_uuid in self._layers:
            return self._layers[layer_uuid]
        return None

    def set_layer_properties(self, layer: Layer, properties: LayerProperties):
        if layer.uuid not in self._layers:
            logger.error(
                f"Cannot set layer properties. Layer {layer.name} does not belong to this state"
            )
            return

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

    def update_partition_path(self, layer: Layer, partition: Partition, path: list[Shape]):
        if layer.uuid not in self._layers:
            logger.error(
                f"Cannot update partition path. Layer {layer.name} does not belong to this state"
            )
            return

        if partition not in layer.partitions.values():
            logger.error(f"Partition {partition.name} does not belong to layer {layer.name}")
            return

        self._undo_stack.push(UpdatePartitionPathCommand(self, layer, partition, path, None))

    def update_layer_partitions(self, layer: Layer, partitions: dict[str, Partition]):
        if layer.uuid not in self._layers:
            logger.error(
                f"Cannot update layer partitions. Layer {layer.name} does not belong to this state"
            )
            return

        self._undo_stack.push(UpdateLayerPartitionsCommand(self, layer, partitions, None))

    def update_text_layer(self, layer: Layer, text: str, font_name: str, color_name: str):
        if layer.uuid not in self._layers:
            logger.error(
                f"Cannot update text layer. Layer {layer.name} does not belong to this state"
            )
            return
        self._undo_stack.push(
            UpdateTextLayerCommand(self, layer, text, font_name, color_name, None)
        )

    @property
    def undo_stack(self) -> QUndoStack:
        return self._undo_stack

    @property
    def selected_layer(self) -> Layer | None:
        if self._properties.selected_layer_uuid is None:
            return None
        if self._properties.selected_layer_uuid in self._layers:
            return self._layers[self._properties.selected_layer_uuid]
        logger.warning(f"selected_layer. Layer '{self._properties.selected_layer_uuid}' not found")
        # Should it return a valid one? No, Let it fail, and fix the root cause
        # return self._layers[0]
        return None

    @property
    def selected_layer_uuid(self) -> str:
        return self._properties.selected_layer_uuid

    @selected_layer_uuid.setter
    def selected_layer_uuid(self, uuid: str | None):
        if uuid is None:
            self._properties.selected_layer_uuid = uuid
            return
        if uuid not in self._layers:
            logger.error(
                f"Failed to change selected_layer_uuid. Layer UUID '{uuid}' not found in state layers: {self._layers}"
            )
            return
        self._properties.selected_layer_uuid = uuid

    @property
    def layers(self) -> list[Layer]:
        return list(self._layers.values())

    @layers.setter
    def layers(self, layers: list[Layer]) -> None:
        # Must be a re-order of the existing list
        # FIXME: add checks, or rename function, or add a proper "reorder layers" method
        self._layers = {}
        for layer in layers:
            self._layers[layer.uuid] = layer

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
    def project_filename(self) -> str:
        return self._project_filename

    @property
    def hoop_size(self) -> tuple[float, float]:
        return self._properties.hoop_size

    @hoop_size.setter
    def hoop_size(self, hoop_size: tuple[float, float]) -> None:
        if self._properties.hoop_size != hoop_size:
            self._undo_stack.push(UpdateStateHoopSizeCommand(self, hoop_size, None))

    @property
    def hoop_visible(self) -> bool:
        return self._properties.hoop_visible

    @hoop_visible.setter
    def hoop_visible(self, visible: bool) -> None:
        if self._properties.hoop_visible != visible:
            self._undo_stack.push(UpdateStateHoopVisibleCommand(self, visible, None))

    @property
    def hoop_color(self) -> str:
        return self._properties.hoop_color

    @hoop_color.setter
    def hoop_color(self, color: str) -> None:
        if self._properties.hoop_color != color:
            self._undo_stack.push(UpdateStateHoopColorCommand(self, color, None))

    @property
    def canvas_background_color(self) -> str:
        return self._properties.canvas_background_color

    @canvas_background_color.setter
    def canvas_background_color(self, color: str) -> None:
        if self._properties.canvas_background_color != color:
            self._undo_stack.push(UpdateStateCanvasBackgroundColorCommand(self, color, None))

    @property
    def partition_foreground_color(self) -> str:
        return self._properties.partition_foreground_color

    @partition_foreground_color.setter
    def partition_foreground_color(self, color: str) -> None:
        if self._properties.partition_foreground_color != color:
            self._undo_stack.push(UpdateStatePartitionForegroundColorCommand(self, color, None))

    @property
    def partition_background_color(self) -> str:
        return self._properties.partition_background_color

    @partition_background_color.setter
    def partition_background_color(self, color: str) -> None:
        if self._properties.partition_background_color != color:
            self._undo_stack.push(UpdateStatePartitionBackgroundColorCommand(self, color, None))

    #
    # Private methods, mostly to be called by Undo Commands
    #
    def _set_layer_properties(self, layer: Layer, properties: LayerProperties):
        if layer.uuid not in self._layers:
            logger.error(
                f"Cannot set layer properties. Layer {layer.name} does not belong to this state"
            )
            return
        layer.properties = properties
        self.layer_property_changed.emit(layer)

    def _update_partition_path(self, layer: Layer, partition: Partition, path: list[Shape]):
        if layer.uuid not in self._layers:
            logger.error(
                f"Cannot update partition path. Layer {layer.name} does not belong to this state"
            )
            return
        if partition not in layer.partitions.values():
            logger.error(f"Partition {partition.name} does not belong to layer {layer.name}")
            return
        partition.path = path
        self.partition_path_updated.emit(layer, partition)

    def _update_layer_partitions(self, layer: Layer, partitions: dict[str, Partition]):
        if layer.uuid not in self._layers:
            logger.error(
                f"Cannot update layer partitions. Layer {layer.name} does not belong to this state"
            )
            return
        layer.partitions = partitions
        self.layer_partitions_changed.emit(layer)

    def _add_layer(self, layer: Layer) -> None:
        self._layers[layer.uuid] = layer
        self._properties.selected_layer_uuid = layer.uuid
        self.layer_added.emit(layer)

    def _delete_layer(self, layer: Layer) -> None:
        try:
            del self._layers[layer.uuid]

            # if there are no elements left, idx = -1
            if len(self._layers) > 0:
                self._properties.selected_layer_uuid = list(self._layers.keys())[-1]
            else:
                self._properties.selected_layer_uuid = None

            self.layer_removed.emit(layer)
        except ValueError:
            logger.warning(f"Failed to remove layer, not  found {layer.name}")

    def _set_hoop_size(self, hoop_size: tuple[float, float]) -> None:
        self._properties.hoop_size = hoop_size
        self.state_property_changed.emit(StatePropertyFlags.HOOP_SIZE, self.properties)

    def _set_hoop_visible(self, visible: bool) -> None:
        self._properties.hoop_visible = visible
        self.state_property_changed.emit(StatePropertyFlags.HOOP_VISIBLE, self.properties)

    def _set_hoop_color(self, color: str) -> None:
        self._properties.hoop_color = color
        self.state_property_changed.emit(StatePropertyFlags.HOOP_COLOR, self.properties)

    def _set_canvas_background_color(self, color: str) -> None:
        self._properties.canvas_background_color = color
        self.state_property_changed.emit(
            StatePropertyFlags.CANVAS_BACKGROUND_COLOR, self.properties
        )

    def _set_partition_foreground_color(self, color: str) -> None:
        self._properties.partition_foreground_color = color
        self.state_property_changed.emit(
            StatePropertyFlags.PARTITION_FOREGROUND_COLOR, self.properties
        )

    def _set_partition_background_color(self, color: str) -> None:
        self._properties.partition_background_color = color
        self.state_property_changed.emit(
            StatePropertyFlags.PARTITION_BACKGROUND_COLOR, self.properties
        )

    def _set_zoom_factor(self, zoom_factor: float) -> None:
        self._properties.zoom_factor = zoom_factor
        self.state_property_changed.emit(StatePropertyFlags.ZOOM_FACTOR, self.properties)

    #
    # Compatibility methods for PreferenceDialog
    #
    def get_hoop_size(self) -> tuple[float, float]:
        return self.hoop_size

    def set_hoop_size(self, size: tuple[float, float]) -> None:
        self.hoop_size = size

    def get_hoop_visible(self) -> bool:
        return self.hoop_visible

    def set_hoop_visible(self, visible: bool) -> None:
        self.hoop_visible = visible

    def get_hoop_color_name(self) -> str:
        return self.hoop_color

    def set_hoop_color_name(self, color: str) -> None:
        self.hoop_color = color

    def get_canvas_background_color_name(self) -> str:
        return self.canvas_background_color

    def set_canvas_background_color_name(self, color: str) -> None:
        self.canvas_background_color = color

    def get_partition_foreground_color_name(self) -> str:
        return self.partition_foreground_color

    def set_partition_foreground_color_name(self, color: str) -> None:
        self.partition_foreground_color = color

    def get_partition_background_color_name(self) -> str:
        return self.partition_background_color

    def set_partition_background_color_name(self, color: str) -> None:
        self.partition_background_color = color

    def _update_text_layer(self, new_layer: Layer):
        if new_layer.uuid not in self._layers:
            logger.error(
                f"Cannot update text layer. Layer {new_layer.name} does not belong to this state"
            )
            return
        self._layers[new_layer.uuid] = new_layer
        self.layer_pixels_changed.emit(new_layer)
