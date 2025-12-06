# Pixem
# Copyright 2025 - Ricardo Quesada

import copy
import logging
from enum import IntEnum, auto

from PySide6.QtGui import QUndoCommand

from layer import Layer, LayerProperties, TextLayer
from partition import Partition
from shape import Shape

logger = logging.getLogger(__name__)


class CommandID(IntEnum):
    # Add commands that can be compressed/merged.
    ROTATION_COMMAND_ID = auto()
    OPACITY_COMMAND_ID = auto()


class UpdateTextLayerCommand(QUndoCommand):
    def __init__(
        self,
        state,
        layer: Layer,
        text: str,
        font_name: str,
        color_name: str,
        parent: QUndoCommand | None,
    ):
        super().__init__(parent)
        self._state = state
        self._old_layer = layer

        # copy.deepcopy fails when trying to copy the QImage
        self._new_layer = TextLayer(text, font_name, color_name)
        self._new_layer._uuid = self._old_layer.uuid
        self._new_layer.properties = self._old_layer.properties
        self.setText(f"Update TextLayer {self._new_layer.name}: {self._new_layer.text}")

    def undo(self):
        self._state._update_text_layer(self._old_layer)

    def redo(self):
        self._state._update_text_layer(self._new_layer)


class UpdateLayerPropertiesCommand(QUndoCommand):
    def __init__(
        self, state, layer: Layer, properties: LayerProperties, parent: QUndoCommand | None
    ):
        super().__init__(parent)
        self._state = state
        self._layer = layer
        self._new_properties = properties
        self._old_properties = layer.properties

    def undo(self) -> None:
        self._state._set_layer_properties(self._layer, self._old_properties)

    def redo(self) -> None:
        self._state._set_layer_properties(self._layer, self._new_properties)


class UpdateLayerRotationCommand(UpdateLayerPropertiesCommand):
    def __init__(self, state, layer: Layer, rotation: int, parent: QUndoCommand | None):
        properties = copy.deepcopy(layer.properties)
        properties.rotation = rotation
        super().__init__(state, layer, properties, parent)
        self.setText(f"Rotation {rotation}")

    def id(self) -> int:
        return CommandID.ROTATION_COMMAND_ID

    def mergeWith(self, other: QUndoCommand) -> bool:
        if not isinstance(other, UpdateLayerRotationCommand):
            return False
        if self._layer != other._layer:
            return False
        self._new_properties = other._new_properties
        self.setText(f"Rotation {self._new_properties.rotation}")
        self.setObsolete(False)
        return True


class UpdateLayerPositionCommand(UpdateLayerPropertiesCommand):
    def __init__(
        self, state, layer: Layer, position: tuple[float, float], parent: QUndoCommand | None
    ):
        properties = copy.deepcopy(layer.properties)
        properties.position = position
        super().__init__(state, layer, properties, parent)
        if self._old_properties.position[0] == self._new_properties.position[0]:
            self.setText(f"Position Y: {self._new_properties.position[1]}")
        elif self._old_properties.position[1] == self._new_properties.position[1]:
            self.setText(f"Position X: {self._new_properties.position[0]}")
        else:
            self.setText(f"Position XY: {self._new_properties.position}")


class UpdateLayerPixelSizeCommand(UpdateLayerPropertiesCommand):
    def __init__(
        self, state, layer: Layer, pixel_size: tuple[float, float], parent: QUndoCommand | None
    ):
        properties = copy.deepcopy(layer.properties)
        properties.pixel_size = pixel_size
        super().__init__(state, layer, properties, parent)
        self.setText(f"Pixel Size: {pixel_size}")


class UpdateLayerOpacityCommand(UpdateLayerPropertiesCommand):
    def __init__(self, state, layer: Layer, opacity: float, parent: QUndoCommand | None):
        properties = copy.deepcopy(layer.properties)
        properties.opacity = opacity
        super().__init__(state, layer, properties, parent)
        self.setText(f"Opacity: {opacity}")


class UpdateLayerVisibleCommand(UpdateLayerPropertiesCommand):
    def __init__(self, state, layer: Layer, visible: bool, parent: QUndoCommand | None):
        properties = copy.deepcopy(layer.properties)
        properties.visible = visible
        super().__init__(state, layer, properties, parent)
        self.setText(f"Visible: {visible}")


class UpdateLayerNameCommand(UpdateLayerPropertiesCommand):
    def __init__(self, state, layer: Layer, name: str, parent: QUndoCommand | None):
        properties = copy.deepcopy(layer.properties)
        properties.name = name
        super().__init__(state, layer, properties, parent)
        self.setText(f"Name: {name}")


class UpdateStateHoopSizeCommand(QUndoCommand):
    def __init__(self, state, hoop_size: tuple[float, float], parent: QUndoCommand | None):
        super().__init__(f"Hoop Size: {hoop_size}", parent)
        self._new_hoop_size = hoop_size
        self._old_hoop_size = state.properties.hoop_size
        self._state = state

    def undo(self) -> None:
        self._state._set_hoop_size(self._old_hoop_size)

    def redo(self) -> None:
        self._state._set_hoop_size(self._new_hoop_size)


class UpdateStateZoomFactorCommand(QUndoCommand):
    def __init__(self, state, zoom_factor: float, parent: QUndoCommand | None):
        super().__init__(f"Zoom Factor: {zoom_factor}", parent)
        self._new_zoom_factor = zoom_factor
        self._old_zoom_factor = state.properties.zoom_factor
        self._state = state

    def undo(self) -> None:
        self._state._set_zoom_factor(self._old_zoom_factor)

    def redo(self) -> None:
        self._state._set_zoom_factor(self._new_zoom_factor)


class AddLayerCommand(QUndoCommand):
    def __init__(self, state, layer: Layer, parent: QUndoCommand | None):
        super().__init__(f"New Layer: {layer.properties.name}", parent)
        self._state = state
        self._new_layer = layer

    def undo(self) -> None:
        self._state._delete_layer(self._new_layer)

    def redo(self) -> None:
        self._state._add_layer(self._new_layer)


class DeleteLayerCommand(QUndoCommand):
    def __init__(self, state, layer: Layer, parent: QUndoCommand | None):
        super().__init__(f"Delete Layer: {layer.properties.name}", parent)
        self._state = state
        self._old_layer = layer

    def undo(self) -> None:
        self._state._add_layer(self._old_layer)

    def redo(self) -> None:
        self._state._delete_layer(self._old_layer)


class UpdatePartitionPathCommand(QUndoCommand):
    def __init__(
        self,
        state,
        layer: Layer,
        partition: Partition,
        path: list[Shape],
        parent: QUndoCommand | None,
    ):
        super().__init__(f"Update Partition Path: {partition.name}", parent)
        self._state = state
        self._layer = layer
        self._partition = partition
        self._new_path = path
        self._old_path = partition.path

    def undo(self) -> None:
        self._state._update_partition_path(self._layer, self._partition, self._old_path)

    def redo(self) -> None:
        self._state._update_partition_path(self._layer, self._partition, self._new_path)


class UpdateLayerPartitionsCommand(QUndoCommand):
    def __init__(
        self,
        state,
        layer: Layer,
        partitions: dict[str, Partition],
        parent: QUndoCommand | None,
    ):
        super().__init__(f"Reorder Partitions: {layer.name}", parent)
        self._state = state
        self._layer = layer
        self._new_partitions = copy.copy(partitions)
        self._old_partitions = copy.copy(layer.partitions)

    def undo(self) -> None:
        self._state._update_layer_partitions(self._layer, self._old_partitions)

    def redo(self) -> None:
        self._state._update_layer_partitions(self._layer, self._new_partitions)


class DeletePartitionCommand(QUndoCommand):
    def __init__(
        self,
        state,
        layer: Layer,
        partition: Partition,
        new_partitions: dict[str, Partition],
        parent: QUndoCommand | None,
    ):
        super().__init__(f"Delete Partition: {partition.name}", parent)
        self._state = state
        self._layer = layer
        self._partition = partition
        self._new_partitions = new_partitions
        self._old_partitions = layer.partitions

    def undo(self) -> None:
        self._state._update_layer_partitions(self._layer, self._old_partitions)

    def redo(self) -> None:
        self._state._update_layer_partitions(self._layer, self._new_partitions)


class UpdateStateLayersCommand(QUndoCommand):
    def __init__(self, state, layers: list[Layer], parent: QUndoCommand | None):
        super().__init__("Reorder Layers", parent)
        self._state = state
        self._new_layers = layers
        self._old_layers = state.layers

    def undo(self) -> None:
        self._state._set_layers(self._old_layers)

    def redo(self) -> None:
        self._state._set_layers(self._new_layers)
