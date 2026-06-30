# Pixem
# Copyright 2026 - Ricardo Quesada

import logging
from enum import IntEnum, auto

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, QSize, Qt, Signal, Slot
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QGuiApplication,
    QIcon,
    QImage,
    QKeySequence,
    QMouseEvent,
    QPainter,
    QPalette,
    QPen,
    QPixmap,
    QUndoCommand,
    QUndoStack,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from image_utils import create_icon_from_svg

logger = logging.getLogger(__name__)

ICON_SIZE = 22


class EditImageCommand(QUndoCommand):
    """Local undo command for drawing strokes on the image."""

    def __init__(self, widget, old_image: QImage, new_image: QImage, description: str = "Draw"):
        super().__init__(description)
        self._widget = widget
        self._old_image = old_image.copy()
        self._new_image = new_image.copy()

    def undo(self):
        self._widget.set_image(self._old_image)

    def redo(self):
        self._widget.set_image(self._new_image)


class PixelImageWidget(QWidget):
    """A widget for editing a QImage at the pixel level."""

    color_picked = Signal(QColor)

    class Tool(IntEnum):
        PENCIL = auto()
        ERASER = auto()
        COLOR_PICKER = auto()

    def __init__(self, image: QImage, parent=None):
        super().__init__(parent)
        self._image = image.copy()
        self._zoom_factor = 16.0
        self._tool = self.Tool.PENCIL
        self._active_color = QColor(Qt.GlobalColor.black)
        self._show_grid = False
        self._is_drawing = False
        self._image_before_stroke = None
        self._pan_last_pos = None
        self._hover_pos = None  # QPoint in image coordinates

        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._update_widget_size()

    def get_image(self) -> QImage:
        return self._image

    def set_image(self, image: QImage):
        self._image = image.copy()
        self.update()

    def set_tool(self, tool: Tool):
        self._tool = tool
        self.update()

    def set_active_color(self, color: QColor):
        self._active_color = color

    def set_show_grid(self, show: bool):
        self._show_grid = show
        self.update()

    def zoom_in(self):
        self._zoom_factor = min(64.0, self._zoom_factor * 1.25)
        self._update_widget_size()

    def zoom_out(self):
        self._zoom_factor = max(1.0, self._zoom_factor / 1.25)
        self._update_widget_size()

    def zoom_reset(self):
        self._zoom_factor = 16.0
        self._update_widget_size()

    def _update_widget_size(self):
        self.resize(self.sizeHint())
        self.updateGeometry()
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(
            int(self._image.width() * self._zoom_factor),
            int(self._image.height() * self._zoom_factor),
        )

    def paintEvent(self, event):
        painter = QPainter(self)

        # 1. Draw Checkerboard Background
        self._draw_checkerboard(painter, self.rect())

        # 2. Draw Image
        painter.save()
        painter.scale(self._zoom_factor, self._zoom_factor)
        # Use FastTransformation to keep pixels sharp when scaling
        pixmap = QPixmap.fromImage(self._image)
        painter.drawPixmap(0, 0, pixmap)
        painter.restore()

        # 3. Draw Grid
        if self._show_grid:
            self._draw_grid(painter)

        # 4. Draw Hover Cursor
        if self._hover_pos is not None:
            self._draw_hover_cursor(painter)

        painter.end()

    def _draw_checkerboard(self, painter: QPainter, rect: QRect, size: int = 8):
        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        pm = QPixmap(size * 2, size * 2)
        p = QPainter(pm)
        c1 = QColor(240, 240, 240)
        c2 = QColor(200, 200, 200)
        p.fillRect(0, 0, size, size, c1)
        p.fillRect(size, size, size, size, c1)
        p.fillRect(size, 0, size, size, c2)
        p.fillRect(0, size, size, size, c2)
        p.end()
        brush = QBrush(pm)
        painter.setBrush(brush)
        painter.drawRect(rect)
        painter.restore()

    def _draw_grid(self, painter: QPainter):
        painter.save()
        pen = QPen(QColor(100, 100, 100, 80), 1)
        pen.setCosmetic(True)
        painter.setPen(pen)
        w = self._image.width()
        h = self._image.height()
        for x in range(w + 1):
            painter.drawLine(
                QPointF(x * self._zoom_factor, 0),
                QPointF(x * self._zoom_factor, h * self._zoom_factor),
            )
        for y in range(h + 1):
            painter.drawLine(
                QPointF(0, y * self._zoom_factor),
                QPointF(w * self._zoom_factor, y * self._zoom_factor),
            )
        painter.restore()

    def _draw_hover_cursor(self, painter: QPainter):
        painter.save()
        x = self._hover_pos.x() * self._zoom_factor
        y = self._hover_pos.y() * self._zoom_factor
        rect = QRectF(x, y, self._zoom_factor, self._zoom_factor)

        # Draw a thin black and white dashed rect around the hovered pixel
        pen = QPen(Qt.GlobalColor.black, 1)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.drawRect(rect)

        pen.setColor(Qt.GlobalColor.white)
        pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.drawRect(rect)
        painter.restore()

    def _apply_tool(self, pos: QPoint):
        x, y = pos.x(), pos.y()
        if x < 0 or x >= self._image.width() or y < 0 or y >= self._image.height():
            return

        if self._tool == self.Tool.PENCIL:
            self._image.setPixelColor(x, y, self._active_color)
        elif self._tool == self.Tool.ERASER:
            self._image.setPixelColor(x, y, QColor(Qt.GlobalColor.transparent))
        elif self._tool == self.Tool.COLOR_PICKER:
            color = self._image.pixelColor(x, y)
            self.color_picked.emit(color)
        self.update()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_last_pos = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

        # Right click acts as quick color picker!
        if event.button() == Qt.MouseButton.RightButton:
            pos = event.position()
            x = int(pos.x() / self._zoom_factor)
            y = int(pos.y() / self._zoom_factor)
            if 0 <= x < self._image.width() and 0 <= y < self._image.height():
                color = self._image.pixelColor(x, y)
                self.color_picked.emit(color)
                event.accept()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()
            self._is_drawing = True
            self._image_before_stroke = self._image.copy()
            pos = event.position()
            x = int(pos.x() / self._zoom_factor)
            y = int(pos.y() / self._zoom_factor)
            self._apply_tool(QPoint(x, y))

    def mouseMoveEvent(self, event: QMouseEvent):
        # Handle Panning
        if event.buttons() & Qt.MouseButton.MiddleButton and self._pan_last_pos is not None:
            scroll_area = self
            from PySide6.QtWidgets import QScrollArea

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

        pos = event.position()
        x = int(pos.x() / self._zoom_factor)
        y = int(pos.y() / self._zoom_factor)

        # Update hover position
        if 0 <= x < self._image.width() and 0 <= y < self._image.height():
            self._hover_pos = QPoint(x, y)
        else:
            self._hover_pos = None
        self.update()

        if self._is_drawing and event.buttons() & Qt.MouseButton.LeftButton:
            self._apply_tool(QPoint(x, y))
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_last_pos = None
            self.unsetCursor()
            event.accept()
            return

        if event.button() == Qt.MouseButton.LeftButton and self._is_drawing:
            self._is_drawing = False
            # Check if image changed, if so, push command to parent dialog's undo stack
            if self._image != self._image_before_stroke:
                dialog = self.window()
                if hasattr(dialog, "undo_stack"):
                    command = EditImageCommand(self, self._image_before_stroke, self._image)
                    dialog.undo_stack.push(command)
            self._image_before_stroke = None
            event.accept()

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            angle = event.angleDelta().y()
            if angle > 0:
                self.zoom_in()
            elif angle < 0:
                self.zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)


class PixelEditorDialog(QDialog):
    """A dialog for editing the pixel art of a layer."""

    def __init__(self, image: QImage, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Pixel Editor"))

        self._original_image = image
        self._undo_stack = QUndoStack(self)

        # Create Image Widget
        self._image_widget = PixelImageWidget(image, self)

        # Wrap ImageWidget in a QScrollArea to handle zooming
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidget(self._image_widget)
        self._scroll_area.setWidgetResizable(False)
        self._scroll_area.setBackgroundRole(QPalette.ColorRole.Dark)

        # Palette Panel
        palette_group = QGroupBox(self.tr("Color Palette"))
        palette_layout = QVBoxLayout()
        self._palette_list = QListWidget()
        self._palette_list.setIconSize(QSize(16, 16))
        self._palette_list.itemSelectionChanged.connect(self._on_palette_selection_changed)

        self._add_color_button = QPushButton(self.tr("Add Color..."))
        self._add_color_button.setIcon(
            create_icon_from_svg(":/icons/svg/actions/list-add-symbolic.svg", ICON_SIZE)
        )
        self._add_color_button.clicked.connect(self._on_add_color_clicked)

        palette_layout.addWidget(self._palette_list)
        palette_layout.addWidget(self._add_color_button)
        palette_group.setLayout(palette_layout)

        # Populate palette from image
        self._populate_palette()

        # Toolbar
        toolbar = QToolBar()
        self._mode_actions = {}

        # Tools
        tools = [
            (
                PixelImageWidget.Tool.PENCIL,
                self.tr("Pencil"),
                "draw-freehand-symbolic.svg",
                "P",
            ),
            (
                PixelImageWidget.Tool.ERASER,
                self.tr("Eraser"),
                "draw-eraser-symbolic.svg",
                "E",
            ),
            (
                PixelImageWidget.Tool.COLOR_PICKER,
                self.tr("Eyedropper"),
                "color-picker-symbolic.svg",
                "I",
            ),
        ]

        for tool_type, name, icon_name, shortcut in tools:
            path = f":/icons/svg/actions/{icon_name}"
            icon = create_icon_from_svg(path, ICON_SIZE)
            action = QAction(icon, name, self)
            action.setShortcut(QKeySequence(shortcut))
            action.setToolTip(f"{name} ({shortcut})")
            action.setCheckable(True)
            action.setData(tool_type)
            action.triggered.connect(self._on_tool_action_triggered)
            toolbar.addAction(action)
            self._mode_actions[tool_type] = action

        self._mode_actions[PixelImageWidget.Tool.PENCIL].setChecked(True)

        toolbar.addSeparator()

        # Zoom & Grid
        zoom_in_action = QAction(
            create_icon_from_svg(":/icons/svg/actions/zoom-in-symbolic.svg", ICON_SIZE),
            self.tr("Zoom In"),
            self,
        )
        zoom_in_action.setShortcut(QKeySequence.StandardKey.ZoomIn)
        zoom_in_action.triggered.connect(self._image_widget.zoom_in)
        toolbar.addAction(zoom_in_action)

        zoom_out_action = QAction(
            create_icon_from_svg(":/icons/svg/actions/zoom-out-symbolic.svg", ICON_SIZE),
            self.tr("Zoom Out"),
            self,
        )
        zoom_out_action.setShortcut(QKeySequence.StandardKey.ZoomOut)
        zoom_out_action.triggered.connect(self._image_widget.zoom_out)
        toolbar.addAction(zoom_out_action)

        show_grid_action = QAction(
            create_icon_from_svg(":/icons/svg/actions/show-grid-symbolic.svg", ICON_SIZE),
            self.tr("Show Grid"),
            self,
        )
        show_grid_action.setCheckable(True)
        show_grid_action.toggled.connect(self._image_widget.set_show_grid)
        toolbar.addAction(show_grid_action)

        toolbar.addSeparator()

        # Undo/Redo
        undo_action = self._undo_stack.createUndoAction(self, self.tr("Undo"))
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.setIcon(QIcon.fromTheme("edit-undo"))
        toolbar.addAction(undo_action)

        redo_action = self._undo_stack.createRedoAction(self, self.tr("Redo"))
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        redo_action.setIcon(QIcon.fromTheme("edit-redo"))
        toolbar.addAction(redo_action)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        # Layouts
        image_palette_layout = QHBoxLayout()
        image_palette_layout.addWidget(self._scroll_area, 1)
        image_palette_layout.addWidget(palette_group, 0)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 10)
        main_layout.addWidget(toolbar)
        main_layout.addLayout(image_palette_layout)
        main_layout.addWidget(button_box)
        self.setLayout(main_layout)

        # Connect image widget signals
        self._image_widget.color_picked.connect(self._on_color_picked)

        self._resize_dialog()

    @property
    def undo_stack(self) -> QUndoStack:
        return self._undo_stack

    def get_image(self) -> QImage:
        return self._image_widget.get_image()

    def _populate_palette(self):
        self._palette_list.clear()
        image = self._image_widget.get_image()
        unique_colors = self._get_unique_colors(image)

        for color in unique_colors:
            self._add_color_to_palette_widget(color)

        if self._palette_list.count() > 0:
            self._palette_list.setCurrentRow(0)

    def _get_unique_colors(self, image: QImage) -> list[QColor]:
        colors = set()
        for y in range(image.height()):
            for x in range(image.width()):
                color = image.pixelColor(x, y)
                if color.alpha() > 0:
                    colors.add(color.rgba())
        return [QColor.fromRgba(c) for c in sorted(colors)]

    def _add_color_to_palette_widget(self, color: QColor) -> QListWidgetItem:
        # Check if already exists
        for i in range(self._palette_list.count()):
            item = self._palette_list.item(i)
            item_color = item.data(Qt.UserRole)
            if item_color == color:
                return item

        # Create a small color icon
        pixmap = QPixmap(16, 16)
        pixmap.fill(color)
        icon = QIcon(pixmap)

        hex_name = color.name(QColor.NameFormat.HexRgb).upper()
        item = QListWidgetItem(icon, hex_name)
        item.setData(Qt.UserRole, color)
        self._palette_list.addItem(item)
        return item

    @Slot()
    def _on_palette_selection_changed(self):
        item = self._palette_list.currentItem()
        if item:
            color = item.data(Qt.UserRole)
            self._image_widget.set_active_color(color)
            # Switch back to Pencil tool when selecting a color
            self._mode_actions[PixelImageWidget.Tool.PENCIL].trigger()

    @Slot()
    def _on_add_color_clicked(self):
        color = QColorDialog.getColor(parent=self)
        if color.isValid():
            item = self._add_color_to_palette_widget(color)
            self._palette_list.setCurrentItem(item)

    @Slot(QColor)
    def _on_color_picked(self, color: QColor):
        if color.alpha() == 0:
            # Eyedropped a transparent pixel -> switch to Eraser tool!
            self._mode_actions[PixelImageWidget.Tool.ERASER].trigger()
        else:
            # Eyedropped a color -> add/select it, and switch to Pencil tool
            item = self._add_color_to_palette_widget(color)
            self._palette_list.setCurrentItem(item)
            self._mode_actions[PixelImageWidget.Tool.PENCIL].trigger()

    @Slot()
    def _on_tool_action_triggered(self):
        sender: QAction = self.sender()
        for action in self._mode_actions.values():
            action.setChecked(False)
        sender.setChecked(True)
        tool: PixelImageWidget.Tool = sender.data()
        self._image_widget.set_tool(tool)

    def accept(self):
        # Check if image was modified
        if self._image_widget.get_image() != self._original_image:
            ret = QMessageBox.warning(
                self,
                self.tr("Regenerate Partitions?"),
                self.tr(
                    "Modifying the image pixels will completely regenerate all partitions and "
                    "discard any custom stitch routing you have set for this layer.\n\n"
                    "Are you sure you want to proceed?"
                ),
                QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if ret == QMessageBox.StandardButton.Cancel:
                return

        super().accept()

    def reject(self):
        if not self._undo_stack.isClean():
            ret = QMessageBox.question(
                self,
                self.tr("Unsaved Changes"),
                self.tr("You have unsaved pixel edits. Are you sure you want to discard them?"),
                QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if ret == QMessageBox.StandardButton.Cancel:
                return

        super().reject()

    def _resize_dialog(self):
        screen_geometry = QGuiApplication.primaryScreen().availableGeometry()
        max_width = int(screen_geometry.width() * 0.9)
        max_height = int(screen_geometry.height() * 0.9)

        width = self._image_widget.sizeHint().width() + 180  # Image + Palette + margins
        height = self._image_widget.sizeHint().height() + 120  # Image + Toolbar + Buttons + margins

        width = min(width, max_width)
        height = min(height, max_height)

        # Set a sensible minimum size
        self.setMinimumSize(400, 300)
        self.resize(width, height)
