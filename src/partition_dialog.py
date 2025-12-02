# Pixem
# Copyright 2025 - Ricardo Quesada

import logging
from enum import IntEnum, auto

from PySide6.QtCore import QItemSelectionModel, QPointF, QRect, QSize, Qt, Slot
from PySide6.QtGui import (
    QAction,
    QColor,
    QIcon,
    QImage,
    QKeyEvent,
    QKeySequence,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
    QPixmap,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QScrollArea,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from image_utils import create_icon_from_svg
from partition import Partition
from preferences import get_global_preferences
from shape import Path, Point, Rect, Shape

PAINT_SCALE_FACTOR = 16
ICON_SIZE = 22

logger = logging.getLogger(__name__)


class ImageWidget(QWidget):
    class PrimitiveMode(IntEnum):
        RECT = auto()
        LINE = auto()

    class CoordMode(IntEnum):
        ADD = auto()
        REMOVE = auto()

    class EditMode(IntEnum):
        PAINT = auto()
        FILL = auto()
        ADD_PATH = auto()
        SELECT = auto()

    def __init__(self, partition_dialog, image: QImage, shapes: list[Shape]):
        super().__init__()
        self._partition_dialog = partition_dialog
        self._image = image
        self._original_shapes = shapes
        self._selected_shapes = []

        # Ensure widget is at least image size
        self.setMinimumSize(self._image.size())

        # To prevent creating the rect, we have them pre-created
        self._cached_rects_dict = {}
        self._cached_paths_dict = {}
        self._cached_all_rects = []
        self._cached_all_paths = []
        self._rebuild_cache()

        # The two primitives that are supported: shape.Rect, and shape.Path
        self._cached_selected_rects = []
        self._cached_selected_paths = []
        self._current_building_path = []

        self._edit_mode = self.EditMode.PAINT
        self._walk_mode = Partition.WalkMode.SPIRAL_CW
        self._coord_mode: ImageWidget.CoordMode = self.CoordMode.ADD

        self._background_color = QColor(
            get_global_preferences().get_partition_background_color_name()
        )
        self._foreground_color = QColor(
            get_global_preferences().get_partition_foreground_color_name()
        )

        self._zoom_factor = PAINT_SCALE_FACTOR

        self._pan_last_pos = None

        # To receive keyboard events, the widget needs a focus policy.
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Set initial size
        self._update_widget_size()

    def _rebuild_cache(self):
        self._cached_rects_dict = {}
        self._cached_paths_dict = {}
        for shape in self._original_shapes:
            if isinstance(shape, Rect):
                self._cached_rects_dict[(shape.x, shape.y)] = QRect(shape.x, shape.y, 1, 1)
            elif isinstance(shape, Path):
                point_list = shape.path
                if len(point_list) < 2:
                    continue
                path = QPainterPath()
                path.moveTo(point_list[0].x, point_list[0].y)
                for point in point_list[1:]:
                    path.lineTo(point.x, point.y)
                self._cached_paths_dict[point_list[0].x, point_list[0].y] = path

        self._cached_all_rects = list(self._cached_rects_dict.values())
        self._cached_all_paths = list(self._cached_paths_dict.values())

    def _update_widget_size(self):
        """
        Resizes the widget to match the current zoom level.
        This ensures the QScrollArea updates its scrollbars correctly.
        """
        # resize() directly sets the widget's size. The QScrollArea (with
        # setWidgetResizable(False)) uses this size to calculate the scrollable area.
        self.resize(self.sizeHint())
        # We still call update() to schedule a repaint with the new zoom level.
        self.update()

    def zoom_in(self):
        """Increases the zoom factor."""
        self._zoom_factor = min(2.5 * PAINT_SCALE_FACTOR, self._zoom_factor * 1.25)
        self._update_widget_size()

    def zoom_out(self):
        """Decreases the zoom factor."""
        self._zoom_factor = max(0.25 * PAINT_SCALE_FACTOR, self._zoom_factor / 1.25)
        self._update_widget_size()

    def zoom_reset(self):
        self._zoom_factor = PAINT_SCALE_FACTOR
        self._update_widget_size()

    def wheelEvent(self, event: QWheelEvent):
        """Handles mouse wheel events for zooming (requires Ctrl key)."""
        # A common UI pattern is to require a modifier key for zooming to
        # differentiate from scrolling. We'll use the Control key.
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            angle = event.angleDelta().y()
            if angle > 0:
                self.zoom_in()
            elif angle < 0:
                self.zoom_out()
            # Accept the event to prevent it from being passed to the parent (QScrollArea)
            event.accept()
        else:
            # If Ctrl is not pressed, pass the event to the base class. This allows
            # the parent QScrollArea to handle it for normal scrolling.
            super().wheelEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        """Handles keyboard press events."""
        key = event.key()

        modifiers = event.modifiers()  # Get the current modifiers

        # Check if Shift is pressed
        is_shift_pressed = modifiers & Qt.KeyboardModifier.ShiftModifier

        # Use the parent dialog's actions to ensure the UI stays in sync
        dialog_actions = self._partition_dialog._mode_actions

        if key == Qt.Key.Key_P:
            dialog_actions[self.EditMode.PAINT].trigger()
            event.accept()
        elif key == Qt.Key.Key_F:
            dialog_actions[self.EditMode.FILL].trigger()
            event.accept()
        elif key == Qt.Key.Key_S:
            dialog_actions[self.EditMode.SELECT].trigger()
            event.accept()
        elif key in [Qt.Key.Key_Plus, Qt.Key.Key_Equal]:
            self.zoom_in()
            event.accept()
        elif key == Qt.Key.Key_Minus:
            self.zoom_out()
            event.accept()
        elif key in (Qt.Key.Key_0, Qt.Key.Key_1):
            self.zoom_reset()
            event.accept()
        elif key == Qt.Key.Key_Escape:
            if self._current_building_path:
                self._current_building_path = []
                self.update()
            else:
                # Clear the selection and update the UI
                self.set_selected_shapes([])
                self._partition_dialog.update_shapes([], self._original_shapes)
            event.accept()
        elif key in [Qt.Key.Key_Return, Qt.Key.Key_Enter]:
            if self._edit_mode == self.EditMode.ADD_PATH:
                self._finalize_current_path()
            event.accept()
        elif (
            key in [Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Left, Qt.Key.Key_Right]
            and is_shift_pressed
        ):
            # Emulate QListWidget behavior to select items.
            # This is needed since QListWidget; when it loses focus, it doesn't
            #  keep the state of the current cursor position on the selected items.
            # At least this is true for Qt 6.9
            if key in [Qt.Key.Key_Up, Qt.Key.Key_Left]:
                self._selected_shapes = self._selected_shapes[:-1]
            elif key in [Qt.Key.Key_Down, Qt.Key.Key_Right]:
                for shape in self._original_shapes:
                    if shape not in self._selected_shapes:
                        self._selected_shapes.append(shape)
                        break
            self.set_selected_shapes(self._selected_shapes)
            full_shapes = self._selected_shapes[:]
            for shape in self._original_shapes:
                if shape not in full_shapes:
                    full_shapes.append(shape)
            # Update original shapes with new order
            self._original_shapes = full_shapes
            self._partition_dialog.update_shapes(self._selected_shapes, full_shapes)
            event.accept()
        elif key in [Qt.Key.Key_Delete, Qt.Key.Key_Backspace]:
            self.delete_selection()
            event.accept()
        else:
            # If we don't handle the key, pass the event to the base class
            super().keyPressEvent(event)

    def _update_shape(self, shape: Shape):
        if shape not in self._original_shapes:
            logger.debug(f"Coordinate outside of color: {shape}")
            return

        if self._coord_mode == self.CoordMode.ADD:
            if shape not in self._selected_shapes:
                self._selected_shapes.append(shape)
        elif self._coord_mode == self.CoordMode.REMOVE:
            if shape in self._selected_shapes:
                self._selected_shapes.remove(shape)
        else:
            logger.warning(f"Invalid coord mode: {self._coord_mode}")

        self._update_selected_shapes_cache()

    def _update_selected_shapes_cache(self):
        self._cached_selected_rects = []
        self._cached_selected_paths = []
        for shape in self._selected_shapes:
            if isinstance(shape, Rect):
                self._cached_selected_rects.append(self._cached_rects_dict[(shape.x, shape.y)])
            elif isinstance(shape, Path):
                # shape.path is a list[Point]
                point_list = shape.path
                if len(point_list) < 2:
                    continue
                path = QPainterPath()
                path.moveTo(point_list[0].x, point_list[0].y)
                for point in point_list[1:]:
                    path.lineTo(point.x, point.y)
                self._cached_selected_paths.append(path)
            else:
                raise Exception(f"Unknown shape: {shape}")
        self.update()

    def set_selected_shapes(self, shapes: list[Shape]):
        self._selected_shapes = shapes
        self._update_selected_shapes_cache()

    def delete_selection(self):
        if not self._selected_shapes:
            return

        # Remove selected shapes from original shapes
        for shape in self._selected_shapes:
            if shape in self._original_shapes:
                self._original_shapes.remove(shape)

        self._partition_dialog.remove_shapes(self._selected_shapes)
        self.set_selected_shapes([])
        self._rebuild_cache()
        self.update()

    def set_edit_mode(self, mode: EditMode):
        self._edit_mode = mode

    def set_walk_mode(self, mode: Partition.WalkMode):
        self._walk_mode = mode

    def paintEvent(self, event):
        painter = QPainter(self)
        pixmap = QPixmap.fromImage(self._image)
        painter.scale(self._zoom_factor, self._zoom_factor)
        painter.drawPixmap(0, 0, pixmap)

        # painter.setPen(Qt.NoPen)
        painter.setPen(QPen(Qt.GlobalColor.gray, 0.1, Qt.PenStyle.SolidLine))

        # Set the brush (fill)
        brush = painter.brush()
        brush.setStyle(Qt.BrushStyle.SolidPattern)
        brush.setColor(self._background_color)
        painter.setBrush(brush)

        painter.drawRects(self._cached_all_rects)

        painter.save()
        # For paths (to avoid jump stitches), we want to draw a visible line.
        pen = QPen(self._background_color, 2.0 / self._zoom_factor, Qt.PenStyle.DotLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for path in self._cached_all_paths:
            painter.drawPath(path)
        painter.restore()

        painter.save()
        brush = painter.brush()
        brush.setColor(self._foreground_color)
        painter.setBrush(brush)
        painter.drawRects(self._cached_selected_rects)
        painter.restore()

        # For paths (to avoid jump stitches), we want to draw a visible line.
        painter.save()
        pen = QPen(self._foreground_color, 4.0 / self._zoom_factor, Qt.PenStyle.DotLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for path in self._cached_selected_paths:
            painter.drawPath(path)
        painter.restore()

        if self._current_building_path:
            painter.save()
            pen = QPen(self._foreground_color, 2.0 / self._zoom_factor, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)

            path = QPainterPath()
            if len(self._current_building_path) > 0:
                p0 = self._current_building_path[0]
                path.moveTo(p0.x, p0.y)
                for p in self._current_building_path[1:]:
                    path.lineTo(p.x, p.y)

            painter.drawPath(path)

            # Draw points
            painter.setBrush(self._foreground_color)
            w = 4.0 / self._zoom_factor
            h = 4.0 / self._zoom_factor
            for p in self._current_building_path:
                painter.drawEllipse(QPointF(p.x, p.y), w, h)

            painter.restore()

        painter.end()

    def _finalize_current_path(self):
        if len(self._current_building_path) >= 2:
            new_path = Path(self._current_building_path)

            insert_index = len(self._original_shapes)
            if self._selected_shapes:
                # Find the max index of selected shapes
                indices = [
                    self._original_shapes.index(s)
                    for s in self._selected_shapes
                    if s in self._original_shapes
                ]
                if indices:
                    insert_index = max(indices) + 1

            self._original_shapes.insert(insert_index, new_path)
            self._partition_dialog.update_shapes(self._selected_shapes, self._original_shapes)
            self._rebuild_cache()
        self._current_building_path = []
        self.update()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_last_pos = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

        if self._edit_mode not in [
            ImageWidget.EditMode.PAINT,
            ImageWidget.EditMode.FILL,
            ImageWidget.EditMode.ADD_PATH,
        ]:
            event.ignore()
            return
        event.accept()
        pos = event.pos()
        x = pos.x() / self._zoom_factor
        y = pos.y() / self._zoom_factor
        shape = Rect(int(x), int(y))

        if shape not in self._original_shapes:
            event.ignore()
            return

        match self._edit_mode:
            case ImageWidget.EditMode.PAINT:
                self._coord_mode = (
                    self.CoordMode.ADD if event.button() == Qt.LeftButton else self.CoordMode.REMOVE
                )
                self._update_shape(shape)
            case ImageWidget.EditMode.FILL:
                if shape in self._selected_shapes:
                    # Could be a user error, when it clicks a pixel that it is already painted
                    return
                partial_partition = list(set(self._original_shapes) - set(self._selected_shapes))
                # Create temporal partition
                part = Partition(partial_partition)
                part.walk_path(self._walk_mode, (shape.x, shape.y))
                ordered_partition = part.path
                self._selected_shapes = self._selected_shapes + ordered_partition
                self._update_selected_shapes_cache()
            case ImageWidget.EditMode.ADD_PATH:
                if event.button() == Qt.MouseButton.RightButton:
                    self._finalize_current_path()
                elif event.button() == Qt.LeftButton:
                    self._current_building_path.append(Point(int(x), int(y)))
                    print(f"Added point: ({int(x)}, {int(y)})")
                    self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() & Qt.MouseButton.MiddleButton and self._pan_last_pos:
            scroll_area = self._partition_dialog._scroll_area
            h_bar = scroll_area.horizontalScrollBar()
            v_bar = scroll_area.verticalScrollBar()

            delta = event.pos() - self._pan_last_pos
            h_bar.setValue(h_bar.value() - delta.x())
            v_bar.setValue(v_bar.value() - delta.y())

            self._pan_last_pos = event.pos()
            event.accept()
            return

        if self._edit_mode not in [
            ImageWidget.EditMode.PAINT,
        ]:
            event.ignore()
            return

        event.accept()
        pos = event.pos()
        x = pos.x() / self._zoom_factor
        y = pos.y() / self._zoom_factor
        shape = Rect(int(x), int(y))

        self._update_shape(shape)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_last_pos = None
            self.unsetCursor()
            event.accept()
            return

        if self._edit_mode not in [
            ImageWidget.EditMode.PAINT,
            ImageWidget.EditMode.FILL,
        ]:
            event.ignore()
            return

        event.accept()
        if len(self._selected_shapes) == 0:
            return
        full_shapes = self._selected_shapes[:]
        for shape in self._original_shapes:
            if shape not in full_shapes:
                full_shapes.append(shape)
        # Update original shapes with new order
        self._original_shapes = full_shapes
        self._partition_dialog.update_shapes(self._selected_shapes, full_shapes)

    def sizeHint(self):
        return QSize(
            self._image.size().width() * self._zoom_factor,
            self._image.size().height() * self._zoom_factor,
        )


class PartitionDialog(QDialog):
    def __init__(self, image: QImage, partition: Partition):
        super().__init__()

        self.setWindowTitle(self.tr("Partition Editor"))
        shapes = partition.path

        # Create Image Widget
        self._image_widget = ImageWidget(self, image, shapes)

        #  Wrap ImageWidget in a QScrollArea to handle zooming
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidget(self._image_widget)
        # Let the widget's sizeHint dictate the size, don't stretch it.
        self._scroll_area.setWidgetResizable(False)
        # A dark background for the scroll area looks better.
        self._scroll_area.setBackgroundRole(QPalette.ColorRole.Dark)

        # Create List Widget
        self._list_widget = QListWidget()
        self._list_widget.installEventFilter(self)
        self._populate_list_widget(shapes)
        self._connect_list_widget()

        self._mode_actions = {}
        self._fill_mode_actions = {}

        self._edit_mode = None
        self._set_edit_mode(ImageWidget.EditMode.PAINT)

        # Layouts
        image_list_layout = QHBoxLayout()
        image_list_layout.addWidget(self._scroll_area, 1)
        image_list_layout.addWidget(self._list_widget, 0)

        toolbar = QToolBar()

        # Edit modes
        action_modes = [
            (
                ImageWidget.EditMode.PAINT,
                self.tr("Paint"),
                "draw-freehand-symbolic.svg",
            ),
            (
                ImageWidget.EditMode.ADD_PATH,
                self.tr("Add Path"),
                "draw-path-symbolic.svg",
            ),
            (ImageWidget.EditMode.FILL, self.tr("Fill"), "color-fill-symbolic.svg"),
            (
                ImageWidget.EditMode.SELECT,
                self.tr("Select"),
                "dialog-layers-symbolic.svg",
            ),
        ]
        for mode in action_modes:
            path = f":/icons/svg/actions/{mode[2]}"
            icon = create_icon_from_svg(path, ICON_SIZE)
            action = QAction(icon, mode[1], self)
            toolbar.addAction(action)
            action.setCheckable(True)
            action.triggered.connect(self._on_action_edit_mode)
            action.setData(mode[0])
            self._mode_actions[mode[0]] = action
        self._mode_actions[ImageWidget.EditMode.PAINT].setChecked(True)

        toolbar.addSeparator()

        # Fill modes
        fill_modes = [
            (
                Partition.WalkMode.SPIRAL_CW,
                self.tr("Spiral CW"),
                "arrow-clockwise-pixem.svg",
            ),
            (
                Partition.WalkMode.SPIRAL_CCW,
                self.tr("Spiral CCW"),
                "arrow-counter-clockwise-pixem.svg",
            ),
            (Partition.WalkMode.RANDOM, self.tr("Random"), "randomize-symbolic.svg"),
        ]

        for mode in fill_modes:
            path = f":/icons/svg/actions/{mode[2]}"
            icon = create_icon_from_svg(path, ICON_SIZE)
            action = QAction(icon, mode[1], self)
            toolbar.addAction(action)
            action.setCheckable(True)
            action.triggered.connect(self._on_action_fill_mode)
            action.setData(mode[0])
            # Only enable them when "fill mode" is enabled
            action.setEnabled(False)
            self._fill_mode_actions[mode[0]] = action
        self._fill_mode_actions[Partition.WalkMode.SPIRAL_CW].setChecked(True)

        toolbar.addSeparator()
        zoom_actions = [
            (
                self.tr("Zoom In"),
                "zoom-in",
                QKeySequence.StandardKey.ZoomIn,
                self._on_zoom_in,
            ),
            (
                self.tr("Zoom Out"),
                "zoom-out",
                QKeySequence.StandardKey.ZoomOut,
                self._on_zoom_out,
            ),
        ]
        for text, icon_name, key_sequence, slot in zoom_actions:
            action = QAction(QIcon.fromTheme(icon_name), text, self)
            action.setShortcut(key_sequence)
            toolbar.addAction(action)
            action.triggered.connect(slot)

        # Create Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 10)
        main_layout.addWidget(toolbar)
        main_layout.addLayout(image_list_layout)
        main_layout.addWidget(button_box)

        self.setLayout(main_layout)

    def _connect_list_widget(self):
        self._list_widget.model().rowsMoved.connect(self._on_rows_moved)
        self._list_widget.itemSelectionChanged.connect(self._on_item_selection_changed)

    def _disconnect_list_widget(self):
        self._list_widget.model().rowsMoved.disconnect(self._on_rows_moved)
        self._list_widget.itemSelectionChanged.disconnect(self._on_item_selection_changed)

    def _populate_list_widget(self, shapes: list[Shape]):
        # precondition: list_widget should not have "connected" slots.
        for i, shape in enumerate(shapes):
            if isinstance(shape, Rect):
                item = QListWidgetItem(f"{i} - Rect({shape.x}, {shape.y})")
                self._list_widget.addItem(item)
                item.setData(Qt.UserRole, shape)
            elif isinstance(shape, Path):
                item = QListWidgetItem(f"{i} - Path({shape.path})")
                self._list_widget.addItem(item)
                item.setData(Qt.UserRole, shape)
            else:
                raise Exception(f"Unknown shape: {shape}")

    def _set_edit_mode(self, mode: ImageWidget.EditMode):
        if mode != self._edit_mode:
            self._edit_mode = mode
            self._image_widget.set_edit_mode(mode)

            match mode:
                case ImageWidget.EditMode.PAINT:
                    self._list_widget.setDragDropMode(QListWidget.NoDragDrop)
                    self._list_widget.setSelectionMode(QListWidget.ContiguousSelection)
                case ImageWidget.EditMode.ADD_PATH:
                    self._list_widget.setDragDropMode(QListWidget.NoDragDrop)
                    self._list_widget.setSelectionMode(QListWidget.ContiguousSelection)
                case ImageWidget.EditMode.FILL:
                    self._list_widget.setDragDropMode(QListWidget.NoDragDrop)
                    self._list_widget.setSelectionMode(QListWidget.ContiguousSelection)
                case ImageWidget.EditMode.SELECT:
                    self._list_widget.setDragDropMode(QListWidget.InternalMove)
                    self._list_widget.setSelectionMode(QListWidget.ExtendedSelection)

            enabled = mode == ImageWidget.EditMode.FILL
            self._enable_fill_mode_actions(enabled)

    def _enable_fill_mode_actions(self, enabled: bool):
        for action in self._fill_mode_actions.values():
            action.setEnabled(enabled)

    def _set_walk_mode(self, mode: Partition.WalkMode):
        self._image_widget.set_walk_mode(mode)

    @Slot()
    def _on_zoom_in(self):
        self._image_widget.zoom_in()

    @Slot()
    def _on_zoom_out(self):
        self._image_widget.zoom_out()

    @Slot()
    def _on_action_edit_mode(self, value):
        sender: QAction = self.sender()
        if sender not in self._mode_actions.values():
            logger.warning("Unknown actions {sender}")
            return
        for action in self._mode_actions.values():
            action.setChecked(False)

        sender.setChecked(True)

        mode: ImageWidget.EditMode = sender.data()
        self._set_edit_mode(mode)

    @Slot()
    def _on_action_fill_mode(self, value):
        sender: QAction = self.sender()
        if sender not in self._fill_mode_actions.values():
            logger.warning("Unknown actions {sender}")
            return
        for action in self._fill_mode_actions.values():
            action.setChecked(False)
        sender.setChecked(True)

        mode: Partition.WalkMode = sender.data()
        self._set_walk_mode(mode)

    @Slot()
    def _on_rows_moved(self, parent, start, end, destination):
        # FIXME: Do something ? It seems that the partition data was automatically updated (???)
        # You can access the new order of items here
        # for row in range(self._list_widget.count()):
        #     item = self._list_widget.item(row)
        pass

    @Slot()
    def _on_item_selection_changed(self):
        selected_items = self._list_widget.selectedItems()
        selected_shapes = [item.data(Qt.UserRole) for item in selected_items]
        self._image_widget.set_selected_shapes(selected_shapes)
        # logger.info(f"Current Index: {self._list_widget.currentIndex()}")

    def update_shapes(self, selected_shapes: list[Shape], full_shapes: list[Shape]):
        """
        Update the selected shapes in the list widget.
        Called from ImageWidget.
        """
        self._disconnect_list_widget()

        lastest_selected_item = None
        for i, shape in enumerate(full_shapes):
            item = self._list_widget.item(i)
            if item is None:
                item = QListWidgetItem()
                self._list_widget.addItem(item)

            if isinstance(shape, Rect):
                item.setText(f"{i} - Rect({shape.x}, {shape.y})")
            elif isinstance(shape, Path):
                item.setText(f"{i} - Path({shape.path})")
            else:
                raise Exception(f"Unknown shape: {shape}")
            item.setData(Qt.UserRole, shape)
            selected = shape in selected_shapes
            item.setSelected(selected)
            if selected:
                lastest_selected_item = item
        if lastest_selected_item is not None:
            index = self._list_widget.indexFromItem(lastest_selected_item)
            self._list_widget.selectionModel().setCurrentIndex(
                index, QItemSelectionModel.SelectCurrent
            )

        self._connect_list_widget()

    def remove_shapes(self, shapes_to_remove: list[Shape]):
        """
        Remove the specified shapes from the list widget.
        Called from ImageWidget.
        """
        self._disconnect_list_widget()

        # We need to find the items associated with the shapes
        # Since we don't have a direct mapping, we iterate.
        # It is safer to iterate backwards when removing items.
        for i in range(self._list_widget.count() - 1, -1, -1):
            item = self._list_widget.item(i)
            shape = item.data(Qt.UserRole)
            if shape in shapes_to_remove:
                self._list_widget.takeItem(i)

        self._connect_list_widget()

    def get_path(self) -> list[Shape]:
        """
        Return the path.
        Called from MainWindow.
        """
        path = [
            self._list_widget.item(i).data(Qt.UserRole) for i in range(self._list_widget.count())
        ]
        return path

    def eventFilter(self, source, event):
        if event.type() == QKeyEvent.Type.KeyPress and source is self._list_widget:
            if event.key() in [Qt.Key.Key_Delete, Qt.Key.Key_Backspace]:
                self._image_widget.delete_selection()
                return True
        return super().eventFilter(source, event)
