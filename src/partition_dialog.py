from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QDialog, QHBoxLayout, QListWidget, QPushButton, QVBoxLayout, QWidget

PAINT_SCALE_FACTOR = 10


class ImageWidget(QWidget):
    def __init__(self, image: QImage, coords: list[tuple]):
        super().__init__()
        self._image = image
        self._coords = coords
        self.setMinimumSize(self._image.size())  # Ensure widget is at least image size

        self._cached_rects = [QRect(x, y, 1, 1) for x, y in self._coords]

    def paintEvent(self, event):
        painter = QPainter(self)
        pixmap = QPixmap.fromImage(self._image)
        painter.scale(PAINT_SCALE_FACTOR, PAINT_SCALE_FACTOR)
        painter.drawPixmap(0, 0, pixmap)

        painter.save()
        # painter.setPen(Qt.NoPen)
        painter.setPen(QPen(Qt.GlobalColor.gray, 0.1, Qt.PenStyle.SolidLine))

        # Set the brush (fill)
        brush = painter.brush()
        brush.setColor(QColor(255, 0, 0, 128))  # Red, semi-transparent fill
        brush.setStyle(Qt.BrushStyle.SolidPattern)  # Solid fill
        painter.setBrush(brush)
        painter.drawRects(self._cached_rects)
        painter.restore()
        painter.end()

    def sizeHint(self):
        return QSize(
            self._image.size().width() * PAINT_SCALE_FACTOR,
            self._image.size().height() * PAINT_SCALE_FACTOR,
        )


class PartitionDialog(QDialog):
    def __init__(self, image: QImage, partition: dict):
        super().__init__()

        self.setWindowTitle("Partition Editor")
        coords = partition["path"]

        # Create Image Widget
        self._image_widget = ImageWidget(image, coords)

        # Create List Widget
        self._list_widget = QListWidget()
        self._list_widget.setDragDropMode(QListWidget.InternalMove)  # Enable reordering
        items = [f"({coord[0]} x {coord[1]})" for coord in coords]
        self._list_widget.addItems(items)

        self._list_widget.model().rowsMoved.connect(self._on_rows_moved)

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

        main_layout = QVBoxLayout()
        main_layout.addLayout(image_list_layout)
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

    def _on_rows_moved(self, parent, start, end, destination):
        print(f"Rows moved from {start} to {end} to destination {destination}")
        # You can access the new order of items here
        for row in range(self._list_widget.count()):
            item = self._list_widget.item(row)
            print(f"  Item at row {row}: {item.text()}")

    def get_selected_items(self):
        return [item.text() for item in self._list_widget.selectedItems()]
