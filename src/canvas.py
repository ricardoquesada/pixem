# Pixem
# Copyright 2024 Ricardo Quesada

import logging

from preferences import global_preferences
from state import State

from PySide6.QtCore import (
    Qt,
)

from PySide6.QtGui import (
    QPaintEvent,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import (
    QWidget,
)

logger = logging.getLogger(__name__)  # __name__ gets the current module's name

DEFAULT_SCALE_FACTOR = 5.0
INCHES_TO_MM = 25.4


class Canvas(QWidget):
    def __init__(self, state: State) -> None:
        super().__init__()
        self.state: State = state

        self.cached_hoop_visible = global_preferences.get_hoop_visible()
        self.cached_hoop_size = global_preferences.get_hoop_size()

    def paintEvent(self, event: QPaintEvent) -> None:
        if not self.state.layers:
            return

        painter = QPainter(self)
        painter.scale(
            self.state.scale_factor * DEFAULT_SCALE_FACTOR,
            self.state.scale_factor * DEFAULT_SCALE_FACTOR,
        )

        for i, layer in enumerate(self.state.layers):
            if layer.visible:
                painter.save()
                painter.setOpacity(layer.opacity)
                # Scale the image based on pixel size
                scaled_x = layer.image.width() * layer.pixel_size.width()
                scaled_y = layer.image.height() * layer.pixel_size.height()
                transformed_image = layer.image.scaled(
                    round(scaled_x),
                    round(scaled_y),
                    Qt.IgnoreAspectRatio,
                    Qt.FastTransformation,
                )
                painter.translate(
                    scaled_x / 2 + layer.position.x(), scaled_y / 2 + layer.position.y()
                )
                painter.rotate(layer.rotation)
                painter.translate(
                    -(scaled_x / 2 + layer.position.x()),
                    -(scaled_y / 2 + layer.position.y()),
                )
                painter.drawImage(layer.position, transformed_image)
                painter.restore()

        # Draw hoop
        if self.cached_hoop_visible:
            painter.setPen(QPen(Qt.gray, 1, Qt.DashDotDotLine))
            path = QPainterPath()
            path.moveTo(0, 0)
            path.lineTo(0.0, 0.0)
            path.lineTo(0.0, self.cached_hoop_size[1] * INCHES_TO_MM)
            path.lineTo(
                self.cached_hoop_size[0] * INCHES_TO_MM, self.cached_hoop_size[1] * INCHES_TO_MM
            )
            path.lineTo(self.cached_hoop_size[0] * INCHES_TO_MM, 0.0)
            path.lineTo(0.0, 0.0)

            painter.drawPath(path)

        # Draw selected pixels
        for x, y in self.state.current_nodes_path:
            painter.end()

    def on_preferences_updated(self):
        """Updates the preference cache"""
        self.cached_hoop_visible = global_preferences.get_hoop_visible()
        self.cached_hoop_size = global_preferences.get_hoop_size()
