# Pixem
# Copyright 2024 Ricardo Quesada

import copy
import logging
import sys

import resources_rc  # noqa: F401

from about_dialog import AboutDialog
from preference_dialog import PreferenceDialog
from preferences import global_preferences
from state import State
from layer import Layer, ImageLayer
from layer_parser import LayerParser

from PySide6.QtCore import (
    QCoreApplication,
    QFile,
    QIODevice,
    QPointF,
    QSize,
    QSizeF,
    Qt,
)

from PySide6.QtGui import (
    QAction,
    QCloseEvent,
    QGuiApplication,
    QIcon,
    QPaintEvent,
    QPainter,
    QPainterPath,
    QPen,
    QUndoStack,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QDialog,
    QDockWidget,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QSlider,
    QStyle,
    QToolBar,
    QUndoView,
    QWidget,
)

logger = logging.getLogger(__name__)  # __name__ gets the current module's name

DEFAULT_SCALE_FACTOR = 5.0
INCHES_TO_MM = 25.4


class Canvas(QWidget):
    def __init__(self, state: State) -> None:
        super().__init__()
        self.state: State = state

        self.cached_hoop_visible = global_preferences.get_hoop_visible()
        self.cached_hoop_size = global_preferences.get_hoop_size()

    def paintEvent(self, event: QPaintEvent) -> None:
        if not self.state.layers:
            return

        painter = QPainter(self)
        painter.scale(
            self.state.scale_factor * DEFAULT_SCALE_FACTOR,
            self.state.scale_factor * DEFAULT_SCALE_FACTOR,
        )

        for i, layer in enumerate(self.state.layers):
            if layer.visible:
                painter.save()
                painter.setOpacity(layer.opacity)
                # Scale the image based on pixel size
                scaled_x = layer.image.width() * layer.pixel_size.width()
                scaled_y = layer.image.height() * layer.pixel_size.height()
                transformed_image = layer.image.scaled(
                    round(scaled_x),
                    round(scaled_y),
                    Qt.IgnoreAspectRatio,
                    Qt.FastTransformation,
                )
                painter.translate(
                    scaled_x / 2 + layer.position.x(), scaled_y / 2 + layer.position.y()
                )
                painter.rotate(layer.rotation)
                painter.translate(
                    -(scaled_x / 2 + layer.position.x()),
                    -(scaled_y / 2 + layer.position.y()),
                )
                painter.drawImage(layer.position, transformed_image)
                painter.restore()

        # Draw hoop
        if self.cached_hoop_visible:
            painter.setPen(QPen(Qt.gray, 1, Qt.DashDotDotLine))
            path = QPainterPath()
            path.moveTo(0, 0)
            path.lineTo(0.0, 0.0)
            path.lineTo(0.0, self.cached_hoop_size[1] * INCHES_TO_MM)
            path.lineTo(
                self.cached_hoop_size[0] * INCHES_TO_MM, self.cached_hoop_size[1] * INCHES_TO_MM
            )
            path.lineTo(self.cached_hoop_size[0] * INCHES_TO_MM, 0.0)
            path.lineTo(0.0, 0.0)

            painter.drawPath(path)
        painter.end()

    def on_preferences_updated(self):
        """Updates the preference cache"""
        self.cached_hoop_visible = global_preferences.get_hoop_visible()
        self.cached_hoop_size = global_preferences.get_hoop_size()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.state = State()

        self.undo_stack = QUndoStack(self)

        menu_bar = self.menuBar()
        file_menu = QMenu("&File", self)
        menu_bar.addMenu(file_menu)

        open_action = QAction(QIcon.fromTheme("document-open"), "&Open Project", self)
        open_action.triggered.connect(self.open_project)
        file_menu.addAction(open_action)

        save_action = QAction(QIcon.fromTheme("document-save"), "Save Project", self)
        save_action.triggered.connect(self.save_project)
        file_menu.addAction(save_action)

        save_as_action = QAction(QIcon.fromTheme("document-save-as"), "Save Project As...", self)
        save_as_action.triggered.connect(self.save_project_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        export_action = QAction("Export Project", self)
        export_action.triggered.connect(self.export_project)
        file_menu.addAction(export_action)

        export_as_action = QAction("Export Project As...", self)
        export_as_action.triggered.connect(self.export_project_as)
        file_menu.addAction(export_as_action)

        edit_menu = QMenu("&Edit", self)
        menu_bar.addMenu(edit_menu)

        undo_action = QAction(QIcon.fromTheme("edit-undo"), "&Undo", self)
        undo_action.triggered.connect(self.undo_stack.undo)
        edit_menu.addAction(undo_action)

        redo_action = QAction(QIcon.fromTheme("edit-redo"), "&Redo", self)
        redo_action.triggered.connect(self.undo_stack.redo)
        edit_menu.addAction(redo_action)

        edit_menu.addSeparator()

        preferences_action = QAction("&Preferences", self)
        preferences_action.triggered.connect(self.preferences)
        edit_menu.addAction(preferences_action)

        view_menu = QMenu("&View", self)
        menu_bar.addMenu(view_menu)
        # The rest of the "View" actions are added once the docks are finished

        show_hoop_separator_action = view_menu.addSeparator()

        show_hoop_action = QAction("&Show hoop size", self)
        show_hoop_action.setCheckable(True)
        show_hoop_action.triggered.connect(lambda: self.show_hoop_size(show_hoop_action))
        view_menu.addAction(show_hoop_action)
        show_hoop_action.setChecked(global_preferences.get_hoop_visible())

        view_menu.addSeparator()

        reset_layout_action = QAction("&Reset Layout", self)
        reset_layout_action.triggered.connect(self.reset_layout)
        view_menu.addAction(reset_layout_action)

        layer_menu = QMenu("&Layer", self)
        menu_bar.addMenu(layer_menu)

        add_image_action = QAction(QIcon.fromTheme("insert-image"), "Add Image Layer", self)
        add_image_action.triggered.connect(self.layer_add_image)
        layer_menu.addAction(add_image_action)

        add_text_action = QAction(QIcon.fromTheme("insert-text"), "Add Text Layer", self)
        add_text_action.triggered.connect(self.layer_add_text)
        layer_menu.addAction(add_text_action)

        delete_layer_action = QAction(QIcon.fromTheme("edit-delete"), "Delete Layer", self)
        delete_layer_action.triggered.connect(self.layer_delete)
        layer_menu.addAction(delete_layer_action)

        layer_menu.addSeparator()

        analyze_layer_action = QAction("&Analyze Layer", self)
        analyze_layer_action.triggered.connect(self.layer_analyze)
        layer_menu.addAction(analyze_layer_action)

        help_menu = QMenu("&Help", self)
        menu_bar.addMenu(help_menu)

        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

        self.toolbar = QToolBar("Tools")
        self.toolbar.setObjectName("main_window_toolbar")
        self.toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(self.toolbar)

        self.toolbar.addAction(open_action)
        self.toolbar.addAction(save_action)
        self.toolbar.addSeparator()

        self.toolbar.addAction(add_image_action)
        self.toolbar.addAction(add_text_action)
        self.toolbar.addSeparator()

        self.toolbar.addAction(undo_action)
        self.toolbar.addAction(redo_action)
        self.toolbar.addSeparator()

        color_action = QAction("Pen Color", self)
        color_action.triggered.connect(self.choose_color)
        self.toolbar.addAction(color_action)

        zoom_slider = QSlider(Qt.Horizontal)
        zoom_slider.setRange(1, 500)
        zoom_slider.setValue(100)
        zoom_slider.valueChanged.connect(self.zoom)
        self.toolbar.addWidget(zoom_slider)

        # Layers Dock
        self.layer_list = QListWidget()
        self.layer_list.currentItemChanged.connect(self.change_layer)
        layer_dock = QDockWidget("Layers", self)
        layer_dock.setObjectName("layer_dock")
        layer_dock.setWidget(self.layer_list)
        self.addDockWidget(Qt.RightDockWidgetArea, layer_dock)

        # Undo Dock
        undo_view = QUndoView(self.undo_stack)
        undo_dock = QDockWidget("Undo List", self)
        undo_dock.setObjectName("undo_dock")
        undo_dock.setWidget(undo_view)
        self.addDockWidget(Qt.RightDockWidgetArea, undo_dock)

        # Property Dock
        self.property_editor = QWidget()
        self.property_layout = QFormLayout(self.property_editor)
        self.property_editor.setEnabled(False)
        self.name_edit = QLineEdit()
        self.property_layout.addRow("Name:", self.name_edit)

        self.position_x_spinbox = QDoubleSpinBox()
        self.position_x_spinbox.setRange(-1000.0, 1000.0)
        self.property_layout.addRow("Position X:", self.position_x_spinbox)
        self.position_y_spinbox = QDoubleSpinBox()
        self.position_y_spinbox.setRange(-1000.0, 1000.0)
        self.property_layout.addRow("Position Y:", self.position_y_spinbox)

        self.pixel_width_spinbox = QDoubleSpinBox()
        self.pixel_width_spinbox.setMinimum(1.0)
        self.property_layout.addRow("Pixel Width:", self.pixel_width_spinbox)
        self.pixel_height_spinbox = QDoubleSpinBox()
        self.pixel_height_spinbox.setMinimum(1.0)
        self.property_layout.addRow("Pixel Height:", self.pixel_height_spinbox)

        self.rotation_slider = QSlider(Qt.Horizontal)
        self.rotation_slider.setRange(0, 360)
        self.rotation_slider.setValue(0)
        self.property_layout.addRow("Rotation:", self.rotation_slider)

        self.visible_checkbox = QCheckBox()
        self.property_layout.addRow("Visible:", self.visible_checkbox)
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        self.property_layout.addRow("Opacity:", self.opacity_slider)

        property_dock = QDockWidget("Properties", self)
        property_dock.setObjectName("property_dock")
        property_dock.setWidget(self.property_editor)
        self.addDockWidget(Qt.RightDockWidgetArea, property_dock)

        self.name_edit.editingFinished.connect(self.update_layer_property)
        self.position_x_spinbox.valueChanged.connect(self.update_layer_property)
        self.position_y_spinbox.valueChanged.connect(self.update_layer_property)
        self.rotation_slider.valueChanged.connect(self.update_layer_property)
        self.pixel_width_spinbox.valueChanged.connect(self.update_layer_property)
        self.pixel_height_spinbox.valueChanged.connect(self.update_layer_property)
        self.visible_checkbox.stateChanged.connect(self.update_layer_property)
        self.opacity_slider.valueChanged.connect(self.update_layer_property)

        # Insert all docks in Menu
        view_menu.insertActions(
            show_hoop_separator_action,
            [
                layer_dock.toggleViewAction(),
                property_dock.toggleViewAction(),
                undo_dock.toggleViewAction(),
            ],
        )

        self.canvas = Canvas(self.state)
        self.setCentralWidget(self.canvas)

        self.load_settings()

        self.setWindowTitle("Pixem")

    def load_settings(self):
        # Save defaults before restoring saved settings
        # FIXME: Probably there is a more efficient way to do it.
        global_preferences.set_default_window_geometry(self.saveGeometry())
        global_preferences.set_default_window_state(
            self.saveState(global_preferences.STATE_VERSION)
        )

        geometry = global_preferences.get_window_geometry()
        if geometry is not None:
            self.restoreGeometry(geometry)
        state = global_preferences.get_window_state()
        if state is not None:
            self.restoreState(state)

    def save_settings(self):
        global_preferences.set_window_geometry(self.saveGeometry())
        global_preferences.set_window_state(self.saveState(global_preferences.STATE_VERSION))

    def closeEvent(self, event: QCloseEvent):
        self.save_settings()
        super().closeEvent(event)

    def mousePressEvent(self, event) -> None:
        pass

    def mouseMoveEvent(self, event) -> None:
        pass

    def open_project(self) -> None:
        options = QFileDialog.Options()  # For more options if needed
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open Pixem Project File",
            "",
            "Pixem Project Files (*.toml *.pixemproj);;All Files (*)",
            options=options,
        )
        if filename:
            state = State.load_from_filename(filename)
            if state is None:
                logger.warning(f"Failed to load state from filename {filename}")
                return

            # FIXME: Add a method that sets the new state
            self.state = state
            self.canvas.state = state

            self.layer_list.clear()
            for layer in self.state.layers:
                self.layer_list.addItem(layer.name)
            self.update()

    def save_project(self) -> None:
        filename = self.state.filename
        if filename is None:
            self.save_project_as()
            return
        self.state.save_to_filename(filename)

    def save_project_as(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Project", "", "pixem (*.pixemproj *.toml)"
        )
        if filename:
            self.state.save_to_filename(filename)

    def export_project(self) -> None:
        pass

    def export_project_as(self) -> None:
        pass

    def show_hoop_size(self, action: QAction) -> None:
        is_checked = action.isChecked()
        global_preferences.set_hoop_visible(is_checked)
        self.canvas.on_preferences_updated()
        self.update()

    def reset_layout(self) -> None:
        default_geometry = global_preferences.get_default_window_geometry()
        default_state = global_preferences.get_default_window_state()
        self.restoreGeometry(default_geometry)
        self.restoreState(default_state, global_preferences.STATE_VERSION)

        self.setGeometry(
            QStyle.alignedRect(
                Qt.LayoutDirection.LeftToRight,
                Qt.AlignmentFlag.AlignCenter,
                self.size(),
                QGuiApplication.primaryScreen().geometry(),
            )
        )

    def preferences(self) -> None:
        dialog = PreferenceDialog()
        if dialog.exec() == QDialog.Accepted:
            self.canvas.on_preferences_updated()
            self.update()

    def layer_add_image(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Open Image", "", "Image Files (*.png *.jpg *.bmp)"
        )
        if file_name:
            layer = ImageLayer(file_name, f"Layer {len(self.state.layers) + 1}")
            self.state.add_layer(layer)
            self.layer_list.addItem(layer.name)
            self.layer_list.setCurrentRow(self.state.current_layer_idx)
            self.update()

    def layer_add_text(self) -> None:
        file = QFile(":/res/fonts/petscii-charset.bin")
        if not file.open(QIODevice.OpenModeFlag.ReadOnly):
            print(f"Could not load file: {file.errorString()}")
            return
        data = file.readAll()
        print(data)

    def layer_delete(self) -> None:
        selected_items = self.layer_list.selectedItems()
        layer = self.state.get_selected_layer()

        if not selected_items or not layer:
            logger.warning("Cannot delete layer, no layers selected")
            return

        # Remove it from the widget
        for item in selected_items:
            row = self.layer_list.row(item)
            self.layer_list.takeItem(row)

        # Remove it from the state
        self.state.delete_layer(layer)

        self.update()

    def layer_analyze(self) -> None:
        layer: Layer = self.state.get_selected_layer()
        if layer is None:
            logger.warning("Cannot analyze layer. Invalid")
            return

        parser = LayerParser(layer)
        print(parser.conf)

    def choose_color(self) -> None:
        color = QColorDialog.getColor(self.state.pen_color, self)
        if color.isValid():
            self.state.pen_color = color

    def zoom(self, value: int) -> None:
        self.state.scale_factor = value / 100.0
        self.update()

    def change_layer(self, current: QListWidgetItem, previous: QListWidgetItem) -> None:
        enabled = current is not None
        self.property_editor.setEnabled(enabled)
        if enabled:
            self.state.current_layer_idx = self.layer_list.row(current)
            # Cache all variables first
            clone = copy.copy(self.state.layers[self.state.current_layer_idx])
            # And then update widgets.
            # This is updating the widgets will trigger the "value changed", that will
            # update the current layer based on the self.current.
            self.name_edit.setText(clone.name)
            self.position_x_spinbox.setValue(clone.position.x())
            self.position_y_spinbox.setValue(clone.position.y())
            self.rotation_slider.setValue(round(clone.rotation))
            self.pixel_width_spinbox.setValue(clone.pixel_size.width())
            self.pixel_height_spinbox.setValue(clone.pixel_size.height())
            self.visible_checkbox.setChecked(clone.visible)
            self.opacity_slider.setValue(round(clone.opacity * 100))
        else:
            self.state.current_layer_idx = -1

    def update_layer_property(self) -> None:
        enabled = self.state.current_layer_idx != -1
        self.property_editor.setEnabled(enabled)
        if enabled:
            current_layer = self.state.layers[self.state.current_layer_idx]
            current_layer.name = self.name_edit.text()
            current_layer.position = QPointF(
                self.position_x_spinbox.value(), self.position_y_spinbox.value()
            )
            current_layer.rotation = self.rotation_slider.value()
            current_layer.pixel_size = QSizeF(
                self.pixel_width_spinbox.value(), self.pixel_height_spinbox.value()
            )
            current_layer.visible = self.visible_checkbox.isChecked()
            current_layer.opacity = self.opacity_slider.value() / 100.0
            self.layer_list.currentItem().setText(current_layer.name)
            self.update()

    def show_about_dialog(self) -> None:
        dialog = AboutDialog()
        dialog.exec()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    QCoreApplication.setApplicationName("Pixem")
    QCoreApplication.setOrganizationName("Retro Moe")
    QCoreApplication.setOrganizationDomain("retro.moe")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
