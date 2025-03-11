# Pixem
# Copyright 2024 Ricardo Quesada

import logging
import os.path
import sys

from PySide6.QtCore import QPointF, QSize, Qt
from PySide6.QtGui import QAction, QCloseEvent, QGuiApplication, QIcon, QKeySequence, QUndoStack
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QDockWidget,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QScrollArea,
    QSlider,
    QSpinBox,
    QStyle,
    QToolBar,
    QUndoView,
    QWidget,
)

import rc_resources  # noqa: F401
from about_dialog import AboutDialog
from canvas import Canvas
from export_dialog import ExportDialog
from font_dialog import FontDialog
from image_parser import ImageParser
from image_utils import create_icon_from_svg
from layer import ImageLayer, Layer, LayerAlign, LayerProperties, TextLayer
from partition_dialog import PartitionDialog
from preference_dialog import PreferenceDialog
from preferences import global_preferences
from state import State

logger = logging.getLogger(__name__)  # __name__ gets the current module's name

ICON_SIZE = 22


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self._state = None
        self._setup_ui()
        self._load_settings()

        self._cleanup_state()

        open_on_startup = global_preferences.get_open_file_on_startup()
        if open_on_startup:
            files = global_preferences.get_recent_files()
            if len(files) > 0:
                self._open_filename(files[0])

        self._update_window_title()

    def _setup_ui(self):
        menu_bar = self.menuBar()
        file_menu = QMenu("&File", self)
        menu_bar.addMenu(file_menu)

        self._new_action = QAction(QIcon.fromTheme("document-new"), "New Project", self)
        self._new_action.setShortcut(QKeySequence("Ctrl+N"))
        self._new_action.triggered.connect(self._on_new_project)
        file_menu.addAction(self._new_action)

        self._open_action = QAction(QIcon.fromTheme("document-open"), "Open Image or Project", self)
        self._open_action.setShortcut(QKeySequence("Ctrl+O"))
        self._open_action.triggered.connect(self._on_open_image_or_project)
        file_menu.addAction(self._open_action)

        self._recent_menu = QMenu("Recent Files", file_menu)
        file_menu.addMenu(self._recent_menu)
        self._populate_recent_menu()

        self._close_action = QAction(QIcon.fromTheme("window-close"), "Close Project", self)
        self._close_action.setShortcut(QKeySequence("Ctrl+W"))
        self._close_action.triggered.connect(self._on_close_project)
        file_menu.addAction(self._close_action)

        file_menu.addSeparator()

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

        self._export_action = QAction("Export Project", self)
        self._export_action.setShortcut(QKeySequence("Ctrl+E"))
        self._export_action.triggered.connect(self._on_export_project)
        file_menu.addAction(self._export_action)

        self._export_as_action = QAction("Export Project As...", self)
        self._export_as_action.setShortcut(QKeySequence("Ctrl+Shift+E"))
        self._export_as_action.triggered.connect(self._on_export_project_as)
        file_menu.addAction(self._export_as_action)

        file_menu.addSeparator()

        self._exit_action = QAction(QIcon.fromTheme("application-exit"), "Exit", self)
        self._exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        self._exit_action.triggered.connect(self._on_exit_application)
        file_menu.addAction(self._exit_action)

        edit_menu = QMenu("&Edit", self)
        menu_bar.addMenu(edit_menu)

        self._undo_action = QAction(QIcon.fromTheme("edit-undo"), "&Undo", self)
        self._undo_action.setShortcut("Ctrl+Z")
        edit_menu.addAction(self._undo_action)
        self._redo_action = QAction(QIcon.fromTheme("edit-redo"), "&Redo", self)
        self._redo_action.setShortcut("Ctrl+Shift+Z")
        edit_menu.addAction(self._redo_action)

        edit_menu.addSeparator()

        icon = create_icon_from_svg(":/res/icons/svg/actions/object-select-symbolic.svg")
        self._canvas_mode_move_action = QAction(icon, "Select Mode", self)
        self._canvas_mode_move_action.setCheckable(True)
        self._canvas_mode_move_action.setChecked(True)
        self._canvas_mode_move_action.triggered.connect(self._on_canvas_mode_move)
        edit_menu.addAction(self._canvas_mode_move_action)

        icon = create_icon_from_svg(":/res/icons/svg/actions/draw-freehand-symbolic.svg")
        self._canvas_mode_drawing_action = QAction(icon, "Drawing Mode", self)
        self._canvas_mode_drawing_action.setCheckable(True)
        self._canvas_mode_drawing_action.setChecked(False)
        self._canvas_mode_drawing_action.triggered.connect(self._on_canvas_mode_drawing)
        edit_menu.addAction(self._canvas_mode_drawing_action)
        # FIXME: Enable "Drawing" mode
        self._canvas_mode_drawing_action.setEnabled(False)

        edit_menu.addSeparator()

        self._preferences_action = QAction(
            QIcon.fromTheme("preferences-system"), "&Preferences", self
        )
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

        layer_menu.addSeparator()
        aligns = [
            (
                LayerAlign.HORIZONTAL_LEFT,
                "Align Horizontal Left",
                "align-horizontal-left-symbolic.svg",
            ),
            (
                LayerAlign.HORIZONTAL_CENTER,
                "Align Horizontal Center",
                "align-horizontal-center-symbolic.svg",
            ),
            (
                LayerAlign.HORIZONTAL_RIGHT,
                "Align Horizontal Right",
                "align-horizontal-right-symbolic.svg",
            ),
            (LayerAlign.VERTICAL_TOP, "Align Vertical Top", "align-vertical-top-symbolic.svg"),
            (
                LayerAlign.VERTICAL_CENTER,
                "Align Vertical Center",
                "align-vertical-center-symbolic.svg",
            ),
            (
                LayerAlign.VERTICAL_BOTTOM,
                "Align Vertical Bottom",
                "align-vertical-bottom-symbolic.svg",
            ),
        ]

        self._align_actions = {}

        for i, align in enumerate(aligns):
            path = f":/res/icons/svg/actions/{align[2]}"
            icon = create_icon_from_svg(path)
            action = QAction(icon, align[1], self)
            action.triggered.connect(self._on_layer_align)
            action.setData(align[0])
            self._align_actions[align[0]] = action
            layer_menu.addAction(action)
            if i == 2:
                layer_menu.addSeparator()

        partition_menu = QMenu("&Partition", self)
        menu_bar.addMenu(partition_menu)

        self._edit_partition_action = QAction("Edit Partition", self)
        self._edit_partition_action.setShortcut(QKeySequence("Ctrl+P"))
        self._edit_partition_action.triggered.connect(self._on_partition_edit)
        partition_menu.addAction(self._edit_partition_action)

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

        self._toolbar.addAction(self._canvas_mode_move_action)
        self._toolbar.addAction(self._canvas_mode_drawing_action)
        self._toolbar.addSeparator()

        # Add Align actions
        for i, key in enumerate(self._align_actions):
            action = self._align_actions[key]
            self._toolbar.addAction(action)
            if i == 2:
                self._toolbar.addSeparator()

        self._toolbar.addSeparator()

        self._toolbar.addAction(self._undo_action)
        self._toolbar.addAction(self._redo_action)
        self._toolbar.addSeparator()

        self._zoom_slider = QSlider(Qt.Horizontal)
        self._zoom_slider.setRange(1, 500)
        self._zoom_slider.setValue(100)
        self._zoom_slider.valueChanged.connect(self._on_zoom_changed)
        self._toolbar.addWidget(self._zoom_slider)

        # Layers Dock
        self._layer_list = QListWidget()
        self._layer_list.setDragDropMode(QListWidget.InternalMove)  # Enable reordering
        self._layer_list.model().rowsMoved.connect(self._on_layer_rows_moved)
        layer_dock = QDockWidget("Layers", self)
        layer_dock.setObjectName("layer_dock")
        layer_dock.setWidget(self._layer_list)
        self.addDockWidget(Qt.RightDockWidgetArea, layer_dock)

        # Partitions Dock
        self._partition_list = QListWidget()
        self._partition_list.setDragDropMode(QListWidget.InternalMove)  # Enable reordering
        self._partition_list.model().rowsMoved.connect(self._on_partition_rows_moved)
        partitions_dock = QDockWidget("Partitions", self)
        partitions_dock.setObjectName("partitions_dock")
        partitions_dock.setWidget(self._partition_list)
        self.addDockWidget(Qt.RightDockWidgetArea, partitions_dock)

        self._connect_layer_partition_callbacks()

        # Undo Dock
        self._undo_dock = QDockWidget("Undo List", self)
        self._undo_dock.setObjectName("undo_dock")
        self._undo_view = QUndoView()
        self._undo_dock.setWidget(self._undo_view)
        self.addDockWidget(Qt.RightDockWidgetArea, self._undo_dock)

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
        self._rotation_spinbox = QSpinBox()
        self._rotation_spinbox.setRange(0, 360)
        self._rotation_spinbox.setValue(0)
        hbox = QHBoxLayout()
        hbox.addWidget(self._rotation_spinbox)
        hbox.addWidget(self._rotation_slider)
        self._rotation_spinbox.valueChanged.connect(self._rotation_slider.setValue)
        self._property_layout.addRow("Rotation:", hbox)

        self._visible_checkbox = QCheckBox()
        self._property_layout.addRow("Visible:", self._visible_checkbox)
        self._opacity_slider = QSlider(Qt.Horizontal)
        self._opacity_slider.setRange(0, 100)
        self._opacity_slider.setValue(100)
        self._property_layout.addRow("Opacity:", self._opacity_slider)

        property_dock = QDockWidget("Layer Properties", self)
        property_dock.setObjectName("property_dock")
        property_dock.setWidget(self._property_editor)
        self.addDockWidget(Qt.RightDockWidgetArea, property_dock)

        self._connect_property_callbacks()
        self._update_qactions()

        # Insert all docks in Menu
        view_menu.insertActions(
            show_hoop_separator_action,
            [
                layer_dock.toggleViewAction(),
                partitions_dock.toggleViewAction(),
                property_dock.toggleViewAction(),
                self._undo_dock.toggleViewAction(),
            ],
        )

        self._canvas = Canvas(self._state)
        self._canvas.position_changed.connect(self._on_position_changed_from_canvas)
        self._canvas.layer_selection_changed.connect(self._on_layer_selection_changed_from_canvas)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self._canvas)

        self.setCentralWidget(scroll_area)

    def _populate_recent_menu(self):
        self._recent_menu.clear()
        recent_files = global_preferences.get_recent_files()
        for file_name in recent_files:
            action = QAction(os.path.basename(file_name), self)
            action.setData(file_name)
            action.triggered.connect(self._on_recent_file)
            self._recent_menu.addAction(action)

        self._recent_menu.addSeparator()
        action = QAction(QIcon.fromTheme("edit-clear"), "Clear Menu", self)
        action.triggered.connect(self._on_clear_recent_files)
        self._recent_menu.addAction(action)

        self._recent_menu.setEnabled(len(recent_files) > 0)

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

        self._edit_partition_action.setEnabled(enabled)

        self._zoom_slider.setEnabled(enabled)

        self._property_editor.setEnabled(enabled)

        for key in self._align_actions:
            action = self._align_actions[key]
            action.setEnabled(enabled)

        # short circuit
        self._undo_action.setEnabled(enabled and self._state.undo_stack.canUndo())
        self._redo_action.setEnabled(enabled and self._state.undo_stack.canRedo())

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

    def _connect_layer_partition_callbacks(self):
        self._layer_list.currentItemChanged.connect(self._on_change_layer)
        self._partition_list.currentItemChanged.connect(self._on_change_partition)
        self._partition_list.itemDoubleClicked.connect(self._on_double_click_partition)

    def _disconnect_layer_partition_callbacks(self):
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
        global_preferences.save_recent_files()

    def _update_window_title(self):
        title = "Pixem"
        if self._state is not None and self._state.project_filename is not None:
            title = f"{title} - {os.path.basename(self._state.project_filename)}"
        self.setWindowTitle(title)

    def _open_filename(self, filename: str) -> None:
        state = State.load_from_filename(filename)
        if state is None:
            logger.warning(f"Failed to load state from filename {filename}")
            return

        self._setup_state(state)

        self._disconnect_layer_partition_callbacks()
        self._layer_list.clear()
        self._partition_list.clear()
        self._connect_layer_partition_callbacks()

        selected_layer = self._state.selected_layer

        selected_layer_idx = -1
        selected_partition_idx = -1

        for i, layer in enumerate(self._state.layers):
            item = QListWidgetItem(layer.name)
            item.setData(Qt.UserRole, layer.uuid)
            self._layer_list.addItem(item)
            if selected_layer is not None and layer.uuid == selected_layer.uuid:
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

        self._update_window_title()
        global_preferences.add_recent_file(filename)
        self._populate_recent_menu()

    def _setup_state(self, state: State):
        self._state = state
        self._canvas.state = state
        self._state.layer_property_changed.connect(self._on_layer_property_changed_from_state)

        self._undo_action.triggered.connect(self._state.undo_stack.undo)
        self._redo_action.triggered.connect(self._state.undo_stack.redo)

        self._undo_view.setStack(self._state.undo_stack)
        self._undo_dock.setEnabled(True)

    def _cleanup_state(self):
        if self._state is not None:
            self._undo_action.triggered.disconnect(self._state.undo_stack.undo)
            self._redo_action.triggered.disconnect(self._state.undo_stack.redo)
        self._state = None
        self._canvas.state = None
        self._undo_view.setStack(QUndoStack())
        self._undo_dock.setEnabled(False)

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

    def _refresh_partitions(self):
        # Called from on_layer_changed
        self._disconnect_layer_partition_callbacks()
        self._partition_list.clear()
        self._connect_layer_partition_callbacks()

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

    #
    # pyside6 events
    #
    def closeEvent(self, event: QCloseEvent):
        if self._state and not self._state.undo_stack.isClean():
            reply = QMessageBox.question(
                self,
                "Warning",
                "Changes will be lost. Continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply == QMessageBox.No:
                event.ignore()
                return

        logger.info("Closing Pixem")
        self._save_settings()
        super().closeEvent(event)

    #
    # local events / callbacks
    #
    def _on_new_project(self) -> None:
        # FIXME: If an existing state is dirty, it should ask for "are you sure"
        state = State()
        self._setup_state(state)
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

        self._update_window_title()

    def _on_open_image_or_project(self) -> None:
        # FIXME: If an existing state is dirty, it should ask for "are you sure"
        options = QFileDialog.Options()  # For more options if needed
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open Pixem Project File",
            "",
            "All Supported Files (*.pixemproj *.png *.jpg *.bmp );;"
            "Pixem project (*.pixemproj);;"
            "All files (*)",
            options=options,
        )
        if filename:
            _, ext = os.path.splitext(filename)
            if ext == ".pixemproj":
                self._open_filename(filename)
            else:
                self._on_new_project()
                layer = ImageLayer(filename)
                layer.name = f"ImageLayer {len(self._state.layers) + 1}"
                self._add_layer(layer)
        else:
            logger.warning("Could not open file. Invalid filename")

    def _on_recent_file(self) -> None:
        filename = self.sender().data()
        self._open_filename(filename)

    def _on_clear_recent_files(self) -> None:
        global_preferences.clear_recent_files()
        self._populate_recent_menu()

    def _on_save_project(self) -> None:
        filename = self._state.project_filename
        if filename is None:
            self._on_save_project_as()
            return
        self._state.save_to_filename(filename)

    def _on_save_project_as(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Project", "", "Pixem files (*.pixemproj);;All files (*)"
        )
        if filename:
            _, ext = os.path.splitext(filename)
            if ext != ".pixemproj":
                filename = filename + ".pixemproj"
            self._state.save_to_filename(filename)
            self._update_window_title()
            global_preferences.add_recent_file(filename)
            self._populate_recent_menu()

    def _on_export_project(self) -> None:
        export_params = self._state.export_params
        if (
            export_params.filename is None
            or len(export_params.filename) == 0
            or not os.path.exists(export_params.filename)
        ):
            self._on_export_project_as()
            return

        self._state.export_to_filename(export_params)

    def _on_export_project_as(self) -> None:
        dialog = ExportDialog(self._state.export_params)
        if dialog.exec() == QDialog.Accepted:
            export_params = dialog.get_export_parameters()
            self._state.export_to_filename(export_params)

    def _on_close_project(self) -> None:
        if self._state and not self._state.undo_stack.isClean():
            reply = QMessageBox.question(
                self,
                "Warning",
                "Changes will be lost. Continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply == QMessageBox.No:
                return

        self._cleanup_state()

        self._disconnect_layer_partition_callbacks()
        self._layer_list.clear()
        self._partition_list.clear()
        self._connect_layer_partition_callbacks()

        # FIXME: update state should be done in one method
        self._update_qactions()
        self._canvas.recalculate_fixed_size()
        self.update()

        self._update_window_title()

    def _on_exit_application(self) -> None:
        QApplication.quit()

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

    def _on_layer_add_image(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Open Image", "", "Images (*.png *.jpg *.bmp);;All files (*)"
        )
        if file_name:
            layer = ImageLayer(file_name)
            layer.name = f"ImageLayer {len(self._state.layers) + 1}"
            self._add_layer(layer)

    def _on_layer_add_text(self) -> None:
        dialog = FontDialog()
        if dialog.exec() == QDialog.Accepted:
            text, font_name = dialog.get_data()
            layer = TextLayer(text, font_name)
            layer.name = f"TextLayer {len(self._state.layers) + 1}"
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

    def _on_layer_align(self):
        s = self.sender()
        if self._state is None or self._state.selected_layer is None:
            return
        x, y = self._state.selected_layer.calculate_pos_for_align(
            s.data(), global_preferences.get_hoop_size()
        )
        logger.info(f"align new values {x}, {y}")
        self._position_x_spinbox.setValue(x)
        self._position_y_spinbox.setValue(y)

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
            self._rotation_spinbox.setValue(round(layer.rotation))
            self._pixel_width_spinbox.setValue(layer.pixel_size.width())
            self._pixel_height_spinbox.setValue(layer.pixel_size.height())
            self._visible_checkbox.setChecked(layer.visible)
            self._opacity_slider.setValue(round(layer.opacity * 100))

            self._connect_property_callbacks()

            self._state.current_layer_uuid = layer.uuid

            self._refresh_partitions()
        else:
            if self._state is not None:
                self._state.current_layer_uuid = None

    def _on_layer_rows_moved(self, parent, start, end, destination):
        if self._state is None:
            logger.warning("Cannot reorder layers, no active state")
            return
        layers = self._state.layers
        new_layers = []
        for row in range(self._layer_list.count()):
            item = self._layer_list.item(row)
            layer_name = item.text()
            for layer in layers:
                if layer.name == layer_name:
                    new_layers.append(layer)
                    break
        self._state.layers = new_layers

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

        self._on_partition_edit()

    def _on_partition_edit(self):
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

    def _on_partition_rows_moved(self, parent, start, end, destination):
        if self._state is None or self._state.selected_layer is None:
            logger.warning("Cannot reorder partitions, no layer selected")
            return
        layer = self._state.selected_layer
        partitions = layer.partitions
        # reorder dict keys
        new_partitions = {}
        for row in range(self._partition_list.count()):
            item = self._partition_list.item(row)
            partition_key = item.text()
            new_partitions[partition_key] = partitions[partition_key]
        layer.partitions = new_partitions

    def _on_update_layer_property(self) -> None:
        current_layer = self._state.selected_layer
        enabled = current_layer is not None
        self._property_editor.setEnabled(enabled)
        if enabled:
            properties = LayerProperties(
                position=(self._position_x_spinbox.value(), self._position_y_spinbox.value()),
                rotation=self._rotation_slider.value(),
                pixel_size=(self._pixel_width_spinbox.value(), self._pixel_height_spinbox.value()),
                visible=self._visible_checkbox.isChecked(),
                opacity=self._opacity_slider.value() / 100.0,
                name=self._name_edit.text(),
            )
            self._state.set_layer_properties(current_layer, properties)

            self._canvas.recalculate_fixed_size()
            self.update()

    def _on_show_about_dialog(self) -> None:
        dialog = AboutDialog()
        dialog.exec()

    def _on_position_changed_from_canvas(self, position: QPointF):
        self._position_x_spinbox.setValue(position.x())
        self._position_y_spinbox.setValue(position.y())

    def _on_layer_selection_changed_from_canvas(self, layer: Layer):
        for i in range(self._layer_list.count()):
            item = self._layer_list.item(i)
            if item.text() == layer.name:
                self._layer_list.setCurrentRow(i)
                break

    def _on_layer_property_changed_from_state(self, layer: Layer):
        if self._state is None:
            logger.warning("Unexpected state. Should not be none")
            return
        if self._state.selected_layer != layer:
            logger.warning(
                f"Unexpected selected layer. Got '{layer.name}', expected: '{self._state.selected_layer.name}'"
            )
            return

        properties = layer.properties
        self._disconnect_property_callbacks()
        self._position_x_spinbox.setValue(properties.position[0])
        self._position_y_spinbox.setValue(properties.position[1])
        self._rotation_slider.setValue(round(properties.rotation))
        self._rotation_spinbox.setValue(round(properties.rotation))
        self._pixel_width_spinbox.setValue(properties.pixel_size[0])
        self._pixel_height_spinbox.setValue(properties.pixel_size[1])
        self._connect_property_callbacks()

        self._update_qactions()
        self._canvas.recalculate_fixed_size()
        self.update()

    def _on_canvas_mode_move(self):
        self._canvas_mode_move_action.setChecked(True)
        self._canvas_mode_drawing_action.setChecked(False)
        self._canvas.mode = Canvas.Mode.MOVE

    def _on_canvas_mode_drawing(self):
        self._canvas_mode_move_action.setChecked(False)
        self._canvas_mode_drawing_action.setChecked(True)
        self._canvas.mode = Canvas.Mode.DRAWING


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Pixem")
    app.setOrganizationName("Retro Moe")
    app.setOrganizationDomain("retro.moe")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
