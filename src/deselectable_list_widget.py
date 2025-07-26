# Pixem
# Copyright 2025 Ricardo Quesada

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QListWidget


class DeselectableListWidget(QListWidget):
    """
    A QListWidget that deselects an item if it's clicked while already selected.
    This behavior is intended for SingleSelection mode.

    It also handles double-clicks correctly, ensuring that a double-click on a
    selected item does not trigger a deselection.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._deselection_timer = QTimer(self)
        self._deselection_timer.setSingleShot(True)
        self._deselection_timer.timeout.connect(self._perform_deselection)

    def mousePressEvent(self, event: QMouseEvent):
        """
        Handles mouse presses to initiate either a delayed deselection or a
        double-click.
        """
        # If a timer is already running, it means the user clicked very recently.
        # This is likely the second press of a double-click. We let the base
        # class handle it, which will correctly generate the double-click event.
        if self._deselection_timer.isActive():
            super().mousePressEvent(event)
            return

        # We only apply custom behavior for single selection mode and left clicks
        if (
            self.selectionMode() == QListWidget.SelectionMode.SingleSelection
            and event.button() == Qt.LeftButton
        ):
            item = self.itemAt(event.pos())
            if item and item.isSelected():
                # The user clicked an already-selected item. This could be a
                # single click to deselect, or the first click of a double-click.
                # We start a timer and wait to see if a double-click follows.
                self._deselection_timer.start(QApplication.doubleClickInterval())

                # We still pass the event to the base class. For a selected item,
                # this press won't change the selection, but it's necessary for
                # the widget to correctly detect a subsequent double-click or a
                # drag-and-drop gesture.
                super().mousePressEvent(event)
                return

        # For all other cases, fall back to the default behavior immediately.
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """
        Handles a double-click by canceling the pending deselection timer.
        """
        # A double-click has been detected. We must cancel the pending
        # deselection timer that was started by the first mouse press.
        self._deselection_timer.stop()

        super().mouseDoubleClickEvent(event)

    def startDrag(self, supportedActions):
        """
        Overrides the base method to cancel the deselection timer when a
        drag-and-drop operation begins.
        """
        # A drag is starting, so it's not a click-to-deselect.
        # We must cancel the pending deselection timer.
        self._deselection_timer.stop()
        super().startDrag(supportedActions)

    def _perform_deselection(self):
        """
        This slot is called when the deselection timer times out, indicating
        that a single-click occurred.
        """
        self.setCurrentItem(None)
