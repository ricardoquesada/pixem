# Pixem
# Copyright 2024 Ricardo Quesada

import logging
import math

from preferences import global_preferences
from state import State

from PySide6.QtCore import (
    QRect,
    Qt,
)

from PySide6.QtGui import (
    QColor,
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

        # Draw selected pixels
        if len(self.state.current_nodes_path) > 0:
            painter.save()
            # Scale the image based on pixel size
            scaled_x = layer.image.width() * layer.pixel_size.width()
            scaled_y = layer.image.height() * layer.pixel_size.height()
            transformed_image = layer.image.scaled(
                round(scaled_x),
                round(scaled_y),
                Qt.IgnoreAspectRatio,
                Qt.FastTransformation,
            )
            painter.translate(scaled_x / 2 + layer.position.x(), scaled_y / 2 + layer.position.y())
            painter.rotate(layer.rotation)
            painter.translate(
                -(scaled_x / 2 + layer.position.x()),
                -(scaled_y / 2 + layer.position.y()),
            )

            # Set the pen (outline)
            painter.setPen(Qt.NoPen)

            # Set the brush (fill)
            brush = painter.brush()
            brush.setColor(QColor(255, 0, 0, 128))  # Red, semi-transparent fill
            brush.setStyle(Qt.BrushStyle.SolidPattern)  # Solid fill
            painter.setBrush(brush)

            rects = []
            W = layer.pixel_size.width()
            H = layer.pixel_size.height()
            for x, y in self.state.current_nodes_path:
                rects.append(
                    QRect(
                        math.ceil(layer.position.x() + x * W),
                        math.ceil(layer.position.y() + y * H),
                        math.ceil(W),
                        math.ceil(H),
                    )
                )
            painter.drawRects(rects)
            print(rects)
            painter.restore()

            # Draw hoop
            if self.cached_hoop_visible:
                painter.save()
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
            painter.restore()

            painter.end()

    def on_preferences_updated(self):
        """Updates the preference cache"""
        self.cached_hoop_visible = global_preferences.get_hoop_visible()
        self.cached_hoop_size = global_preferences.get_hoop_size()
