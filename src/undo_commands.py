# Pixem
# Copyright 2025 - Ricardo Quesada

import copy
import logging

from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QUndoCommand

from layer import Layer
from state_properties import StatePropertyFlags

logger = logging.getLogger(__name__)  # __name__ gets the current module's name


class UpdateLayerRotationCommand(QUndoCommand):
    def __init__(self, state, layer: Layer, rotation: int, parent: QUndoCommand | None):
        super().__init__(QCoreApplication.tr(f"Rotation {rotation}"), parent)
        self._layer = layer
        copy_properties = copy.deepcopy(layer.properties)
        copy_properties.rotation = rotation
        self._new_properties = copy_properties
        self._old_properties = layer.properties
        self._state = state

    def undo(self) -> None:
        self._layer.properties = self._old_properties
        self._state.layer_property_changed.emit(self._layer)

    def redo(self) -> None:
        self._layer.properties = self._new_properties
        self._state.layer_property_changed.emit(self._layer)

    def mergeWith(self, other: QUndoCommand) -> bool:
        # FIXME: NOT WORKING, not sure why
        if not isinstance(other, UpdateLayerRotationCommand):
            return False
        if self._layer != other._layer:
            return False
        self._new_properties = other._new_properties
        self.setObsolete(False)
        return True


class UpdateLayerPositionCommand(QUndoCommand):
    def __init__(
        self, state, layer: Layer, position: tuple[float, float], parent: QUndoCommand | None
    ):
        super().__init__(parent)
        self._layer = layer
        copy_properties = copy.deepcopy(layer.properties)
        copy_properties.position = position
        self._new_properties = copy_properties
        self._old_properties = layer.properties
        self._state = state
        if self._old_properties.position[0] == self._new_properties.position[0]:
            self.setText(f"Position Y: {self._new_properties.position[1]}")
        elif self._old_properties.position[1] == self._new_properties.position[1]:
            self.setText(f"Position X: {self._new_properties.position[0]}")
        else:
            self.setText(f"Position XY: {self._new_properties.position}")

    def undo(self) -> None:
        self._layer.properties = self._old_properties
        self._state.layer_property_changed.emit(self._layer)

    def redo(self) -> None:
        self._layer.properties = self._new_properties
        self._state.layer_property_changed.emit(self._layer)


class UpdateLayerPixelSizeCommand(QUndoCommand):
    def __init__(
        self, state, layer: Layer, pixel_size: tuple[float, float], parent: QUndoCommand | None
    ):
        super().__init__(f"Pixel Size: {pixel_size}", parent)
        self._layer = layer
        copy_properties = copy.deepcopy(layer.properties)
        copy_properties.pixel_size = pixel_size
        self._new_properties = copy_properties
        self._old_properties = layer.properties
        self._state = state

    def undo(self) -> None:
        self._layer.properties = self._old_properties
        self._state.layer_property_changed.emit(self._layer)

    def redo(self) -> None:
        self._layer.properties = self._new_properties
        self._state.layer_property_changed.emit(self._layer)


class UpdateLayerOpacityCommand(QUndoCommand):
    def __init__(self, state, layer: Layer, opacity: float, parent: QUndoCommand | None):
        super().__init__(f"Opacity: {opacity}", parent)
        self._layer = layer
        copy_properties = copy.deepcopy(layer.properties)
        copy_properties.opacity = opacity
        self._new_properties = copy_properties
        self._old_properties = layer.properties
        self._state = state

    def undo(self) -> None:
        self._layer.properties = self._old_properties
        self._state.layer_property_changed.emit(self._layer)

    def redo(self) -> None:
        self._layer.properties = self._new_properties
        self._state.layer_property_changed.emit(self._layer)


class UpdateLayerVisibleCommand(QUndoCommand):
    def __init__(self, state, layer: Layer, visible: bool, parent: QUndoCommand | None):
        super().__init__(f"Visible: {visible}", parent)
        self._layer = layer
        copy_properties = copy.deepcopy(layer.properties)
        copy_properties.visible = visible
        self._new_properties = copy_properties
        self._old_properties = layer.properties
        self._state = state

    def undo(self) -> None:
        self._layer.properties = self._old_properties
        self._state.layer_property_changed.emit(self._layer)

    def redo(self) -> None:
        self._layer.properties = self._new_properties
        self._state.layer_property_changed.emit(self._layer)


class UpdateLayerNameCommand(QUndoCommand):
    def __init__(self, state, layer: Layer, name: str, parent: QUndoCommand | None):
        super().__init__(f"Name: {name}", parent)
        self._layer = layer
        copy_properties = copy.deepcopy(layer.properties)
        copy_properties.name = name
        self._new_properties = copy_properties
        self._old_properties = layer.properties
        self._state = state

    def undo(self) -> None:
        self._layer.properties = self._old_properties
        self._state.layer_property_changed.emit(self._layer)

    def redo(self) -> None:
        self._layer.properties = self._new_properties
        self._state.layer_property_changed.emit(self._layer)


class UpdateStateHoopSizeCommand(QUndoCommand):
    def __init__(self, state, hoop_size: tuple[float, float], parent: QUndoCommand | None):
        super().__init__(f"Hoop Size: {hoop_size}", parent)
        self._new_hoop_size = hoop_size
        self._old_hoop_size = state.properties.hoop_size
        self._state = state

    def undo(self) -> None:
        self._state.properties.hoop_size = self._old_hoop_size
        self._state.state_property_changed.emit(
            StatePropertyFlags.HOOP_SIZE, self._state.properties
        )

    def redo(self) -> None:
        self._state.properties.hoop_size = self._new_hoop_size
        self._state.state_property_changed.emit(
            StatePropertyFlags.HOOP_SIZE, self._state.properties
        )


class UpdateStateZoomFactorCommand(QUndoCommand):
    def __init__(self, state, zoom_factor: float, parent: QUndoCommand | None):
        super().__init__(f"Zoom Factor: {zoom_factor}", parent)
        self._new_zoom_factor = zoom_factor
        self._old_zoom_factor = state.properties.zoom_factor
        self._state = state

    def undo(self) -> None:
        self._state.properties.zoom_factor = self._old_zoom_factor
        self._state.state_property_changed.emit(
            StatePropertyFlags.ZOOM_FACTOR, self._state.properties
        )

    def redo(self) -> None:
        self._state.properties.zoom_factor = self._new_zoom_factor
        self._state.state_property_changed.emit(
            StatePropertyFlags.ZOOM_FACTOR, self._state.properties
        )

    def mergeWith(self, other: QUndoCommand) -> bool:
        # FIXME: NOT WORKING, not sure why
        if not isinstance(other, UpdateStateZoomFactorCommand):
            return False
        if self._state != other._state:
            return False
        self._new_zoom_factor = other._new_zoom_factor
        self.setObsolete(False)
        return True


class AddLayerCommand(QUndoCommand):
    def __init__(self, state, layer: Layer, parent: QUndoCommand | None):
        super().__init__(f"New Layer: {layer.properties.name}", parent)
        self._state = state
        self._new_layer = layer

    def undo(self) -> None:
        self._state._delete_layer(self._new_layer)
        self._state.layer_removed.emit(self._new_layer)

    def redo(self) -> None:
        self._state._add_layer(self._new_layer)
        self._state.layer_added.emit(self._new_layer)


class DeleteLayerCommand(QUndoCommand):
    def __init__(self, state, layer: Layer, parent: QUndoCommand | None):
        super().__init__(f"Delete Layer: {layer.properties.name}", parent)
        self._state = state
        self._old_layer = layer

    def undo(self) -> None:
        self._state._add_layer(self._old_layer)
        self._state.layer_added.emit(self._old_layer)

    def redo(self) -> None:
        self._state._delete_layer(self._old_layer)
        self._state.layer_removed.emit(self._old_layer)


class SelectLayerCommand(QUndoCommand):
    def __init__(self, state, layer: str | None, parent: QUndoCommand | None):
        name = "N/A"
        if layer is not None:
            name = layer.name

        super().__init__(f"Select Layer: {name}", parent)
        self._state = state
        self._new_layer = layer
        self._old_layer = state.get_layer_for_uuid(state.current_layer_uuid)

    def undo(self) -> None:
        uuid = self._old_layer.uuid if self._old_layer else None
        self._state._set_current_layer_uuid(uuid)
        self._state.layer_selected.emit(self._old_layer)

    def redo(self) -> None:
        uuid = self._new_layer.uuid if self._new_layer else None
        self._state._set_current_layer_uuid(uuid)
        self._state.layer_selected.emit(self._new_layer)
