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
        self._coord_mode: ImageWidget.CoordMode = self.CoordMode.ADD

    def set_selected_coords(self, coords: list[tuple[int, int]]):
        self._cached_selected_rects = [QRect(x, y, 1, 1) for x, y in coords]
        self.update()

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
        event.accept()
        pos = event.pos()
        x = pos.x() / PAINT_SCALE_FACTOR
        y = pos.y() / PAINT_SCALE_FACTOR
        coord = [int(x), int(y)]

        self._coord_mode = (
            self.CoordMode.ADD if event.button() == Qt.LeftButton else self.CoordMode.REMOVE
        )
        self._update_coordinate(coord)

    def mouseMoveEvent(self, event: QMouseEvent):
        event.accept()
        pos = event.pos()
        x = pos.x() / PAINT_SCALE_FACTOR
        y = pos.y() / PAINT_SCALE_FACTOR
        coord = [int(x), int(y)]

        self._update_coordinate(coord)

    def mouseReleaseEvent(self, event: QMouseEvent):
        event.accept()
        if len(self._selected_coords) == 0:
            return
        full_coords = self._selected_coords[:]
        for coord in self._original_coords:
            if coord not in full_coords:
                full_coords.append(coord)
        self._partition_dialog.update_coords(full_coords)

    def _update_coordinate(self, coord: tuple[int, int]):
        if coord not in self._original_coords:
            logger.info(f"Coordinates {coord} not in original coords")
            return

        if self._coord_mode == self.CoordMode.ADD:
            if coord not in self._selected_coords:
                self._selected_coords.append(coord)
        elif self._coord_mode == self.CoordMode.REMOVE:
            if coord in self._selected_coords:
                self._selected_coords.remove(coord)
        else:
            logger.warning(f"Invalid coord mode: {self._coord_mode}")

        self.set_selected_coords(self._selected_coords)
        self.update()

    def sizeHint(self):
        return QSize(
            self._image.size().width() * PAINT_SCALE_FACTOR,
            self._image.size().height() * PAINT_SCALE_FACTOR,
        )

    def set_edit_mode(self, mode: EditMode):
        self._edit_mode = mode


class PartitionDialog(QDialog):
    def __init__(self, image: QImage, path: list[tuple[int, int]]):
        super().__init__()

        self.setWindowTitle("Partition Editor")
        coords = path

        # Create Image Widget
        self._image_widget = ImageWidget(self, image, coords)

        # Create List Widget
        self._list_widget = QListWidget()
        self._list_widget.setDragDropMode(QListWidget.InternalMove)  # Enable reordering
        self._list_widget.setSelectionMode(QListWidget.ExtendedSelection)

        for coord in coords:
            item = QListWidgetItem(f"{coord[0]} x {coord[1]}")
            item.setData(Qt.UserRole, coord)
            self._list_widget.addItem(item)

        self._list_widget.model().rowsMoved.connect(self._on_rows_moved)
        self._list_widget.itemSelectionChanged.connect(self._on_selection_changed)

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
        self._paint_action = QAction(QIcon.fromTheme("document-open"), "Paint", self)
        self._paint_action.triggered.connect(self._on_action_mode_paint)
        self._fill_action = QAction(QIcon.fromTheme("document-save"), "Fill", self)
        self._fill_action.triggered.connect(self._on_action_mode_fill)
        self._select_action = QAction(QIcon.fromTheme("document-save"), "Select", self)
        self._select_action.triggered.connect(self._on_action_mode_select)
        actions = [self._paint_action, self._fill_action, self._select_action]
        toolbar.addActions(actions)
        for action in actions:
            action.setCheckable(True)
        self._paint_action.setChecked(True)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)  # Remove all margins
        main_layout.addWidget(toolbar)
        main_layout.addLayout(image_list_layout)
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

    def _on_action_mode_paint(self, value):
        self._paint_action.setChecked(True)
        self._fill_action.setChecked(False)
        self._select_action.setChecked(False)
        self._image_widget.set_edit_mode(ImageWidget.EditMode.PAINT)

    def _on_action_mode_fill(self, value):
        self._paint_action.setChecked(False)
        self._fill_action.setChecked(True)
        self._select_action.setChecked(False)
        self._image_widget.set_edit_mode(ImageWidget.EditMode.FILL)

    def _on_action_mode_select(self, value):
        self._paint_action.setChecked(False)
        self._fill_action.setChecked(False)
        self._select_action.setChecked(True)
        self._image_widget.set_edit_mode(ImageWidget.EditMode.SELECT)

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

    def update_coords(self, coords: list[tuple[int, int]]):
        self._list_widget.clear()
        for coord in coords:
            item = QListWidgetItem(f"{coord[0]} x {coord[1]}")
            item.setData(Qt.UserRole, coord)
            self._list_widget.addItem(item)

    def get_path(self):
        path = [
            self._list_widget.item(i).data(Qt.UserRole) for i in range(self._list_widget.count())
        ]
        return path
