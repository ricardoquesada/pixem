# Pixem
# Copyright 2025 Ricardo Quesada

from PySide6.QtCore import Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QListWidget


class DeselectableListWidget(QListWidget):
    """
    A QListWidget that deselects an item if it's clicked while already selected.
    This behavior is intended for SingleSelection mode.
    """

    def mousePressEvent(self, event: QMouseEvent):
        # We only apply custom behavior for single selection mode and left clicks
        if (
            self.selectionMode() == QListWidget.SelectionMode.SingleSelection
            and event.button() == Qt.LeftButton
        ):
            item = self.itemAt(event.pos())
            if item and item.isSelected():
                # The user clicked on an already-selected item.
                # We clear the current item, which also clears the selection.
                # This will emit `currentItemChanged` with a null `current` item.
                self.setCurrentItem(None)
                # We then consume the event to prevent the default handler
                # from re-selecting the item.
                return

        # For all other cases (e.g., right-click, multi-selection mode,
        # or clicking an unselected item), we fall back to the default behavior.
        super().mousePressEvent(event)
