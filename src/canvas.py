# Pixem
# Copyright 2024 Ricardo Quesada

"""The main canvas widget for the application."""

import logging
from enum import IntEnum, auto
from typing import override

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal, Slot
from PySide6.QtGui import (
    QColor,
    QImage,
    QKeyEvent,
    QMouseEvent,
    QPaintDevice,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QPen,
    QWheelEvent,
)
from PySide6.QtWidgets import QScrollArea, QWidget

import image_utils
from preferences import get_global_preferences
from shape import Path, Rect
from state import State

logger = logging.getLogger(__name__)

DEFAULT_SCALE_FACTOR = 5.0
INCHES_TO_MM = 25.4


class Canvas(QWidget):
    """
    The main drawing area of the Pixem application.

    It's responsible for rendering the image layers, handling user input for
    navigation (panning, zooming), and layer manipulation (moving, selecting).
    """

    position_changed = Signal(QPointF)
    layer_selection_changed = Signal(str)
    layer_double_clicked = Signal(str)

    class Mode(IntEnum):
        """The operating mode of the canvas."""

        MOVE = auto()
        DRAWING = auto()

    class ModeStatus(IntEnum):
        """The status of the current mode."""

        IDLE = auto()
        MOVING = auto()

    def __init__(self, state: State | None):
        """
        Initializes the Canvas.

        Args:
            state: The application state.
        """
        super().__init__()
        self._state = state

        preferences = get_global_preferences()
        if self._state is None:
            self._cached_hoop_size = preferences.get_hoop_size()
        else:
            self._cached_hoop_size = self._state.hoop_size
        self._cached_hoop_color = QColor(preferences.get_hoop_color_name())
        self._cached_hoop_visible = preferences.get_hoop_visible()
        self._cached_partition_background_color = QColor(
            preferences.get_partition_background_color_name()
        )
        self._cached_canvas_background_color = QColor(
            preferences.get_canvas_background_color_name()
        )

        # FIXME: must be set according to layer size
        self.setFixedSize(QSize(152 * 2, 254 * 2))

        self._mouse_start_coords = QPointF(0.0, 0.0)
        self._mouse_delta = QPointF(0.0, 0.0)
        self._mode = Canvas.Mode.MOVE
        self._mode_status = Canvas.ModeStatus.IDLE

        self._pan_last_pos = None
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        preferences.partition_background_color_changed.connect(
            self._on_partition_background_color_changed
        )
        preferences.canvas_background_color_changed.connect(
            self._on_canvas_color_background_changed
        )
        preferences.canvas_hoop_color_changed.connect(self._on_hoop_color_changed)
        preferences.hoop_visible_changed.connect(self._on_hoop_visible_changed)
        preferences.hoop_size_changed.connect(self._on_hoop_size_changed)

    def zoom_in(self):
        """Increases the zoom factor."""
        if self._state:
            # You might want to define max zoom in your state or preferences
            self._state.zoom_factor = min(2.5, self._state.zoom_factor * 1.25)
            self.recalculate_fixed_size()

    def zoom_out(self):
        """Decreases the zoom factor."""
        if self._state:
            # You might want to define min zoom in your state or preferences
            self._state.zoom_factor = max(0.25, self._state.zoom_factor / 1.25)
            self.recalculate_fixed_size()

    def zoom_reset(self):
        """Resets the zoom factor to 1."""
        if self._state:
            self._state.zoom_factor = 1
            self.recalculate_fixed_size()

    def _paint_to_qimage(
        self,
        image: QPaintDevice,
        show_background_color: bool,
        show_selected_partition: bool,
        show_hoop: bool,
    ) -> None:
        """
        Renders the canvas to a QPaintDevice.

        Args:
            image: The QPaintDevice to render to.
            show_background_color: Whether to show the background color.
            show_selected_partition: Whether to highlight the selected partition.
            show_hoop: Whether to show the hoop.
        """
        painter = QPainter(image)
        if show_background_color:
            size = self.sizeHint()
            painter.fillRect(
                QRectF(0, 0, size.width(), size.height()), self._cached_canvas_background_color
            )

        painter.scale(
            self._state.zoom_factor * DEFAULT_SCALE_FACTOR,
            self._state.zoom_factor * DEFAULT_SCALE_FACTOR,
        )

        # 1. Draw the layers. Use the cached image to draw them
        for i, layer in enumerate(self._state.layers):
            offset = layer.position
            if layer.uuid == self._state.selected_layer.uuid:
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
                    # FIXME: Move color to preferences
                    brush.setColor(QColor(0, 0, 255, 16))  # Red, semi-transparent fill
                    brush.setStyle(Qt.BrushStyle.SolidPattern)  # Solid fill
                    painter.setBrush(brush)
                    painter.setPen(QPen(Qt.GlobalColor.lightGray, 0.5, Qt.PenStyle.DashLine))
                    rect = QRectF(offset.x(), offset.y(), scaled_x, scaled_y)
                    painter.drawRect(rect)

                painter.restore()

        # 2. Draw selected partition pixels
        layer = self._state.selected_layer
        if (
            layer is not None
            and layer.selected_partition_uuid is not None
            and layer.visible
            and self._mode_status != Canvas.ModeStatus.MOVING
            and show_selected_partition
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
            brush.setColor(self._cached_partition_background_color)
            brush.setStyle(Qt.BrushStyle.SolidPattern)  # Solid fill
            painter.setBrush(brush)

            W = layer.pixel_size.width()
            H = layer.pixel_size.height()
            if layer.selected_partition_uuid in layer.partitions:
                partition = layer.partitions[layer.selected_partition_uuid]

                for shape in partition.path:
                    if isinstance(shape, Rect):
                        x, y = shape.x, shape.y
                        polygon = [
                            QPointF(offset.x() + x * W, offset.y() + y * H),
                            QPointF(offset.x() + (x + 1) * W, offset.y() + y * H),
                            QPointF(offset.x() + (x + 1) * W, offset.y() + (y + 1) * H),
                            QPointF(offset.x() + x * W, offset.y() + (y + 1) * H),
                        ]
                        # Use drawPolygon instead of drawRects because drawPolygon supports floats
                        painter.drawPolygon(polygon)
                    elif isinstance(shape, Path):
                        if not shape.path:
                            continue

                        # Convert our Path of Points to a list of QPointF,
                        # scaling them to the canvas coordinates.
                        # The path should connect the center of the pixels.
                        q_points = [
                            QPointF(offset.x() + p.x * W, offset.y() + p.y * H) for p in shape.path
                        ]

                        # Save the current painter state to not affect
                        # subsequent drawing of Rects.
                        painter.save()

                        # Use a different pen to represent the jump-stitch path
                        pen = QPen(Qt.GlobalColor.black, 0.3, Qt.PenStyle.DashLine)
                        painter.setPen(pen)
                        painter.setBrush(Qt.BrushStyle.NoBrush)

                        painter.drawPolyline(q_points)

                        painter.restore()
            else:
                logger.warning(
                    f"paintEvent: key {layer.selected_partition_uuid} not found in layer {layer.uuid}"
                )
            painter.restore()

        # 3. Draw hoop
        if show_hoop:
            painter.save()
            painter.setPen(QPen(self._cached_hoop_color, 1, Qt.PenStyle.DashDotDotLine))
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

    #
    # Slots
    #
    @Slot(str)
    def _on_partition_background_color_changed(self, color: str):
        self._cached_partition_background_color = QColor(color)
        self.update()

    @Slot(str)
    def _on_canvas_color_background_changed(self, color: str):
        self._cached_canvas_background_color = QColor(color)
        self.update()

    @Slot(str)
    def _on_hoop_color_changed(self, color: str):
        self._cached_hoop_color = QColor(color)
        self.update()

    @Slot(bool)
    def _on_hoop_visible_changed(self, visible: bool):
        self._cached_hoop_visible = visible
        self.update()

    @Slot(tuple)
    def _on_hoop_size_changed(self, size: tuple[float, float]):
        self._cached_hoop_size = size
        self.recalculate_fixed_size()
        self.update()

    #
    # Pyside6 events
    #
    @override
    def paintEvent(self, event: QPaintEvent) -> None:
        """
        Handles the paint event.

        Args:
            event: The paint event.
        """
        if not self._state:
            return
        self._paint_to_qimage(self, True, True, self._cached_hoop_visible)

    @override
    def keyPressEvent(self, event: QKeyEvent):
        """
        Handles key press events.

        Args:
            event: The key event.
        """
        if not self._state:
            event.ignore()
            return

        key = event.key()
        if key in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
            self.zoom_in()
            event.accept()
        elif key == Qt.Key.Key_Minus:
            self.zoom_out()
            event.accept()
        else:
            super().keyPressEvent(event)

    @override
    def wheelEvent(self, event: QWheelEvent):
        """
        Handles wheel events for zooming.

        Args:
            event: The wheel event.
        """
        if not self._state:
            event.ignore()
            return

        # Use Ctrl+Wheel to zoom, otherwise allow normal scrolling
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            angle = event.angleDelta().y()
            if angle > 0:
                self.zoom_in()
            elif angle < 0:
                self.zoom_out()
            event.accept()
        else:
            # Pass to parent (QScrollArea) for scrolling
            super().wheelEvent(event)

    @override
    def mousePressEvent(self, event: QMouseEvent):
        """
        Handles mouse press events for panning and layer selection.

        Args:
            event: The mouse event.
        """
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_last_pos = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

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
                if layer.uuid != self._state.selected_layer_uuid:
                    self.layer_selection_changed.emit(layer.uuid)
                self.update()
                break

    @override
    def mouseMoveEvent(self, event: QMouseEvent):
        """
        Handles mouse move events for panning and moving layers.

        Args:
            event: The mouse event.
        """
        if event.buttons() & Qt.MouseButton.MiddleButton and self._pan_last_pos is not None:
            # Find the parent QScrollArea to control its scrollbars
            scroll_area = self
            while scroll_area and not isinstance(scroll_area, QScrollArea):
                scroll_area = scroll_area.parent()

            if scroll_area:
                delta = event.position() - self._pan_last_pos
                h_bar = scroll_area.horizontalScrollBar()
                v_bar = scroll_area.verticalScrollBar()
                h_bar.setValue(h_bar.value() - delta.x())
                v_bar.setValue(v_bar.value() - delta.y())
                self._pan_last_pos = event.position()
                event.accept()
                return

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

    @override
    def mouseReleaseEvent(self, event: QMouseEvent):
        """
        Handles mouse release events to finalize panning or moving layers.

        Args:
            event: The mouse event.
        """
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_last_pos = None
            self.unsetCursor()
            event.accept()
            return

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

    @override
    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """
        Handles mouse double-click events to select and interact with layers.

        Args:
            event: The mouse event.
        """
        # Layer on top (visually) first
        # FIXME: almost same code as mousePressEvent()
        for layer in reversed(self._state.layers):
            if not layer.visible or layer.opacity == 0:
                continue
            point = event.position()
            scale = self._state.zoom_factor * DEFAULT_SCALE_FACTOR
            point = QPointF(point.x() / scale, point.y() / scale)
            if layer.is_point_inside(point):
                self.layer_double_clicked.emit(layer.uuid)
                event.accept()
                break
        event.ignore()

    @override
    def sizeHint(self) -> QSize:
        """
        Provides a recommended size for the widget.

        Returns:
            The recommended size.
        """
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
        """Updates the preference cache."""
        self._cached_hoop_visible = get_global_preferences().get_hoop_visible()
        if self._state:
            self._cached_hoop_size = self._state.hoop_size
        else:
            self._cached_hoop_size = get_global_preferences().get_hoop_size()

    def recalculate_fixed_size(self):
        """Recalculates the fixed size of the canvas."""
        self.updateGeometry()
        new_size = self.sizeHint()
        self.setFixedSize(new_size)
        self.update()

    def render_to_qimage(self) -> QImage | None:
        """
        Renders the canvas to a QImage.

        Returns:
            The rendered QImage, or None if the state is not available.
        """
        if self._state is None:
            return None
        qimage = QImage(self.sizeHint(), QImage.Format.Format_ARGB32)
        self._paint_to_qimage(qimage, True, False, False)
        return qimage

    @property
    def mode(self) -> Mode:
        """The current operating mode of the canvas."""
        return self._mode

    @mode.setter
    def mode(self, value: Mode) -> None:
        self._mode = value

    @property
    def state(self) -> State:
        """The application state."""
        return self._state

    @state.setter
    def state(self, value: State) -> None:
        self._state = value
        if self._state:
            self._cached_hoop_size = self._state.hoop_size
        else:
            self._cached_hoop_size = get_global_preferences().get_hoop_size()
