# Pixem
# Copyright 2025 - Ricardo Quesada

from PySide6.QtGui import QUndoCommand


class UpdateStateHoopVisibleCommand(QUndoCommand):
    def __init__(self, state, visible: bool, parent: QUndoCommand | None):
        super().__init__(f"Hoop Visible: {visible}", parent)
        self._new_visible = visible
        self._old_visible = state.properties.hoop_visible
        self._state = state

    def undo(self) -> None:
        self._state._set_hoop_visible(self._old_visible)

    def redo(self) -> None:
        self._state._set_hoop_visible(self._new_visible)


class UpdateStateHoopColorCommand(QUndoCommand):
    def __init__(self, state, color: str, parent: QUndoCommand | None):
        super().__init__(f"Hoop Color: {color}", parent)
        self._new_color = color
        self._old_color = state.properties.hoop_color
        self._state = state

    def undo(self) -> None:
        self._state._set_hoop_color(self._old_color)

    def redo(self) -> None:
        self._state._set_hoop_color(self._new_color)


class UpdateStateCanvasBackgroundColorCommand(QUndoCommand):
    def __init__(self, state, color: str, parent: QUndoCommand | None):
        super().__init__(f"Canvas Background: {color}", parent)
        self._new_color = color
        self._old_color = state.properties.canvas_background_color
        self._state = state

    def undo(self) -> None:
        self._state._set_canvas_background_color(self._old_color)

    def redo(self) -> None:
        self._state._set_canvas_background_color(self._new_color)


class UpdateStatePartitionForegroundColorCommand(QUndoCommand):
    def __init__(self, state, color: str, parent: QUndoCommand | None):
        super().__init__(f"Partition Foreground: {color}", parent)
        self._new_color = color
        self._old_color = state.properties.partition_foreground_color
        self._state = state

    def undo(self) -> None:
        self._state._set_partition_foreground_color(self._old_color)

    def redo(self) -> None:
        self._state._set_partition_foreground_color(self._new_color)


class UpdateStatePartitionBackgroundColorCommand(QUndoCommand):
    def __init__(self, state, color: str, parent: QUndoCommand | None):
        super().__init__(f"Partition Background: {color}", parent)
        self._new_color = color
        self._old_color = state.properties.partition_background_color
        self._state = state

    def undo(self) -> None:
        self._state._set_partition_background_color(self._old_color)

    def redo(self) -> None:
        self._state._set_partition_background_color(self._new_color)
