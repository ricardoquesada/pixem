# Pixem
# Copyright 2025 - Ricardo Quesada

import logging
from typing import Optional

from PySide6.QtWidgets import QScrollArea, QVBoxLayout, QWidget

from canvas import Canvas
from state import State

logger = logging.getLogger(__name__)


class Document(QWidget):
    """
    Represents a single open document in the application.

    It encapsulates the State (data) and the Canvas (view), along with the
    necessary UI wrappers (QScrollArea).
    """

    def __init__(self, state: Optional[State] = None, filename: Optional[str] = None):
        super().__init__()

        self._state = state if state else State()
        self._filename = filename

        # Setup UI
        self._setup_ui()

    @property
    def state(self) -> State:
        return self._state

    @property
    def canvas(self) -> Canvas:
        return self._canvas

    @property
    def filename(self) -> Optional[str]:
        return self._filename

    @filename.setter
    def filename(self, value: Optional[str]):
        self._filename = value

    def _setup_ui(self):
        # Create Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Create ScrollArea
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)

        # Create Canvas
        self._canvas = Canvas(self._state)
        # Assuming Canvas policies might need adjustment, but Canvas usually handles itself.
        # But we need to ensure it expands if needed or centers.
        # For now, following MainWindow's previous approach implies setWidget handles it.

        self._scroll_area.setWidget(self._canvas)
        layout.addWidget(self._scroll_area)

    def undo_stack(self):
        """Returns the undo stack associated with this document's state."""
        return self._state.undo_stack

    def set_active(self, active: bool):
        """
        Called when the document becomes active or inactive.
        Used to enable/disable specific processing if needed.
        """
        # Might be useful effectively later, for now just a placeholder hook
        pass
