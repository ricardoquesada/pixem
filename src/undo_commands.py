# Pixem
# Copyright 2025 - Ricardo Quesada
import copy
import logging

from PySide6.QtGui import QUndoCommand

from layer import Layer

logger = logging.getLogger(__name__)  # __name__ gets the current module's name


class UpdateLayerRotationCommand(QUndoCommand):
    def __init__(self, state, layer: Layer, rotation: int, parent: QUndoCommand | None):
        super().__init__(f"Rotation: {rotation}", parent)
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
