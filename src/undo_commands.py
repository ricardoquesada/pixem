# Pixem
# Copyright 2025 - Ricardo Quesada

import logging

from PySide6.QtGui import QUndoCommand

from layer import Layer, LayerRenderProperties

logger = logging.getLogger(__name__)  # __name__ gets the current module's name


class UpdateLayerRenderPropertiesCommand(QUndoCommand):
    def __init__(
        self, state, layer: Layer, properties: LayerRenderProperties, parent: QUndoCommand | None
    ):
        super().__init__("Layer Render Properties", parent)
        self._layer = layer
        self._new_properties = properties
        self._old_properties = layer.render_properties
        self._state = state

    def undo(self) -> None:
        self._layer.render_properties = self._old_properties
        self._state.layer_property_changed.emit(self._layer)

    def redo(self) -> None:
        self._layer.render_properties = self._new_properties
        self._state.layer_property_changed.emit(self._layer)
