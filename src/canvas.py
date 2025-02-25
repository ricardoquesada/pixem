# Pixem
# Copyright 2024 Ricardo Quesada

import logging

from PySide6.QtCore import QPointF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPaintEvent, QPen
from PySide6.QtWidgets import QWidget

from preferences import global_preferences
from state import State

logger = logging.getLogger(__name__)  # __name__ gets the current module's name

DEFAULT_SCALE_FACTOR = 5.0
INCHES_TO_MM = 25.4


class Canvas(QWidget):
    def __init__(self, state: State | None) -> None:
        super().__init__()
        self.state = state

        self.cached_hoop_visible = global_preferences.get_hoop_visible()
        self.cached_hoop_size = global_preferences.get_hoop_size()
        # FIXME: must be set according to layer size
        self.setFixedSize(QSize(152 * 2, 254 * 2))

    def paintEvent(self, event: QPaintEvent) -> None:
        if not self.state or not self.state.layers:
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
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.FastTransformation,
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

        # Draw selected partition pixels
        layer = self.state.get_selected_layer()
        if layer is not None and layer.current_partition_key is not None:
            painter.save()
            # Scale the image based on pixel size
            scaled_x = layer.image.width() * layer.pixel_size.width()
            scaled_y = layer.image.height() * layer.pixel_size.height()
            transformed_image = layer.image.scaled(
                round(scaled_x),
                round(scaled_y),
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.FastTransformation,
            )
            painter.translate(scaled_x / 2 + layer.position.x(), scaled_y / 2 + layer.position.y())
            painter.rotate(layer.rotation)
            painter.translate(
                -(scaled_x / 2 + layer.position.x()),
                -(scaled_y / 2 + layer.position.y()),
            )

            # painter.setPen(Qt.NoPen)
            painter.setPen(QPen(Qt.GlobalColor.gray, 0.2, Qt.PenStyle.SolidLine))

            # Set the brush (fill)
            brush = painter.brush()
            brush.setColor(QColor(255, 0, 0, 128))  # Red, semi-transparent fill
            brush.setStyle(Qt.BrushStyle.SolidPattern)  # Solid fill
            painter.setBrush(brush)

            W = layer.pixel_size.width()
            H = layer.pixel_size.height()
            if layer.current_partition_key in layer.partitions:
                partition = layer.partitions[layer.current_partition_key]

                for x, y in partition["nodes_path"]:
                    polygon = [
                        QPointF(layer.position.x() + x * W, layer.position.y() + y * H),
                        QPointF(layer.position.x() + (x + 1) * W, layer.position.y() + y * H),
                        QPointF(layer.position.x() + (x + 1) * W, layer.position.y() + (y + 1) * H),
                        QPointF(layer.position.x() + x * W, layer.position.y() + (y + 1) * H),
                    ]
                    # Use drawPolygon instead of drawRects because drawPolygon supports floats
                    painter.drawPolygon(polygon)
            else:
                logger.warning(f"paintEvent: key {layer.current_partition_key} not found")
            painter.restore()

        # Draw hoop
        if self.cached_hoop_visible:
            painter.save()
            painter.setPen(QPen(Qt.GlobalColor.gray, 1, Qt.PenStyle.DashDotDotLine))
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

    def sizeHint(self) -> QSize:
        if self.state is None:
            return QSize(400, 400)

        max_w = 0
        max_h = 0

        if len(self.state.layers) == 0:
            max_w = self.cached_hoop_size[0] * INCHES_TO_MM
            max_h = self.cached_hoop_size[1] * INCHES_TO_MM
        else:
            for layer in self.state.layers:
                w = layer.image.width() * layer.pixel_size.width()
                h = layer.image.width() * layer.pixel_size.width()
                if w > max_w:
                    max_w = w
                if h > max_h:
                    max_h = h
        return QSize(max_w * self.state.scale_factor, max_h * self.state.scale_factor)
