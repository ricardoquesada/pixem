# Pixem
# Copyright 2024 Ricardo Quesada

import logging
from enum import Enum, auto

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPainterPath, QPaintEvent, QPen
from PySide6.QtWidgets import QWidget

import image_utils
from preferences import get_global_preferences
from state import State

logger = logging.getLogger(__name__)

DEFAULT_SCALE_FACTOR = 5.0
INCHES_TO_MM = 25.4


class Canvas(QWidget):
    position_changed = Signal(QPointF)
    layer_selection_changed = Signal(str)

    class Mode(int, Enum):
        INVALID = auto()
        MOVE = auto()
        DRAWING = auto()

    class ModeStatus(int, Enum):
        INVALID = auto()
        IDLE = auto()
        MOVING = auto()

    def __init__(self, state: State | None):
        super().__init__()
        self._state = state

        self._cached_hoop_visible = get_global_preferences().get_hoop_visible()
        if self._state is None:
            self._cached_hoop_size = get_global_preferences().get_hoop_size()
        else:
            self._cached_hoop_size = self._state.hoop_size
        # FIXME: must be set according to layer size
        self.setFixedSize(QSize(152 * 2, 254 * 2))

        self._mouse_start_coords = QPointF(0.0, 0.0)
        self._mouse_delta = QPointF(0.0, 0.0)
        self._mode = Canvas.Mode.MOVE
        self._mode_status = Canvas.ModeStatus.IDLE

    #
    # Pyside6 events
    #
    def paintEvent(self, event: QPaintEvent) -> None:
        if not self._state:
            return

        painter = QPainter(self)
        painter.scale(
            self._state.zoom_factor * DEFAULT_SCALE_FACTOR,
            self._state.zoom_factor * DEFAULT_SCALE_FACTOR,
        )

        for i, layer in enumerate(self._state.layers):
            offset = layer.position
            if layer.name == self._state.selected_layer.name:
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

                # Draw rect around it
                if (
                    self._mode_status == Canvas.ModeStatus.MOVING
                    and self._state.selected_layer == layer
                ):
                    brush = painter.brush()
                    brush.setColor(QColor(0, 0, 255, 16))  # Red, semi-transparent fill
                    brush.setStyle(Qt.BrushStyle.SolidPattern)  # Solid fill
                    painter.setBrush(brush)
                    painter.setPen(QPen(Qt.GlobalColor.lightGray, 0.5, Qt.PenStyle.DashLine))
                    rect = QRectF(offset.x(), offset.y(), scaled_x, scaled_y)
                    painter.drawRect(rect)

                painter.restore()

        # Draw selected partition pixels
        layer = self._state.selected_layer
        if (
            layer is not None
            and layer.current_partition_uuid is not None
            and layer.visible
            and self._mode_status != Canvas.ModeStatus.MOVING
        ):
            offset = layer.position + self._mouse_delta
            painter.save()
            # Scale the image based on pixel size
            scaled_x = layer.image.width() * layer.pixel_size.width()
            scaled_y = layer.image.height() * layer.pixel_size.height()
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
            if layer.current_partition_uuid in layer.partitions:
                partition = layer.partitions[layer.current_partition_uuid]

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
                logger.warning(f"paintEvent: key {layer.current_partition_uuid} not found")
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
        if not self._state or not self._state.layers:
            event.ignore()
            return
        if self._mode != Canvas.Mode.MOVE:
            event.ignore()
            return
        if event.button() != Qt.LeftButton:
            event.ignore()
            return
        event.accept()
        # Layer on top (visually) first
        for layer in reversed(self._state.layers):
            if not layer.visible or layer.opacity == 0:
                continue
            point = event.position()
            scale = self._state.zoom_factor * DEFAULT_SCALE_FACTOR
            point = QPointF(point.x() / scale, point.y() / scale)
            if layer.is_point_inside(point):
                self._mouse_start_coords = event.position()
                self._mode_status = Canvas.ModeStatus.MOVING
                if layer.uuid != self._state.current_layer_uuid:
                    self.layer_selection_changed.emit(layer.uuid)
                self.update()
                break

    def mouseMoveEvent(self, event: QMouseEvent):
        if not self._state or not self._state.layers:
            event.ignore()
            return
        if self._mode != Canvas.Mode.MOVE:
            event.ignore()
            return
        if self._mode_status != Canvas.ModeStatus.MOVING:
            event.ignore()
            return
        event.accept()
        delta = event.position() - self._mouse_start_coords
        scale_factor = self._state.zoom_factor * DEFAULT_SCALE_FACTOR
        self._mouse_delta = QPointF(delta.x() / scale_factor, delta.y() / scale_factor)
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if not self._state or not self._state.layers:
            event.ignore()
            return
        if self._mode != Canvas.Mode.MOVE:
            event.ignore()
            return
        if self._mode_status != Canvas.ModeStatus.MOVING:
            event.ignore()
            return
        if event.button() != Qt.LeftButton:
            event.ignore()
            return
        event.accept()

        self._mode_status = Canvas.ModeStatus.IDLE
        delta = event.position() - self._mouse_start_coords
        scale_factor = self._state.zoom_factor * DEFAULT_SCALE_FACTOR
        orig_pos = self._state.selected_layer.position
        new_pos = QPointF(
            orig_pos.x() + delta.x() / scale_factor, orig_pos.y() + delta.y() / scale_factor
        )
        self.position_changed.emit(new_pos)
        self._mouse_start_coords = QPointF(0.0, 0.0)
        self._mouse_delta = QPointF(0.0, 0.0)

    def sizeHint(self) -> QSize:
        max_w = self._cached_hoop_size[0] * INCHES_TO_MM
        max_h = self._cached_hoop_size[1] * INCHES_TO_MM
        if self._state is None:
            return QSize(max_w * DEFAULT_SCALE_FACTOR, max_h * DEFAULT_SCALE_FACTOR)

        for layer in self._state.layers:
            orig_w = layer.image.width() * layer.pixel_size.width()
            orig_h = layer.image.height() * layer.pixel_size.height()
            rot_w, rot_h = image_utils.rotated_rectangle_dimensions(orig_w, orig_h, layer.rotation)

            # Compensates anchor point issues.
            # Rotation is done from center, but position is from top-left
            diff_w = (orig_w - rot_w) / 2
            diff_h = (orig_h - rot_h) / 2

            w = layer.position.x() - diff_w + rot_w
            h = layer.position.y() - diff_h + rot_h
            if w > max_w:
                max_w = w
            if h > max_h:
                max_h = h

        margin = 5
        ret = QSize(
            (max_w + margin) * self._state.zoom_factor * DEFAULT_SCALE_FACTOR,
            (max_h + margin) * self._state.zoom_factor * DEFAULT_SCALE_FACTOR,
        )
        return ret

    #
    # Public
    #
    def on_preferences_updated(self):
        """Updates the preference cache"""
        self._cached_hoop_visible = get_global_preferences().get_hoop_visible()
        if self._state:
            self._cached_hoop_size = self._state.hoop_size
        else:
            self._cached_hoop_size = get_global_preferences().get_hoop_size()

    def recalculate_fixed_size(self):
        self.updateGeometry()
        new_size = self.sizeHint()
        self.setFixedSize(new_size)
        self.update()

    @property
    def mode(self) -> Mode:
        return self._mode

    @mode.setter
    def mode(self, value: Mode) -> None:
        self._mode = value

    @property
    def state(self) -> State:
        return self._state

    @state.setter
    def state(self, value: State) -> None:
        self._state = value
        if self._state:
            self._cached_hoop_size = self._state.hoop_size
        else:
            self._cached_hoop_size = get_global_preferences().get_hoop_size()
