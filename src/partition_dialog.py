# Pixem
# Copyright 2025 - Ricardo Quesada

import logging
from enum import Enum, auto

from PySide6.QtCore import QRect, QSize, Qt, Slot
from PySide6.QtGui import QAction, QColor, QImage, QMouseEvent, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from image_utils import create_icon_from_svg
from partition import Partition

PAINT_SCALE_FACTOR = 12
ICON_SIZE = 22

logger = logging.getLogger(__name__)


class ImageWidget(QWidget):
    class CoordMode(Enum):
        ADD = auto()
        REMOVE = auto()

    class EditMode(Enum):
        PAINT = auto()
        FILL = auto()
        SELECT = auto()

    def __init__(self, partition_dialog, image: QImage, coords: list[tuple[int, int]]):
        super().__init__()
        self._partition_dialog = partition_dialog
        self._image = image
        self._original_coords = coords
        self._selected_coords = []

        self.setMinimumSize(self._image.size())  # Ensure widget is at least image size

        self._cached_rects = [QRect(x, y, 1, 1) for x, y in coords]
        self._cached_selected_rects = []

        self._edit_mode = self.EditMode.PAINT
        self._walk_mode = Partition.WalkMode.SPIRAL_CW
        self._coord_mode: ImageWidget.CoordMode = self.CoordMode.ADD

    def _update_coordinate(self, coord: tuple[int, int]):
        if coord not in self._original_coords:
            logger.warning(f"Invalid coordinate: {coord}")
            return

        if self._coord_mode == self.CoordMode.ADD:
            if coord not in self._selected_coords:
                self._selected_coords.append(coord)
        elif self._coord_mode == self.CoordMode.REMOVE:
            if coord in self._selected_coords:
                self._selected_coords.remove(coord)
        else:
            logger.warning(f"Invalid coord mode: {self._coord_mode}")

        self._update_selected_coords_cache()

    def _update_selected_coords_cache(self):
        self._cached_selected_rects = [QRect(x, y, 1, 1) for x, y in self._selected_coords]
        self.update()

    def set_selected_coords(self, coords: list[tuple[int, int]]):
        self._selected_coords = coords
        self._update_selected_coords_cache()

    def set_edit_mode(self, mode: EditMode):
        self._edit_mode = mode

    def set_walk_mode(self, mode: Partition.WalkMode):
        self._walk_mode = mode

    def paintEvent(self, event):
        painter = QPainter(self)
        pixmap = QPixmap.fromImage(self._image)
        painter.scale(PAINT_SCALE_FACTOR, PAINT_SCALE_FACTOR)
        painter.drawPixmap(0, 0, pixmap)

        # painter.setPen(Qt.NoPen)
        painter.setPen(QPen(Qt.GlobalColor.gray, 0.1, Qt.PenStyle.SolidLine))

        # Set the brush (fill)
        brush = painter.brush()
        brush.setStyle(Qt.BrushStyle.SolidPattern)
        brush.setColor(QColor(255, 0, 0, 128))
        painter.setBrush(brush)

        painter.drawRects(self._cached_rects)

        brush = painter.brush()
        brush.setColor(QColor(0, 0, 255, 128))
        painter.setBrush(brush)
        painter.drawRects(self._cached_selected_rects)

        painter.end()

    def mousePressEvent(self, event: QMouseEvent):
        if self._edit_mode not in [ImageWidget.EditMode.PAINT, ImageWidget.EditMode.FILL]:
            event.ignore()
            return
        event.accept()
        pos = event.pos()
        x = pos.x() / PAINT_SCALE_FACTOR
        y = pos.y() / PAINT_SCALE_FACTOR
        coord = (int(x), int(y))

        if coord not in self._original_coords:
            event.ignore()
            return

        match self._edit_mode:
            case ImageWidget.EditMode.PAINT:
                self._coord_mode = (
                    self.CoordMode.ADD if event.button() == Qt.LeftButton else self.CoordMode.REMOVE
                )
                self._update_coordinate(coord)
            case ImageWidget.EditMode.FILL:
                if coord in self._selected_coords:
                    # Could be a user error, when it clicks a pixel that it is already painted
                    return
                partial_partition = list(set(self._original_coords) - set(self._selected_coords))
                # Create temporal partition
                part = Partition(partial_partition)
                part.walk_path(self._walk_mode, coord)
                ordered_partition = part.path
                self._selected_coords = self._selected_coords + ordered_partition
                self._update_selected_coords_cache()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._edit_mode not in [
            ImageWidget.EditMode.PAINT,
        ]:
            event.ignore()
            return

        event.accept()
        pos = event.pos()
        x = pos.x() / PAINT_SCALE_FACTOR
        y = pos.y() / PAINT_SCALE_FACTOR
        coord = (int(x), int(y))

        self._update_coordinate(coord)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._edit_mode not in [ImageWidget.EditMode.PAINT, ImageWidget.EditMode.FILL]:
            event.ignore()
            return

        event.accept()
        if len(self._selected_coords) == 0:
            return
        full_coords = self._selected_coords[:]
        for coord in self._original_coords:
            if coord not in full_coords:
                full_coords.append(coord)
        self._partition_dialog.update_coords(self._selected_coords, full_coords)

    def sizeHint(self):
        return QSize(
            self._image.size().width() * PAINT_SCALE_FACTOR,
            self._image.size().height() * PAINT_SCALE_FACTOR,
        )


class PartitionDialog(QDialog):
    def __init__(self, image: QImage, partition: Partition):
        super().__init__()

        self.setWindowTitle(self.tr("Partition Editor"))
        coords = partition.path

        # Create Image Widget
        self._image_widget = ImageWidget(self, image, coords)

        # Create List Widget
        self._list_widget = QListWidget()
        self._connect_list_widget()

        self.update_coords([], coords)

        self._mode_actions = {}
        self._fill_mode_actions = {}

        self._edit_mode = None
        self._set_edit_mode(ImageWidget.EditMode.PAINT)

        # Layouts
        image_list_layout = QHBoxLayout()
        image_list_layout.addWidget(self._image_widget)
        image_list_layout.addWidget(self._list_widget)

        toolbar = QToolBar()

        # Edit modes
        action_modes = [
            (ImageWidget.EditMode.PAINT, self.tr("Paint"), "draw-freehand-symbolic.svg"),
            (ImageWidget.EditMode.FILL, self.tr("Fill"), "color-fill-symbolic.svg"),
            (ImageWidget.EditMode.SELECT, self.tr("Select"), "dialog-layers-symbolic.svg"),
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
            (Partition.WalkMode.SPIRAL_CW, self.tr("Spiral CW"), "arrow-clockwise-pixem.svg"),
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
        self._list_widget.itemSelectionChanged.connect(self._on_selection_changed)

    def _disconnect_list_widget(self):
        self._list_widget.model().rowsMoved.disconnect(self._on_rows_moved)
        self._list_widget.itemSelectionChanged.disconnect(self._on_selection_changed)

    def _set_edit_mode(self, mode: ImageWidget.EditMode):
        if mode != self._edit_mode:
            self._edit_mode = mode
            self._image_widget.set_edit_mode(mode)

            match mode:
                case ImageWidget.EditMode.PAINT:
                    self._list_widget.setDragDropMode(QListWidget.NoDragDrop)  # Enable reordering
                    self._list_widget.setSelectionMode(QListWidget.ContiguousSelection)
                case ImageWidget.EditMode.FILL:
                    self._list_widget.setDragDropMode(QListWidget.NoDragDrop)  # Enable reordering
                    self._list_widget.setSelectionMode(QListWidget.ContiguousSelection)
                case ImageWidget.EditMode.SELECT:
                    self._list_widget.setDragDropMode(QListWidget.InternalMove)  # Enable reordering
                    self._list_widget.setSelectionMode(QListWidget.ExtendedSelection)

            enabled = mode == ImageWidget.EditMode.FILL
            self._enable_fill_mode_actions(enabled)

    def _enable_fill_mode_actions(self, enabled: bool):
        for action in self._fill_mode_actions.values():
            action.setEnabled(enabled)

    def _set_walk_mode(self, mode: Partition.WalkMode):
        self._image_widget.set_walk_mode(mode)

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
    def _on_selection_changed(self):
        selected_items = self._list_widget.selectedItems()
        selected_coords = [item.data(Qt.UserRole) for item in selected_items]
        self._image_widget.set_selected_coords(selected_coords)

    def update_coords(
        self, selected_coords: list[tuple[int, int]], full_coords: list[tuple[int, int]]
    ):
        self._disconnect_list_widget()

        self._list_widget.clear()
        for i, coord in enumerate(full_coords):
            item = QListWidgetItem(f"{i} - [{coord[0]} x {coord[1]}]")
            self._list_widget.addItem(item)
            item.setData(Qt.UserRole, coord)
            selected = coord in selected_coords
            item.setSelected(selected)
        self._connect_list_widget()

    def get_path(self):
        path = [
            self._list_widget.item(i).data(Qt.UserRole) for i in range(self._list_widget.count())
        ]
        return path
