# Pixem
# Copyright 2024 Ricardo Quesada

"""The main canvas widget for the application."""

import copy
import logging
from enum import IntEnum, auto

try:
    from typing import override
except ImportError:
    from typing_extensions import override

from PySide6.QtCore import QPointF, QRectF, QSize, QSizeF, Qt, Signal, Slot
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
    QTransform,
    QWheelEvent,
)
from PySide6.QtWidgets import QScrollArea, QWidget

import image_utils
from layer import Layer
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

    class HandleType(IntEnum):
        NONE = 0
        TOP_LEFT = 1
        TOP_RIGHT = 2
        BOTTOM_LEFT = 3
        BOTTOM_RIGHT = 4
        ROTATION = 5

    class ModeStatus(IntEnum):
        """The status of the current mode."""

        IDLE = auto()
        MOVING = auto()
        SCALING = auto()
        ROTATING = auto()

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
            self._cached_hoop_color = QColor(preferences.get_hoop_color_name())
            self._cached_hoop_visible = preferences.get_hoop_visible()
            self._cached_partition_background_color = QColor(
                preferences.get_partition_background_color_name()
            )
            self._cached_canvas_background_color = QColor(
                preferences.get_canvas_background_color_name()
            )
        else:
            self._cached_hoop_size = self._state.hoop_size
            self._cached_hoop_color = QColor(self._state.hoop_color)
            self._cached_hoop_visible = self._state.hoop_visible
            self._cached_partition_background_color = QColor(self._state.partition_background_color)
            self._cached_canvas_background_color = QColor(self._state.canvas_background_color)

        self.recalculate_fixed_size()

        self._mouse_start_coords = QPointF(0.0, 0.0)
        self._mouse_delta = QPointF(0.0, 0.0)
        self._scale_preview = QSizeF(1.0, 1.0)
        self._position_preview_delta = QPointF(0.0, 0.0)
        self._rotation_preview = 0.0
        self._active_handle = Canvas.HandleType.NONE
        self._cached_handle_color = QColor(preferences.get_canvas_handle_color_name())

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
        preferences.canvas_handle_color_changed.connect(self._on_handle_color_changed)
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

        # Get selected layer preview properties
        selected_layer = self._state.selected_layer
        sel_offset = None
        sel_pixel_size = None
        sel_rotation = None
        if selected_layer:
            sel_offset = selected_layer.position
            sel_pixel_size = selected_layer.pixel_size
            sel_rotation = selected_layer.rotation
            if self._mode_status == Canvas.ModeStatus.MOVING:
                sel_offset = selected_layer.position + self._mouse_delta
            elif self._mode_status == Canvas.ModeStatus.SCALING:
                sel_offset = selected_layer.position + self._position_preview_delta
                sel_pixel_size = QSizeF(
                    selected_layer.pixel_size.width() * self._scale_preview.width(),
                    selected_layer.pixel_size.height() * self._scale_preview.height(),
                )
            elif self._mode_status == Canvas.ModeStatus.ROTATING:
                sel_rotation = selected_layer.rotation + self._rotation_preview

        # 1. Draw the layers. Use the cached image to draw them
        for i, layer in enumerate(self._state.layers):
            if selected_layer and layer.uuid == selected_layer.uuid:
                offset = sel_offset
                pixel_size = sel_pixel_size
                rotation = sel_rotation
            else:
                offset = layer.position
                pixel_size = layer.pixel_size
                rotation = layer.rotation

            if layer.visible:
                painter.save()
                painter.setOpacity(layer.opacity)
                # Scale the image based on pixel size
                scaled_x = layer.image.width() * pixel_size.width()
                scaled_y = layer.image.height() * pixel_size.height()
                transformed_image = layer.image.scaled(
                    round(scaled_x),
                    round(scaled_y),
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.FastTransformation,
                )
                painter.translate(scaled_x / 2 + offset.x(), scaled_y / 2 + offset.y())
                painter.rotate(rotation)
                painter.translate(
                    -(scaled_x / 2 + offset.x()),
                    -(scaled_y / 2 + offset.y()),
                )
                painter.drawImage(offset, transformed_image)
                painter.restore()

                # Draw handles if selected
                if selected_layer and layer.uuid == selected_layer.uuid:
                    self._draw_layer_handles(painter, offset, pixel_size, rotation)

        # 2. Draw selected partition pixels
        layer = self._state.selected_layer
        if (
            layer is not None
            and layer.selected_partition_uuid is not None
            and layer.visible
            and self._mode_status == Canvas.ModeStatus.IDLE
            and show_selected_partition
        ):
            offset = layer.position
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

                for shape in partition.route:
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
                        pen = QPen(
                            self._cached_partition_background_color, 0.3, Qt.PenStyle.DashLine
                        )
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
        """
        Slot for when the partition background color preference changes.

        Args:
            color: The new color as a hex string.
        """
        if self._state is not None:
            return
        self._cached_partition_background_color = QColor(color)
        self.update()

    @Slot(str)
    def _on_canvas_color_background_changed(self, color: str):
        """
        Slot for when the canvas background color preference changes.

        Args:
            color: The new color as a hex string.
        """
        if self._state is not None:
            return
        self._cached_canvas_background_color = QColor(color)
        self.update()

    @Slot(str)
    def _on_hoop_color_changed(self, color: str):
        """
        Slot for when the hoop color preference changes.

        Args:
            color: The new color as a hex string.
        """
        if self._state is not None:
            return
        self._cached_hoop_color = QColor(color)
        self.update()

    @Slot(str)
    def _on_handle_color_changed(self, color: str):
        """
        Slot for when the canvas handle color preference changes.

        Args:
            color: The new color as a hex string.
        """
        self._cached_handle_color = QColor(color)
        self.update()

    @Slot(bool)
    def _on_hoop_visible_changed(self, visible: bool):
        """
        Slot for when the hoop visibility preference changes.

        Args:
            visible: True if the hoop should be visible, False otherwise.
        """
        if self._state is not None:
            return
        self._cached_hoop_visible = visible
        self.update()

    @Slot(tuple)
    def _on_hoop_size_changed(self, size: tuple[float, float]):
        """
        Slot for when the hoop size preference changes.

        Args:
            size: A tuple containing the new width and height of the hoop.
        """
        if self._state is not None:
            return
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
        elif key == Qt.Key.Key_H:
            layer = self._state.selected_layer
            if layer:
                new_image, new_partitions = layer.flipped_image_and_partitions(True, False)
                self._state.update_layer_image_and_partitions(layer, new_image, new_partitions)
            event.accept()
        elif key == Qt.Key.Key_V:
            layer = self._state.selected_layer
            if layer:
                new_image, new_partitions = layer.flipped_image_and_partitions(False, True)
                self._state.update_layer_image_and_partitions(layer, new_image, new_partitions)
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

    def _get_layer_handles(self, layer: Layer) -> dict[HandleType, QPointF]:
        """Calculates the positions of the handles in canvas coordinates."""
        scale = self._state.zoom_factor * DEFAULT_SCALE_FACTOR
        orig_w = layer.image.width() * layer.pixel_size.width()
        orig_h = layer.image.height() * layer.pixel_size.height()
        rect = QRectF(layer.position.x(), layer.position.y(), orig_w, orig_h)

        transform = QTransform()
        transform.translate(rect.center().x(), rect.center().y())
        transform.rotate(layer.rotation)
        transform.translate(-rect.center().x(), -rect.center().y())

        handles = {
            Canvas.HandleType.TOP_LEFT: transform.map(rect.topLeft()),
            Canvas.HandleType.TOP_RIGHT: transform.map(rect.topRight()),
            Canvas.HandleType.BOTTOM_LEFT: transform.map(rect.bottomLeft()),
            Canvas.HandleType.BOTTOM_RIGHT: transform.map(rect.bottomRight()),
        }

        # Rotation handle: extend from top-center
        rotation_extension_canvas = 20 / scale
        local_rot_point = QPointF(rect.center().x(), rect.top() - rotation_extension_canvas)
        handles[Canvas.HandleType.ROTATION] = transform.map(local_rot_point)

        return handles

    def _draw_layer_handles(
        self, painter: QPainter, position: QPointF, pixel_size: QSizeF, rotation: float
    ):
        """Draws the bounding box and interactive handles for the selected layer."""
        scale = self._state.zoom_factor * DEFAULT_SCALE_FACTOR
        handle_size_canvas = 8 / scale

        layer = self._state.selected_layer
        if not layer:
            return

        orig_w = layer.image.width() * pixel_size.width()
        orig_h = layer.image.height() * pixel_size.height()
        rect = QRectF(position.x(), position.y(), orig_w, orig_h)

        transform = QTransform()
        transform.translate(rect.center().x(), rect.center().y())
        transform.rotate(rotation)
        transform.translate(-rect.center().x(), -rect.center().y())

        pts = [
            transform.map(rect.topLeft()),
            transform.map(rect.topRight()),
            transform.map(rect.bottomRight()),
            transform.map(rect.bottomLeft()),
        ]

        painter.save()

        # Draw bounding box
        painter.setPen(QPen(self._cached_handle_color, 1 / scale, Qt.PenStyle.DashLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPolygon(pts)

        # Draw rotation line
        top_center = (pts[0] + pts[1]) / 2
        rotation_extension_canvas = 20 / scale
        local_rot_point = QPointF(rect.center().x(), rect.top() - rotation_extension_canvas)
        rot_point = transform.map(local_rot_point)
        painter.drawLine(top_center, rot_point)

        # Draw scale handles (squares)
        painter.setPen(QPen(self._cached_handle_color, 1 / scale, Qt.PenStyle.SolidLine))
        painter.setBrush(self._cached_handle_color)
        for pt in pts:
            painter.drawRect(
                QRectF(
                    pt.x() - handle_size_canvas / 2,
                    pt.y() - handle_size_canvas / 2,
                    handle_size_canvas,
                    handle_size_canvas,
                )
            )

        # Draw rotation handle (circle)
        painter.drawEllipse(rot_point, handle_size_canvas / 2, handle_size_canvas / 2)

        painter.restore()

    def _get_layer_at_position(self, pos: QPointF) -> Layer | None:
        """
        Finds the visible layer at the given canvas widget position.

        Args:
            pos: The position in widget coordinates (e.g. event.position()).

        Returns:
            The topmost Layer at that position, or None.
        """
        if not self._state or not self._state.layers:
            return None

        scale = self._state.zoom_factor * DEFAULT_SCALE_FACTOR
        point = QPointF(pos.x() / scale, pos.y() / scale)

        for layer in reversed(self._state.layers):
            if not layer.visible or layer.opacity == 0:
                continue
            if layer.is_point_inside(point):
                return layer
        return None

    @override
    def mousePressEvent(self, event: QMouseEvent):
        """
        Handles mouse press events for panning, layer selection, and handle interaction.

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

        scale = self._state.zoom_factor * DEFAULT_SCALE_FACTOR
        pos_canvas = event.position() / scale

        # Check handles of selected layer first
        selected_layer = self._state.selected_layer
        if selected_layer:
            handles = self._get_layer_handles(selected_layer)
            for handle_type, pt in handles.items():
                dist = (pt - pos_canvas).manhattanLength() * scale  # distance in pixels
                if dist < 8:  # 8 pixels tolerance
                    event.accept()
                    self._active_handle = handle_type
                    self._mouse_start_coords = event.position()
                    if handle_type == Canvas.HandleType.ROTATION:
                        self._mode_status = Canvas.ModeStatus.ROTATING
                        self._start_rotation = selected_layer.rotation
                    else:
                        self._mode_status = Canvas.ModeStatus.SCALING
                        self._start_pixel_size = selected_layer.pixel_size
                        self._start_position = selected_layer.position
                        # Determine anchor (opposite corner)
                        anchor_map = {
                            Canvas.HandleType.TOP_LEFT: Canvas.HandleType.BOTTOM_RIGHT,
                            Canvas.HandleType.TOP_RIGHT: Canvas.HandleType.BOTTOM_LEFT,
                            Canvas.HandleType.BOTTOM_LEFT: Canvas.HandleType.TOP_RIGHT,
                            Canvas.HandleType.BOTTOM_RIGHT: Canvas.HandleType.TOP_LEFT,
                        }
                        self._scale_anchor_type = anchor_map[handle_type]
                        self._global_anchor = handles[self._scale_anchor_type]
                    return

        # If no handle hit, check if we hit any layer
        layer = self._get_layer_at_position(event.position())
        if layer:
            event.accept()
            self._mouse_start_coords = event.position()
            self._mode_status = Canvas.ModeStatus.MOVING
            if layer.uuid != self._state.selected_layer_uuid:
                self.layer_selection_changed.emit(layer.uuid)
            self.update()

    @override
    def mouseMoveEvent(self, event: QMouseEvent):
        """
        Handles mouse move events for panning, moving, scaling, and rotating layers.

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

        scale = self._state.zoom_factor * DEFAULT_SCALE_FACTOR

        if self._mode_status == Canvas.ModeStatus.MOVING:
            event.accept()
            delta = event.position() - self._mouse_start_coords
            self._mouse_delta = QPointF(delta.x() / scale, delta.y() / scale)
            self.update()

        elif self._mode_status == Canvas.ModeStatus.ROTATING:
            event.accept()
            layer = self._state.selected_layer
            if not layer:
                return

            # Calculate center in canvas coordinates
            orig_w = layer.image.width() * layer.pixel_size.width()
            orig_h = layer.image.height() * layer.pixel_size.height()
            rect = QRectF(layer.position.x(), layer.position.y(), orig_w, orig_h)
            center = rect.center()

            start_pos_canvas = self._mouse_start_coords / scale
            curr_pos_canvas = event.position() / scale

            v_start = start_pos_canvas - center
            v_curr = curr_pos_canvas - center

            import math

            angle_start = math.atan2(v_start.y(), v_start.x()) * 180 / math.pi
            angle_curr = math.atan2(v_curr.y(), v_curr.x()) * 180 / math.pi

            delta_angle = angle_curr - angle_start
            new_rotation = self._start_rotation + delta_angle

            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                # Snap to 15 degrees
                new_rotation = round(new_rotation / 15) * 15

            self._rotation_preview = new_rotation - layer.rotation
            self.update()

        elif self._mode_status == Canvas.ModeStatus.SCALING:
            event.accept()
            layer = self._state.selected_layer
            if not layer:
                return

            orig_w = layer.image.width() * layer.pixel_size.width()
            orig_h = layer.image.height() * layer.pixel_size.height()
            rect = QRectF(layer.position.x(), layer.position.y(), orig_w, orig_h)

            transform = QTransform()
            transform.translate(rect.center().x(), rect.center().y())
            transform.rotate(layer.rotation)
            transform.translate(-rect.center().x(), -rect.center().y())

            inverse_transform, invertible = transform.inverted()
            if not invertible:
                return

            curr_pos_canvas = event.position() / scale
            local_mouse = inverse_transform.map(curr_pos_canvas)
            local_anchor = inverse_transform.map(self._global_anchor)

            # New local width and height
            new_w = abs(local_mouse.x() - local_anchor.x())
            new_h = abs(local_mouse.y() - local_anchor.y())

            # Prevent zero size
            new_w = max(1.0, new_w)
            new_h = max(1.0, new_h)

            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                # Lock aspect ratio
                orig_ratio = orig_w / orig_h
                if new_w / new_h > orig_ratio:
                    new_w = new_h * orig_ratio
                else:
                    new_h = new_w / orig_ratio

            # Scale preview multipliers
            self._scale_preview = QSizeF(new_w / orig_w, new_h / orig_h)

            # Calculate new position to keep anchor fixed
            new_center_local = QPointF(new_w / 2, new_h / 2)

            local_anchor_relative = QPointF(0, 0)
            if self._scale_anchor_type == Canvas.HandleType.BOTTOM_RIGHT:
                local_anchor_relative = QPointF(new_w, new_h)
            elif self._scale_anchor_type == Canvas.HandleType.BOTTOM_LEFT:
                local_anchor_relative = QPointF(0, new_h)
            elif self._scale_anchor_type == Canvas.HandleType.TOP_RIGHT:
                local_anchor_relative = QPointF(new_w, 0)
            elif self._scale_anchor_type == Canvas.HandleType.TOP_LEFT:
                local_anchor_relative = QPointF(0, 0)

            v_anchor_local_new = local_anchor_relative - new_center_local

            rot_transform = QTransform().rotate(layer.rotation)
            v_anchor_global_new = rot_transform.map(v_anchor_local_new)

            new_position = self._global_anchor - v_anchor_global_new - new_center_local
            self._position_preview_delta = new_position - layer.position

            self.update()

    @override
    def mouseReleaseEvent(self, event: QMouseEvent):
        """
        Handles mouse release events to finalize transformations (move, scale, rotate).

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
        if self._mode_status == Canvas.ModeStatus.IDLE:
            event.ignore()
            return
        if event.button() != Qt.LeftButton:
            event.ignore()
            return
        event.accept()

        layer = self._state.selected_layer
        if not layer:
            self._mode_status = Canvas.ModeStatus.IDLE
            return

        if self._mode_status == Canvas.ModeStatus.MOVING:
            self._mode_status = Canvas.ModeStatus.IDLE
            delta = event.position() - self._mouse_start_coords
            scale_factor = self._state.zoom_factor * DEFAULT_SCALE_FACTOR
            orig_pos = layer.position
            new_pos = QPointF(
                orig_pos.x() + delta.x() / scale_factor, orig_pos.y() + delta.y() / scale_factor
            )
            self.position_changed.emit(new_pos)

        elif self._mode_status == Canvas.ModeStatus.ROTATING:
            self._mode_status = Canvas.ModeStatus.IDLE
            new_rotation = int(layer.rotation + self._rotation_preview) % 360
            if new_rotation < 0:
                new_rotation += 360

            self._rotation_preview = 0.0

            props = copy.deepcopy(layer.properties)
            props.rotation = new_rotation
            self._state.set_layer_properties(layer, props)

        elif self._mode_status == Canvas.ModeStatus.SCALING:
            self._mode_status = Canvas.ModeStatus.IDLE

            new_pixel_size = (
                layer.pixel_size.width() * self._scale_preview.width(),
                layer.pixel_size.height() * self._scale_preview.height(),
            )
            new_position = layer.position + self._position_preview_delta

            self._scale_preview = QSizeF(1.0, 1.0)
            self._position_preview_delta = QPointF(0.0, 0.0)

            props = copy.deepcopy(layer.properties)
            props.pixel_size = new_pixel_size
            props.position = (new_position.x(), new_position.y())
            self._state.set_layer_properties(layer, props)

        self._active_handle = Canvas.HandleType.NONE
        self._mouse_start_coords = QPointF(0.0, 0.0)
        self._mouse_delta = QPointF(0.0, 0.0)
        self.update()

    @override
    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """
        Handles mouse double-click events to select and interact with layers.

        Args:
            event: The mouse event.
        """
        layer = self._get_layer_at_position(event.position())
        if layer:
            self.layer_double_clicked.emit(layer.uuid)
            event.accept()
        else:
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
        prefs = get_global_preferences()
        self._cached_handle_color = QColor(prefs.get_canvas_handle_color_name())

        if self._state:
            self._cached_hoop_size = self._state.hoop_size
            self._cached_hoop_visible = self._state.hoop_visible
            self._cached_hoop_color = QColor(self._state.hoop_color)
            self._cached_canvas_background_color = QColor(self._state.canvas_background_color)
            self._cached_partition_background_color = QColor(self._state.partition_background_color)
        else:
            self._cached_hoop_visible = prefs.get_hoop_visible()
            self._cached_hoop_size = prefs.get_hoop_size()
            self._cached_hoop_color = QColor(prefs.get_hoop_color_name())
            self._cached_canvas_background_color = QColor(prefs.get_canvas_background_color_name())
            self._cached_partition_background_color = QColor(
                prefs.get_partition_background_color_name()
            )

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
        self.on_preferences_updated()
