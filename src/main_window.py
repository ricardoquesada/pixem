# Pixem
# Copyright 2024 Ricardo Quesada

import logging
import sys

from PySide6.QtCore import QCoreApplication, QPointF, QSize, QSizeF, Qt
from PySide6.QtGui import QAction, QCloseEvent, QGuiApplication, QIcon, QKeySequence, QUndoStack
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
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
    QScrollArea,
    QSlider,
    QStyle,
    QToolBar,
    QUndoView,
    QWidget,
)

import resources_rc  # noqa: F401
from about_dialog import AboutDialog
from canvas import Canvas
from export_dialog import ExportDialog
from font_dialog import FontDialog
from image_parser import ImageParser
from layer import ImageLayer, Layer, TextLayer
from partition_dialog import PartitionDialog
from preference_dialog import PreferenceDialog
from preferences import global_preferences
from state import State

logger = logging.getLogger(__name__)  # __name__ gets the current module's name


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self._state = None
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        menu_bar = self.menuBar()
        file_menu = QMenu("&File", self)
        menu_bar.addMenu(file_menu)

        self._new_action = QAction(QIcon.fromTheme("document-new"), "New Project", self)
        self._new_action.setShortcut(QKeySequence("Ctrl+N"))
        self._new_action.triggered.connect(self._on_new_project)
        file_menu.addAction(self._new_action)

        self._open_action = QAction(QIcon.fromTheme("document-open"), "Open Project", self)
        self._open_action.setShortcut(QKeySequence("Ctrl+O"))
        self._open_action.triggered.connect(self._on_open_project)
        file_menu.addAction(self._open_action)

        self._save_action = QAction(QIcon.fromTheme("document-save"), "Save Project", self)
        self._save_action.setShortcut(QKeySequence("Ctrl+S"))
        self._save_action.triggered.connect(self._on_save_project)
        file_menu.addAction(self._save_action)

        self._save_as_action = QAction(
            QIcon.fromTheme("document-save-as"), "Save Project As...", self
        )
        self._save_as_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        self._save_as_action.triggered.connect(self._on_save_project_as)
        file_menu.addAction(self._save_as_action)

        self._close_action = QAction(QIcon.fromTheme("document-save-as"), "Close Project", self)
        self._close_action.setShortcut(QKeySequence("Ctrl+W"))
        self._close_action.triggered.connect(self._on_close_project)
        file_menu.addAction(self._close_action)

        file_menu.addSeparator()

        self._export_action = QAction("Export Project", self)
        self._export_action.setShortcut(QKeySequence("Ctrl+E"))
        self._export_action.triggered.connect(self._on_export_project)
        file_menu.addAction(self._export_action)

        self._export_as_action = QAction("Export Project As...", self)
        self._export_as_action.setShortcut(QKeySequence("Ctrl+Shift+E"))
        self._export_as_action.triggered.connect(self._on_export_project_as)
        file_menu.addAction(self._export_as_action)

        edit_menu = QMenu("&Edit", self)
        menu_bar.addMenu(edit_menu)

        self._undo_stack = QUndoStack(self)
        self._undo_action = QAction(QIcon.fromTheme("edit-undo"), "&Undo", self)
        self._undo_action.triggered.connect(self._undo_stack.undo)
        edit_menu.addAction(self._undo_action)

        self._redo_action = QAction(QIcon.fromTheme("edit-redo"), "&Redo", self)
        self._redo_action.triggered.connect(self._undo_stack.redo)
        edit_menu.addAction(self._redo_action)

        edit_menu.addSeparator()

        self._preferences_action = QAction("&Preferences", self)
        self._preferences_action.triggered.connect(self._on_preferences)
        edit_menu.addAction(self._preferences_action)

        view_menu = QMenu("&View", self)
        menu_bar.addMenu(view_menu)
        # The rest of the "View" actions are added once the docks are finished

        show_hoop_separator_action = view_menu.addSeparator()

        self._show_hoop_action = QAction("&Show hoop size", self)
        self._show_hoop_action.setCheckable(True)
        self._show_hoop_action.triggered.connect(
            lambda: self._on_show_hoop_size(self._show_hoop_action)
        )
        view_menu.addAction(self._show_hoop_action)
        self._show_hoop_action.setChecked(global_preferences.get_hoop_visible())

        view_menu.addSeparator()

        self._reset_layout_action = QAction("Reset Layout", self)
        self._reset_layout_action.triggered.connect(self._on_reset_layout)
        view_menu.addAction(self._reset_layout_action)

        layer_menu = QMenu("&Layer", self)
        menu_bar.addMenu(layer_menu)

        self._add_image_action = QAction(QIcon.fromTheme("insert-image"), "Add Image Layer", self)
        self._add_image_action.setShortcut(QKeySequence("Ctrl+I"))
        self._add_image_action.triggered.connect(self._on_layer_add_image)
        layer_menu.addAction(self._add_image_action)

        self._add_text_action = QAction(QIcon.fromTheme("insert-text"), "Add Text Layer", self)
        self._add_text_action.setShortcut(QKeySequence("Ctrl+T"))
        self._add_text_action.triggered.connect(self._on_layer_add_text)
        layer_menu.addAction(self._add_text_action)

        self._delete_layer_action = QAction(QIcon.fromTheme("edit-delete"), "Delete Layer", self)
        self._delete_layer_action.triggered.connect(self._on_layer_delete)
        layer_menu.addAction(self._delete_layer_action)

        help_menu = QMenu("&Help", self)
        menu_bar.addMenu(help_menu)

        self.about_action = QAction("About", self)
        self.about_action.triggered.connect(self._on_show_about_dialog)
        help_menu.addAction(self.about_action)

        self._toolbar = QToolBar("Tools")
        self._toolbar.setObjectName("main_window_toolbar")
        self._toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(self._toolbar)

        self._toolbar.addAction(self._open_action)
        self._toolbar.addAction(self._save_action)
        self._toolbar.addSeparator()

        self._toolbar.addAction(self._add_image_action)
        self._toolbar.addAction(self._add_text_action)
        self._toolbar.addSeparator()

        self._toolbar.addAction(self._undo_action)
        self._toolbar.addAction(self._redo_action)
        self._toolbar.addSeparator()

        self._zoom_slider = QSlider(Qt.Horizontal)
        self._zoom_slider.setRange(1, 500)
        self._zoom_slider.setValue(100)
        self._zoom_slider.valueChanged.connect(self._on_zoom_changed)
        self._toolbar.addWidget(self._zoom_slider)

        self._update_qactions()

        # Layers Dock
        self._layer_list = QListWidget()
        layer_dock = QDockWidget("Layers", self)
        layer_dock.setObjectName("layer_dock")
        layer_dock.setWidget(self._layer_list)
        self.addDockWidget(Qt.RightDockWidgetArea, layer_dock)

        # Layer colors Dock
        self._partition_list = QListWidget()
        partitions_dock = QDockWidget("Partitions", self)
        partitions_dock.setObjectName("partitions_dock")
        partitions_dock.setWidget(self._partition_list)
        self.addDockWidget(Qt.RightDockWidgetArea, partitions_dock)

        self._connect_list_callbacks()

        # Undo Dock
        undo_view = QUndoView(self._undo_stack)
        undo_dock = QDockWidget("Undo List", self)
        undo_dock.setObjectName("undo_dock")
        undo_dock.setWidget(undo_view)
        self.addDockWidget(Qt.RightDockWidgetArea, undo_dock)

        # Property Dock
        self._property_editor = QWidget()
        self._property_layout = QFormLayout(self._property_editor)
        self._property_editor.setEnabled(False)
        self._name_edit = QLineEdit()
        self._property_layout.addRow("Name:", self._name_edit)

        self._position_x_spinbox = QDoubleSpinBox()
        self._position_x_spinbox.setRange(-1000.0, 1000.0)
        self._property_layout.addRow("Position X:", self._position_x_spinbox)
        self._position_y_spinbox = QDoubleSpinBox()
        self._position_y_spinbox.setRange(-1000.0, 1000.0)
        self._property_layout.addRow("Position Y:", self._position_y_spinbox)

        self._pixel_width_spinbox = QDoubleSpinBox()
        self._pixel_width_spinbox.setMinimum(1.0)
        self._property_layout.addRow("Pixel Width:", self._pixel_width_spinbox)
        self._pixel_height_spinbox = QDoubleSpinBox()
        self._pixel_height_spinbox.setMinimum(1.0)
        self._property_layout.addRow("Pixel Height:", self._pixel_height_spinbox)

        self._rotation_slider = QSlider(Qt.Horizontal)
        self._rotation_slider.setRange(0, 360)
        self._rotation_slider.setValue(0)
        self._property_layout.addRow("Rotation:", self._rotation_slider)

        self._visible_checkbox = QCheckBox()
        self._property_layout.addRow("Visible:", self._visible_checkbox)
        self._opacity_slider = QSlider(Qt.Horizontal)
        self._opacity_slider.setRange(0, 100)
        self._opacity_slider.setValue(100)
        self._property_layout.addRow("Opacity:", self._opacity_slider)

        property_dock = QDockWidget("Properties", self)
        property_dock.setObjectName("property_dock")
        property_dock.setWidget(self._property_editor)
        self.addDockWidget(Qt.RightDockWidgetArea, property_dock)

        self._connect_property_callbacks()

        # Insert all docks in Menu
        view_menu.insertActions(
            show_hoop_separator_action,
            [
                layer_dock.toggleViewAction(),
                partitions_dock.toggleViewAction(),
                property_dock.toggleViewAction(),
                undo_dock.toggleViewAction(),
            ],
        )

        self._canvas = Canvas(self._state)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self._canvas)

        self.setCentralWidget(scroll_area)

        self.setWindowTitle("Pixem")

    def _update_qactions(self):
        enabled = self._state is not None

        self._save_action.setEnabled(enabled)
        self._save_as_action.setEnabled(enabled)
        self._close_action.setEnabled(enabled)
        self._export_action.setEnabled(enabled)
        self._export_as_action.setEnabled(enabled)

        self._add_text_action.setEnabled(enabled)
        self._add_image_action.setEnabled(enabled)
        self._delete_layer_action.setEnabled(enabled)

        self._zoom_slider.setEnabled(enabled)

    def _connect_property_callbacks(self):
        self._name_edit.editingFinished.connect(self._on_update_layer_property)
        self._position_x_spinbox.valueChanged.connect(self._on_update_layer_property)
        self._position_y_spinbox.valueChanged.connect(self._on_update_layer_property)
        self._rotation_slider.valueChanged.connect(self._on_update_layer_property)
        self._pixel_width_spinbox.valueChanged.connect(self._on_update_layer_property)
        self._pixel_height_spinbox.valueChanged.connect(self._on_update_layer_property)
        self._visible_checkbox.stateChanged.connect(self._on_update_layer_property)
        self._opacity_slider.valueChanged.connect(self._on_update_layer_property)
        self._zoom_slider.valueChanged.connect(self._on_zoom_changed)

    def _disconnect_property_callbacks(self):
        self._name_edit.editingFinished.disconnect(self._on_update_layer_property)
        self._position_x_spinbox.valueChanged.disconnect(self._on_update_layer_property)
        self._position_y_spinbox.valueChanged.disconnect(self._on_update_layer_property)
        self._rotation_slider.valueChanged.disconnect(self._on_update_layer_property)
        self._pixel_width_spinbox.valueChanged.disconnect(self._on_update_layer_property)
        self._pixel_height_spinbox.valueChanged.disconnect(self._on_update_layer_property)
        self._visible_checkbox.stateChanged.disconnect(self._on_update_layer_property)
        self._opacity_slider.valueChanged.disconnect(self._on_update_layer_property)
        self._zoom_slider.valueChanged.disconnect(self._on_zoom_changed)

    def _connect_list_callbacks(self):
        self._layer_list.currentItemChanged.connect(self._on_change_layer)
        self._partition_list.currentItemChanged.connect(self._on_change_partition)
        self._partition_list.itemDoubleClicked.connect(self._on_double_click_partition)

    def _disconnect_list_callbacks(self):
        self._layer_list.currentItemChanged.disconnect(self._on_change_layer)
        self._partition_list.currentItemChanged.disconnect(self._on_change_partition)
        self._partition_list.itemDoubleClicked.disconnect(self._on_double_click_partition)

    def _load_settings(self):
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

    def _save_settings(self):
        global_preferences.set_window_geometry(self.saveGeometry())
        global_preferences.set_window_state(self.saveState(global_preferences.STATE_VERSION))

    def closeEvent(self, event: QCloseEvent):
        logger.info("Closing Pixem")
        self._save_settings()
        super().closeEvent(event)

    def _on_new_project(self) -> None:
        # FIXME: If an existing state is dirty, it should ask for "are you suse"
        self._state = State()
        self._canvas.state = self._state
        # Triggers on_change_layer / on_change_partition, but not an issue
        self._layer_list.clear()
        self._partition_list.clear()

        self._disconnect_property_callbacks()
        self._zoom_slider.setValue(self._state.zoom_factor * 100)
        self._connect_property_callbacks()

        # FIXME: update state should be done in one method
        self._update_qactions()
        self._canvas.recalculate_fixed_size()
        self.update()

    def _on_open_project(self) -> None:
        # FIXME: If an existing state is dirty, it should ask for "are you suse"
        options = QFileDialog.Options()  # For more options if needed
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open Pixem Project File",
            "",
            "Pixem files (*.toml *.pixemproj);;All files (*)",
            options=options,
        )
        if filename:
            state = State.load_from_filename(filename)
            if state is None:
                logger.warning(f"Failed to load state from filename {filename}")
                return

            # FIXME: Add a method that sets the new state
            self._state = state
            self._canvas.state = state

            self._disconnect_list_callbacks()
            self._layer_list.clear()
            self._partition_list.clear()
            self._connect_list_callbacks()

            selected_layer = self._state.selected_layer

            selected_layer_idx = -1
            selected_partition_idx = -1

            for i, layer in enumerate(self._state.layers):
                self._layer_list.addItem(layer.name)
                if selected_layer is not None and layer.name == selected_layer.name:
                    selected_layer_idx = i

            if selected_layer is not None:
                selected_partition_key = selected_layer.current_partition_key
                for i, partition in enumerate(selected_layer.partitions):
                    self._partition_list.addItem(partition)
                    if partition == selected_partition_key:
                        selected_partition_idx = i

            # This will trigger "on_" callback
            if selected_layer_idx >= 0:
                self._layer_list.setCurrentRow(selected_layer_idx)
            if selected_partition_idx >= 0:
                self._partition_list.setCurrentRow(selected_partition_idx)

            self._disconnect_property_callbacks()
            self._zoom_slider.setValue(self._state.zoom_factor * 100)
            self._connect_property_callbacks()

            # FIXME: update state should be done in one method
            self._update_qactions()
            self._canvas.recalculate_fixed_size()
            self.update()

    def _on_save_project(self) -> None:
        filename = self._state.project_filename
        if filename is None:
            self._on_save_project_as()
            return
        self._state.save_to_filename(filename)

    def _on_save_project_as(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Project", "", "Pixem files (*.pixemproj *.toml);;All files (*)"
        )
        if filename:
            self._state.save_to_filename(filename)

    def _on_close_project(self) -> None:
        # FIXME: If an existing state is dirty, it should ask for "are you suse"
        self._state = None
        self._canvas.state = self._state
        self._layer_list.clear()
        self._partition_list.clear()

        # FIXME: update state should be done in one method
        self._update_qactions()
        self._canvas.recalculate_fixed_size()
        self.update()

    def _on_export_project(self) -> None:
        export_filename = self._state.export_filename
        if export_filename is None or len(export_filename) == 0:
            self._on_export_project_as()
            return
        self._state.export_to_filename(export_filename)

    def _on_export_project_as(self) -> None:
        dialog = ExportDialog()
        if dialog.exec() == QDialog.Accepted:
            export_filename = dialog.get_file_name()
            pull_compensation_mm = dialog.get_pull_compensation()
            self._state.export_to_filename(export_filename, pull_compensation_mm)

    def _on_show_hoop_size(self, action: QAction) -> None:
        is_checked = action.isChecked()
        global_preferences.set_hoop_visible(is_checked)
        self._canvas.on_preferences_updated()
        self._canvas.update()
        self.update()

    def _on_reset_layout(self) -> None:
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

    def _on_preferences(self) -> None:
        dialog = PreferenceDialog()
        if dialog.exec() == QDialog.Accepted:
            self._canvas.on_preferences_updated()
            self._canvas.update()
            self.update()

    def _add_layer(self, layer: Layer):
        self._state.add_layer(layer)
        self._layer_list.addItem(layer.name)
        self._layer_list.setCurrentRow(len(self._state.layers) - 1)

        parser = ImageParser(layer.image)
        layer.partitions = parser.partitions
        for partition_name in layer.partitions:
            self._partition_list.addItem(partition_name)
        if len(layer.partitions) > 0:
            self._partition_list.setCurrentRow(0)

        self._canvas.recalculate_fixed_size()
        self.update()

    def _on_layer_add_image(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Open Image", "", "Images (*.png *.jpg *.bmp);;All files (*)"
        )
        if file_name:
            layer = ImageLayer(file_name, f"ImageLayer {len(self._state.layers) + 1}")
            self._add_layer(layer)

    def _on_layer_add_text(self) -> None:
        dialog = FontDialog()
        if dialog.exec() == QDialog.Accepted:
            text, font_name = dialog.get_data()
            layer = TextLayer(font_name, text, f"TextLayer {len(self._state.layers) + 1}")
            self._add_layer(layer)

    def _on_layer_delete(self) -> None:
        selected_items = self._layer_list.selectedItems()
        layer = self._state.selected_layer

        if not selected_items or not layer:
            logger.warning("Cannot delete layer, no layers selected")
            return

        # Clear the "partitions"
        self._partition_list.clear()

        # Remove it from the widget
        for item in selected_items:
            row = self._layer_list.row(item)
            self._layer_list.takeItem(row)

        # Remove it from the state
        self._state.delete_layer(layer)

        # _partition_list should get auto-populated
        # because a "on_change_layer" should be triggered

        self._canvas.recalculate_fixed_size()
        self.update()

    def _on_zoom_changed(self, value: int) -> None:
        self._state.zoom_factor = value / 100.0
        self._canvas.recalculate_fixed_size()
        self._canvas.update()
        self.update()

    def _on_change_layer(self, current: QListWidgetItem, previous: QListWidgetItem) -> None:
        enabled = current is not None
        self._property_editor.setEnabled(enabled)
        if enabled:
            idx = self._layer_list.row(current)
            layer = self._state.layers[idx]

            self._disconnect_property_callbacks()

            self._name_edit.setText(layer.name)
            self._position_x_spinbox.setValue(layer.position.x())
            self._position_y_spinbox.setValue(layer.position.y())
            self._rotation_slider.setValue(round(layer.rotation))
            self._pixel_width_spinbox.setValue(layer.pixel_size.width())
            self._pixel_height_spinbox.setValue(layer.pixel_size.height())
            self._visible_checkbox.setChecked(layer.visible)
            self._opacity_slider.setValue(round(layer.opacity * 100))

            self._connect_property_callbacks()

            self._state.current_layer_key = layer.name

            self._refresh_partitions()
        else:
            if self._state is not None:
                self._state.current_layer_key = None

    def _on_change_partition(self, current: QListWidgetItem, previous: QListWidgetItem) -> None:
        enabled = current is not None
        selected_layer = self._state.selected_layer
        new_key = None
        if enabled:
            idx = self._partition_list.row(current)
            new_key = self._partition_list.item(idx).text()

        if selected_layer is not None:
            selected_layer.current_partition_key = new_key

        self._canvas.update()
        self.update()

    def _on_double_click_partition(self, current: QListWidgetItem) -> None:
        if current is None:
            return

        layer = self._state.selected_layer
        if layer is None:
            return

        partition = layer.selected_partition
        if partition is None:
            return

        dialog = PartitionDialog(layer.image, partition)
        if dialog.exec():
            path = dialog.get_path()
            partition.path = path
        else:
            print("Dialog canceled")

    def _on_update_layer_property(self) -> None:
        current_layer = self._state.selected_layer
        enabled = current_layer is not None
        self._property_editor.setEnabled(enabled)
        if enabled:
            current_layer.name = self._name_edit.text()
            current_layer.position = QPointF(
                self._position_x_spinbox.value(), self._position_y_spinbox.value()
            )
            current_layer.rotation = self._rotation_slider.value()
            current_layer.pixel_size = QSizeF(
                self._pixel_width_spinbox.value(), self._pixel_height_spinbox.value()
            )
            current_layer.visible = self._visible_checkbox.isChecked()
            current_layer.opacity = self._opacity_slider.value() / 100.0

            self._layer_list.currentItem().setText(current_layer.name)

            self._canvas.recalculate_fixed_size()
            self.update()

    def _on_show_about_dialog(self) -> None:
        dialog = AboutDialog()
        dialog.exec()

    def _refresh_partitions(self):
        # Called from on_layer_changed

        self._disconnect_list_callbacks()
        self._partition_list.clear()
        self._connect_list_callbacks()

        if self._state is None or self._state.selected_layer is None:
            return

        layer = self._state.selected_layer

        selected_partition_idx = -1
        # First: add all items
        for i, partition in enumerate(layer.partitions):
            self._partition_list.addItem(partition)
            if layer.current_partition_key == partition:
                selected_partition_idx = i

        # Second: select the correct one if present
        if selected_partition_idx >= 0:
            self._partition_list.setCurrentRow(selected_partition_idx)

        if len(layer.partitions) == 0:
            # Sanity check
            layer.current_partition_key = None
            logger.info("Failed to select partition, perhaps layer has not been analyzed yet")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    QCoreApplication.setApplicationName("Pixem")
    QCoreApplication.setOrganizationName("Retro Moe")
    QCoreApplication.setOrganizationDomain("retro.moe")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
