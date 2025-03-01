import logging
from enum import Enum, auto

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QAction, QColor, QIcon, QImage, QMouseEvent, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from partition import Partition, order_partition

PAINT_SCALE_FACTOR = 12

logger = logging.getLogger(__name__)  # __name__ gets the current module's name


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

        match self._edit_mode:
            case ImageWidget.EditMode.PAINT:
                self._coord_mode = (
                    self.CoordMode.ADD if event.button() == Qt.LeftButton else self.CoordMode.REMOVE
                )
                self._update_coordinate(coord)
            case ImageWidget.EditMode.FILL:
                partial_partition = list(set(self._original_coords) - set(self._selected_coords))
                ordered_partition = order_partition(partial_partition, coord, self._walk_mode)
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

        self.setWindowTitle("Partition Editor")
        coords = partition.path

        # Create Image Widget
        self._image_widget = ImageWidget(self, image, coords)

        # Create List Widget
        self._list_widget = QListWidget()
        self._list_widget.setDragDropMode(QListWidget.InternalMove)  # Enable reordering
        self._list_widget.setSelectionMode(QListWidget.ExtendedSelection)

        self._connect_list_widget()

        self.update_coords([], coords)

        self._edit_mode = ImageWidget.EditMode.PAINT
        self._set_edit_mode(ImageWidget.EditMode.PAINT)

        # Create Buttons
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")

        # Connect Buttons
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        # Layouts
        image_list_layout = QHBoxLayout()
        image_list_layout.addWidget(self._image_widget)
        image_list_layout.addWidget(self._list_widget)

        button_layout = QHBoxLayout()
        button_layout.addStretch()  # Add space before buttons
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)

        toolbar = QToolBar()

        # Edit modes
        pixmap = QPixmap(":/res/icons/22x22/categories/applications-graphics.png")
        self._paint_action = QAction(QIcon(pixmap), "Paint", self)
        pixmap = QPixmap(":/res/icons/22x22/actions/stock-tool-bucket-fill.png")
        self._fill_action = QAction(QIcon(pixmap), "Fill", self)
        pixmap = QPixmap(":/res/icons/22x22/actions/stock-tool-rect-select.png")
        self._select_action = QAction(QIcon(pixmap), "Select", self)
        actions = [self._paint_action, self._fill_action, self._select_action]
        toolbar.addActions(actions)
        for action in actions:
            action.setCheckable(True)
            action.triggered.connect(self._on_action_edit_mode)
        self._paint_action.setChecked(True)

        toolbar.addSeparator()

        # Fill modes
        pixmap = QPixmap(":/res/icons/22x22/actions/go-up.png")
        self._fill_spiral_cw_action = QAction(QIcon(pixmap), "Spiral CW", self)
        pixmap = QPixmap(":/res/icons/22x22/actions/go-down.png")
        self._fill_spiral_ccw_action = QAction(QIcon(pixmap), "Spiral CCW", self)
        pixmap = QPixmap(":/res/icons/22x22/actions/go-previous.png")
        self._fill_snake_cw_action = QAction(QIcon(pixmap), "Snake CW", self)
        pixmap = QPixmap(":/res/icons/22x22/actions/go-next.png")
        self._fill_snake_ccw_action = QAction(QIcon(pixmap), "Snake CCW", self)
        actions = [
            self._fill_spiral_cw_action,
            self._fill_spiral_ccw_action,
            self._fill_snake_cw_action,
            self._fill_snake_ccw_action,
        ]
        toolbar.addActions(actions)
        for action in actions:
            action.setCheckable(True)
            action.triggered.connect(self._on_action_walk_mode)
        self._fill_spiral_cw_action.setChecked(True)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 10)
        main_layout.addWidget(toolbar)
        main_layout.addLayout(image_list_layout)
        main_layout.addLayout(button_layout)

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

    def _set_walk_mode(self, mode: Partition.WalkMode):
        self._image_widget.set_walk_mode(mode)

    def _on_action_edit_mode(self, value):
        actions = [self._paint_action, self._fill_action, self._select_action]
        sender: QAction = self.sender()
        if sender not in actions:
            logger.warning("Unknown actions {sender}")
            return
        for action in actions:
            action.setChecked(False)
        sender.setChecked(True)

        mode = ImageWidget.EditMode.PAINT
        match sender:
            case self._paint_action:
                mode = ImageWidget.EditMode.PAINT
            case self._fill_action:
                mode = ImageWidget.EditMode.FILL
            case self._select_action:
                mode = ImageWidget.EditMode.SELECT
        self._set_edit_mode(mode)

    def _on_action_walk_mode(self, value):
        actions = [
            self._fill_spiral_cw_action,
            self._fill_spiral_ccw_action,
            self._fill_snake_cw_action,
            self._fill_snake_ccw_action,
        ]
        sender: QAction = self.sender()
        if sender not in actions:
            logger.warning("Unknown actions {sender}")
            return
        for action in actions:
            action.setChecked(False)
        sender.setChecked(True)

        mode = Partition.WalkMode.SPIRAL_CW
        match sender:
            case self._fill_spiral_cw_action:
                mode = Partition.WalkMode.SPIRAL_CW
            case self._fill_spiral_ccw_action:
                mode = Partition.WalkMode.SPIRAL_CCW
            case self._fill_snake_cw_action:
                mode = Partition.WalkMode.SNAKE_CW
            case self._fill_snake_ccw_action:
                mode = Partition.WalkMode.SNAKE_CCW
        self._set_walk_mode(mode)

    def _on_rows_moved(self, parent, start, end, destination):
        print(f"Rows moved from {start} to {end} to destination {destination}")
        # You can access the new order of items here
        for row in range(self._list_widget.count()):
            item = self._list_widget.item(row)
            print(f"  Item at row {row}: {item.text()}")

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
