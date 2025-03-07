# Pixem
# Copyright 2024 Ricardo Quesada

import logging

from PySide6.QtCore import QPointF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPainterPath, QPaintEvent, QPen
from PySide6.QtWidgets import QWidget

from preferences import global_preferences
from state import State

logger = logging.getLogger(__name__)

DEFAULT_SCALE_FACTOR = 5.0
INCHES_TO_MM = 25.4


class Canvas(QWidget):
    position_changed = Signal(QPointF)

    def __init__(self, state: State | None):
        super().__init__()
        self.state = state

        self._cached_hoop_visible = global_preferences.get_hoop_visible()
        self._cached_hoop_size = global_preferences.get_hoop_size()
        # FIXME: must be set according to layer size
        self.setFixedSize(QSize(152 * 2, 254 * 2))

        self._mouse_start_coords = QPointF(0.0, 0.0)
        self._mouse_delta = QPointF(0.0, 0.0)

    #
    # Pyside6 events
    #
    def paintEvent(self, event: QPaintEvent) -> None:
        if not self.state or not self.state.layers:
            return

        painter = QPainter(self)
        painter.scale(
            self.state.zoom_factor * DEFAULT_SCALE_FACTOR,
            self.state.zoom_factor * DEFAULT_SCALE_FACTOR,
        )

        for i, layer in enumerate(self.state.layers):
            offset = layer.position
            if layer.name == self.state.selected_layer.name:
                offset = layer.position + self._mouse_delta
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
                painter.translate(scaled_x / 2 + offset.x(), scaled_y / 2 + offset.y())
                painter.rotate(layer.rotation)
                painter.translate(
                    -(scaled_x / 2 + offset.x()),
                    -(scaled_y / 2 + offset.y()),
                )
                painter.drawImage(offset, transformed_image)
                painter.restore()

        # Draw selected partition pixels
        layer = self.state.selected_layer
        if layer is not None and layer.current_partition_key is not None and layer.visible:
            offset = layer.position + self._mouse_delta
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
            painter.translate(scaled_x / 2 + offset.x(), scaled_y / 2 + offset.y())
            painter.rotate(layer.rotation)
            painter.translate(
                -(scaled_x / 2 + offset.x()),
                -(scaled_y / 2 + offset.y()),
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

                for x, y in partition.path:
                    polygon = [
                        QPointF(offset.x() + x * W, offset.y() + y * H),
                        QPointF(offset.x() + (x + 1) * W, offset.y() + y * H),
                        QPointF(offset.x() + (x + 1) * W, offset.y() + (y + 1) * H),
                        QPointF(offset.x() + x * W, offset.y() + (y + 1) * H),
                    ]
                    # Use drawPolygon instead of drawRects because drawPolygon supports floats
                    painter.drawPolygon(polygon)
            else:
                logger.warning(f"paintEvent: key {layer.current_partition_key} not found")
            painter.restore()

        # Draw hoop
        if self._cached_hoop_visible:
            painter.save()
            painter.setPen(QPen(Qt.GlobalColor.gray, 1, Qt.PenStyle.DashDotDotLine))
            path = QPainterPath()
            path.moveTo(0, 0)
            path.lineTo(0.0, 0.0)
            path.lineTo(0.0, self._cached_hoop_size[1] * INCHES_TO_MM)
            path.lineTo(
                self._cached_hoop_size[0] * INCHES_TO_MM, self._cached_hoop_size[1] * INCHES_TO_MM
            )
            path.lineTo(self._cached_hoop_size[0] * INCHES_TO_MM, 0.0)
            path.lineTo(0.0, 0.0)

            painter.drawPath(path)
            painter.restore()

        painter.end()

    def mousePressEvent(self, event: QMouseEvent):
        event.accept()
        self._mouse_start_coords = event.position()

    def mouseMoveEvent(self, event: QMouseEvent):
        event.accept()
        delta = event.position() - self._mouse_start_coords
        scale_factor = self.state.zoom_factor * DEFAULT_SCALE_FACTOR
        self._mouse_delta = QPointF(delta.x() / scale_factor, delta.y() / scale_factor)
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        event.accept()
        delta = event.position() - self._mouse_start_coords
        scale_factor = self.state.zoom_factor * DEFAULT_SCALE_FACTOR
        orig_pos = self.state.selected_layer.position
        new_pos = QPointF(
            orig_pos.x() + delta.x() / scale_factor, orig_pos.y() + delta.y() / scale_factor
        )
        self.position_changed.emit(new_pos)
        self._mouse_start_coords = QPointF(0.0, 0.0)
        self._mouse_delta = QPointF(0.0, 0.0)

    def sizeHint(self) -> QSize:
        max_w = self._cached_hoop_size[0] * INCHES_TO_MM
        max_h = self._cached_hoop_size[1] * INCHES_TO_MM
        if self.state is None:
            return QSize(max_w * DEFAULT_SCALE_FACTOR, max_h * DEFAULT_SCALE_FACTOR)

        for layer in self.state.layers:
            w = layer.position.x() + layer.image.width() * layer.pixel_size.width()
            h = layer.position.y() + layer.image.height() * layer.pixel_size.height()
            if w > max_w:
                max_w = w
            if h > max_h:
                max_h = h

        margin = 5
        ret = QSize(
            (max_w + margin) * self.state.zoom_factor * DEFAULT_SCALE_FACTOR,
            (max_h + margin) * self.state.zoom_factor * DEFAULT_SCALE_FACTOR,
        )
        return ret

    #
    # Public
    #
    def on_preferences_updated(self):
        """Updates the preference cache"""
        self._cached_hoop_visible = global_preferences.get_hoop_visible()
        self._cached_hoop_size = global_preferences.get_hoop_size()

    def recalculate_fixed_size(self):
        self.updateGeometry()
        new_size = self.sizeHint()
        self.setFixedSize(new_size)
        self.update()
