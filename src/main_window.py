# Pixem
# Copyright 2024 Ricardo Quesada

import logging
import os.path
import sys

from PySide6.QtCore import QPointF, QSize, Qt, Slot
from PySide6.QtGui import QAction, QCloseEvent, QGuiApplication, QIcon, QKeySequence, QUndoStack
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
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

from about_dialog import AboutDialog
from canvas import Canvas
from export_dialog import ExportDialog
from font_dialog import FontDialog
from image_parser import ImageParser
from image_utils import create_icon_from_svg
from layer import EmbroideryParameters, ImageLayer, Layer, LayerAlign, LayerProperties, TextLayer
from partition_dialog import PartitionDialog
from preference_dialog import PreferenceDialog
from preferences import get_global_preferences
from state import State
from state_properties import StateProperties, StatePropertyFlags

logger = logging.getLogger(__name__)  # __name__ gets the current module's name

ICON_SIZE = 22

# FIXME: Move to a better place
# Matches "100%", which is the default zoom factor in a new state
DEFAULT_ZOOM_FACTOR_IDX = 3


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self._state = None
        self._setup_ui()
        self._load_settings()

        self._cleanup_state()

        open_on_startup = get_global_preferences().get_open_file_on_startup()
        if open_on_startup:
            files = get_global_preferences().get_recent_files()
            if len(files) > 0:
                self._open_filename(files[0])

        self._update_window_title()

    def _setup_ui(self):
        menu_bar = self.menuBar()
        file_menu = QMenu(self.tr("&File"), self)
        menu_bar.addMenu(file_menu)

        self._new_action = QAction(QIcon.fromTheme("document-new"), self.tr("New Project"), self)
        self._new_action.setShortcut(QKeySequence("Ctrl+N"))
        self._new_action.triggered.connect(self._on_new_project)
        file_menu.addAction(self._new_action)

        self._open_action = QAction(
            QIcon.fromTheme("document-open"), self.tr("Open Image or Project"), self
        )
        self._open_action.setShortcut(QKeySequence("Ctrl+O"))
        self._open_action.triggered.connect(self._on_open_image_or_project)
        file_menu.addAction(self._open_action)

        self._recent_menu = QMenu(self.tr("Recent Files"), file_menu)
        file_menu.addMenu(self._recent_menu)
        self._populate_recent_menu()

        self._close_action = QAction(
            QIcon.fromTheme("window-close"), self.tr("Close Project"), self
        )
        self._close_action.setShortcut(QKeySequence("Ctrl+W"))
        self._close_action.triggered.connect(self._on_close_project)
        file_menu.addAction(self._close_action)

        file_menu.addSeparator()

        self._save_action = QAction(QIcon.fromTheme("document-save"), self.tr("Save Project"), self)
        self._save_action.setShortcut(QKeySequence("Ctrl+S"))
        self._save_action.triggered.connect(self._on_save_project)
        file_menu.addAction(self._save_action)

        self._save_as_action = QAction(
            QIcon.fromTheme("document-save-as"), self.tr("Save Project As..."), self
        )
        self._save_as_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        self._save_as_action.triggered.connect(self._on_save_project_as)
        file_menu.addAction(self._save_as_action)

        self._export_action = QAction(self.tr("Export Project"), self)
        self._export_action.setShortcut(QKeySequence("Ctrl+E"))
        self._export_action.triggered.connect(self._on_export_project)
        file_menu.addAction(self._export_action)

        self._export_as_action = QAction(self.tr("Export Project As..."), self)
        self._export_as_action.setShortcut(QKeySequence("Ctrl+Shift+E"))
        self._export_as_action.triggered.connect(self._on_export_project_as)
        file_menu.addAction(self._export_as_action)

        file_menu.addSeparator()

        self._exit_action = QAction(QIcon.fromTheme("application-exit"), self.tr("Exit"), self)
        self._exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        self._exit_action.triggered.connect(self._on_exit_application)
        file_menu.addAction(self._exit_action)

        edit_menu = QMenu(self.tr("&Edit"), self)
        menu_bar.addMenu(edit_menu)

        self._undo_action = QAction(QIcon.fromTheme("edit-undo"), self.tr("&Undo"), self)
        self._undo_action.setShortcut("Ctrl+Z")
        self._undo_action.setEnabled(False)
        edit_menu.addAction(self._undo_action)
        self._redo_action = QAction(QIcon.fromTheme("edit-redo"), self.tr("&Redo"), self)
        self._redo_action.setShortcut("Ctrl+Shift+Z")
        self._redo_action.setEnabled(False)
        edit_menu.addAction(self._redo_action)

        edit_menu.addSeparator()

        icon = create_icon_from_svg(":/icons/svg/actions/object-select-symbolic.svg")
        self._canvas_mode_move_action = QAction(icon, self.tr("Select Mode"), self)
        self._canvas_mode_move_action.setCheckable(True)
        self._canvas_mode_move_action.setChecked(True)
        self._canvas_mode_move_action.triggered.connect(self._on_canvas_mode_move)
        edit_menu.addAction(self._canvas_mode_move_action)

        icon = create_icon_from_svg(":/icons/svg/actions/draw-freehand-symbolic.svg")
        self._canvas_mode_drawing_action = QAction(icon, self.tr("Drawing Mode"), self)
        self._canvas_mode_drawing_action.setCheckable(True)
        self._canvas_mode_drawing_action.setChecked(False)
        self._canvas_mode_drawing_action.triggered.connect(self._on_canvas_mode_drawing)
        edit_menu.addAction(self._canvas_mode_drawing_action)
        # FIXME: Enable "Drawing" mode
        self._canvas_mode_drawing_action.setEnabled(False)

        edit_menu.addSeparator()

        self._preferences_action = QAction(
            QIcon.fromTheme("preferences-system"), self.tr("&Preferences"), self
        )
        self._preferences_action.triggered.connect(self._on_preferences)
        edit_menu.addAction(self._preferences_action)

        view_menu = QMenu("&View", self)
        menu_bar.addMenu(view_menu)
        # The rest of the "View" actions are added once the docks are finished

        show_hoop_separator_action = view_menu.addSeparator()

        self._show_hoop_action = QAction(self.tr("&Show hoop size"), self)
        self._show_hoop_action.setCheckable(True)
        self._show_hoop_action.triggered.connect(
            lambda: self._on_show_hoop_size(self._show_hoop_action)
        )
        view_menu.addAction(self._show_hoop_action)
        self._show_hoop_action.setChecked(get_global_preferences().get_hoop_visible())

        view_menu.addSeparator()

        self._reset_layout_action = QAction(self.tr("Reset Layout"), self)
        self._reset_layout_action.triggered.connect(self._on_reset_layout)
        view_menu.addAction(self._reset_layout_action)

        layer_menu = QMenu(self.tr("&Layer"), self)
        menu_bar.addMenu(layer_menu)

        self._add_image_action = QAction(
            QIcon.fromTheme("insert-image"), self.tr("Add Image Layer"), self
        )
        self._add_image_action.setShortcut(QKeySequence("Ctrl+I"))
        self._add_image_action.triggered.connect(self._on_layer_add_image)
        layer_menu.addAction(self._add_image_action)

        self._add_text_action = QAction(
            QIcon.fromTheme("insert-text"), self.tr("Add Text Layer"), self
        )
        self._add_text_action.setShortcut(QKeySequence("Ctrl+T"))
        self._add_text_action.triggered.connect(self._on_layer_add_text)
        layer_menu.addAction(self._add_text_action)

        self._delete_layer_action = QAction(
            QIcon.fromTheme("edit-delete"), self.tr("Delete Layer"), self
        )
        self._delete_layer_action.triggered.connect(self._on_layer_delete)
        layer_menu.addAction(self._delete_layer_action)

        layer_menu.addSeparator()
        aligns = [
            (
                LayerAlign.HORIZONTAL_LEFT,
                self.tr("Align Horizontal Left"),
                "align-horizontal-left-symbolic.svg",
            ),
            (
                LayerAlign.HORIZONTAL_CENTER,
                self.tr("Align Horizontal Center"),
                "align-horizontal-center-symbolic.svg",
            ),
            (
                LayerAlign.HORIZONTAL_RIGHT,
                self.tr("Align Horizontal Right"),
                "align-horizontal-right-symbolic.svg",
            ),
            (LayerAlign.VERTICAL_TOP, "Align Vertical Top", "align-vertical-top-symbolic.svg"),
            (
                LayerAlign.VERTICAL_CENTER,
                self.tr("Align Vertical Center"),
                "align-vertical-center-symbolic.svg",
            ),
            (
                LayerAlign.VERTICAL_BOTTOM,
                self.tr("Align Vertical Bottom"),
                "align-vertical-bottom-symbolic.svg",
            ),
        ]

        self._align_actions = {}

        for i, align in enumerate(aligns):
            path = f":/icons/svg/actions/{align[2]}"
            icon = create_icon_from_svg(path)
            action = QAction(icon, align[1], self)
            action.triggered.connect(self._on_layer_align)
            action.setData(align[0])
            self._align_actions[align[0]] = action
            layer_menu.addAction(action)
            if i == 2:
                layer_menu.addSeparator()

        partition_menu = QMenu(self.tr("&Partition"), self)
        menu_bar.addMenu(partition_menu)

        self._edit_partition_action = QAction(self.tr("Edit Partition"), self)
        self._edit_partition_action.setShortcut(QKeySequence("Ctrl+P"))
        self._edit_partition_action.triggered.connect(self._on_partition_edit)
        partition_menu.addAction(self._edit_partition_action)

        help_menu = QMenu(self.tr("&Help"), self)
        menu_bar.addMenu(help_menu)

        self.about_action = QAction(self.tr("About"), self)
        self.about_action.triggered.connect(self._on_show_about_dialog)
        help_menu.addAction(self.about_action)

        self._toolbar = QToolBar(self.tr("Tools"))
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
        for i, action in enumerate(self._align_actions.values()):
            self._toolbar.addAction(action)
            if i == 2:
                self._toolbar.addSeparator()

        self._toolbar.addSeparator()

        self._toolbar.addAction(self._undo_action)
        self._toolbar.addAction(self._redo_action)
        self._toolbar.addSeparator()

        # Zoom Widget
        self._zoom_values = ["25%", "50%", "75%", "100%", "150%", "200%"]
        self._zoom_factors = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0]
        self._zoom_combobox = QComboBox()
        self._zoom_combobox.addItems(self._zoom_values)
        self._zoom_combobox.setCurrentIndex(DEFAULT_ZOOM_FACTOR_IDX)
        self._zoom_combobox.currentIndexChanged.connect(self._on_zoom_changed)
        self._toolbar.addWidget(self._zoom_combobox)

        # Layers Dock
        self._layer_list = QListWidget()
        self._layer_list.setDragDropMode(QListWidget.InternalMove)  # Enable reordering
        self._layer_list.model().rowsMoved.connect(self._on_layer_rows_moved)
        layer_dock = QDockWidget(self.tr("Layers"), self)
        layer_dock.setObjectName("layer_dock")
        layer_dock.setWidget(self._layer_list)
        self.addDockWidget(Qt.RightDockWidgetArea, layer_dock)

        # Partitions Dock
        self._partition_list = QListWidget()
        self._partition_list.setDragDropMode(QListWidget.InternalMove)  # Enable reordering
        self._partition_list.model().rowsMoved.connect(self._on_partition_rows_moved)
        partitions_dock = QDockWidget(self.tr("Partitions"), self)
        partitions_dock.setObjectName("partitions_dock")
        partitions_dock.setWidget(self._partition_list)
        self.addDockWidget(Qt.RightDockWidgetArea, partitions_dock)

        self._connect_layer_and_partition_callbacks()

        # Property Dock
        self._property_editor = QWidget()
        self._property_editor.setObjectName("property_widget")
        self._property_editor.setEnabled(False)
        self._property_layout = QFormLayout(self._property_editor)
        self._name_edit = QLineEdit()
        self._property_layout.addRow(self.tr("Name:"), self._name_edit)

        self._position_x_spinbox = QDoubleSpinBox()
        self._position_x_spinbox.setRange(-1000.0, 1000.0)
        self._property_layout.addRow(self.tr("Position X:"), self._position_x_spinbox)
        self._position_y_spinbox = QDoubleSpinBox()
        self._position_y_spinbox.setRange(-1000.0, 1000.0)
        self._property_layout.addRow(self.tr("Position Y:"), self._position_y_spinbox)

        self._pixel_width_spinbox = QDoubleSpinBox()
        self._pixel_width_spinbox.setMinimum(1.0)
        self._property_layout.addRow(self.tr("Pixel Width:"), self._pixel_width_spinbox)
        self._pixel_height_spinbox = QDoubleSpinBox()
        self._pixel_height_spinbox.setMinimum(1.0)
        self._property_layout.addRow(self.tr("Pixel Height:"), self._pixel_height_spinbox)

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
        self._property_layout.addRow(self.tr("Rotation:"), hbox)

        self._visible_checkbox = QCheckBox()
        self._property_layout.addRow(self.tr("Visible:"), self._visible_checkbox)
        self._opacity_slider = QSlider(Qt.Horizontal)
        self._opacity_slider.setRange(0, 100)
        self._opacity_slider.setValue(100)
        self._property_layout.addRow(self.tr("Opacity:"), self._opacity_slider)

        property_dock = QDockWidget(self.tr("Layer Properties"), self)
        property_dock.setObjectName("property_dock")
        property_dock.setWidget(self._property_editor)
        self.addDockWidget(Qt.RightDockWidgetArea, property_dock)

        # Layer Embroidery Properties
        self._embroidery_params_editor = QWidget()
        self._embroidery_params_editor.setObjectName("embroidery_params_editor")
        self._embroidery_params_editor.setEnabled(False)
        self._embroidery_params_layout = QFormLayout(self._embroidery_params_editor)

        self._pull_compensation_spinbox = QDoubleSpinBox()
        self._pull_compensation_spinbox.setMinimum(0.0)
        self._pull_compensation_spinbox.setMaximum(1000.0)
        self._embroidery_params_layout.addRow(
            self.tr("Pull Compensation (mm):"), self._pull_compensation_spinbox
        )

        self._max_stitch_length_spinbox = QDoubleSpinBox()
        self._max_stitch_length_spinbox.setMinimum(0.0)
        self._max_stitch_length_spinbox.setMaximum(2000.0)
        self._embroidery_params_layout.addRow(
            self.tr("Max Stitch Length (mm):"), self._max_stitch_length_spinbox
        )

        self._min_jump_stitch_length_spinbox = QDoubleSpinBox()
        self._min_jump_stitch_length_spinbox.setMinimum(0.0)
        self._min_jump_stitch_length_spinbox.setMaximum(2000.0)
        self._embroidery_params_layout.addRow(
            self.tr("Min Jump Stitch Length (mm):"), self._min_jump_stitch_length_spinbox
        )

        self._initial_angle_spinbox = QSpinBox()
        self._initial_angle_spinbox.setMinimum(0)
        self._initial_angle_spinbox.setMaximum(360)
        self._embroidery_params_layout.addRow(
            self.tr("Initial Angle (degrees):"), self._initial_angle_spinbox
        )

        self._fill_method_combo = QComboBox()
        fill_items = {
            "auto_fill": self.tr("Auto Fill"),
            "legacy_fill": self.tr("Legacy Fill"),
        }
        for k, v in fill_items.items():
            self._fill_method_combo.addItem(v, k)
        self._embroidery_params_layout.addRow(self.tr("Fill Method:"), self._fill_method_combo)

        embroidery_params_dock = QDockWidget(self.tr("Layer Embroidery Properties"), self)
        embroidery_params_dock.setObjectName("layer_embroidery_dock")
        embroidery_params_dock.setWidget(self._embroidery_params_editor)
        self.addDockWidget(Qt.RightDockWidgetArea, embroidery_params_dock)

        # Undo Dock
        self._undo_dock = QDockWidget(self.tr("Undo List"), self)
        self._undo_dock.setObjectName("undo_dock")
        self._undo_dock.setHidden(True)
        self._undo_dock.setFloating(True)
        self._undo_view = QUndoView()
        self._undo_view.setObjectName("undo_view")
        self._undo_dock.setWidget(self._undo_view)
        self.addDockWidget(Qt.RightDockWidgetArea, self._undo_dock)

        self._connect_property_callbacks()
        self._connect_embroidery_callbacks()
        self._update_qactions()

        # Insert all docks in Menu
        view_menu.insertActions(
            show_hoop_separator_action,
            [
                layer_dock.toggleViewAction(),
                partitions_dock.toggleViewAction(),
                property_dock.toggleViewAction(),
                embroidery_params_dock.toggleViewAction(),
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
        recent_files = get_global_preferences().get_recent_files()
        for file_name in recent_files:
            action = QAction(os.path.basename(file_name), self)
            action.setData(file_name)
            action.triggered.connect(self._on_recent_file)
            self._recent_menu.addAction(action)

        self._recent_menu.addSeparator()
        action = QAction(QIcon.fromTheme("edit-clear"), self.tr("Clear Menu"), self)
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

        self._zoom_combobox.setEnabled(enabled)

        self._property_editor.setEnabled(enabled)

        for action in self._align_actions.values():
            action.setEnabled(enabled)

    def _connect_property_callbacks(self):
        self._name_edit.editingFinished.connect(self._on_update_layer_property)
        self._position_x_spinbox.valueChanged.connect(self._on_update_layer_property)
        self._position_y_spinbox.valueChanged.connect(self._on_update_layer_property)
        self._rotation_slider.valueChanged.connect(self._on_update_layer_property)
        self._pixel_width_spinbox.valueChanged.connect(self._on_update_layer_property)
        self._pixel_height_spinbox.valueChanged.connect(self._on_update_layer_property)
        self._visible_checkbox.stateChanged.connect(self._on_update_layer_property)
        self._opacity_slider.valueChanged.connect(self._on_update_layer_property)
        self._zoom_combobox.currentIndexChanged.connect(self._on_zoom_changed)

    def _disconnect_property_callbacks(self):
        self._name_edit.editingFinished.disconnect(self._on_update_layer_property)
        self._position_x_spinbox.valueChanged.disconnect(self._on_update_layer_property)
        self._position_y_spinbox.valueChanged.disconnect(self._on_update_layer_property)
        self._rotation_slider.valueChanged.disconnect(self._on_update_layer_property)
        self._pixel_width_spinbox.valueChanged.disconnect(self._on_update_layer_property)
        self._pixel_height_spinbox.valueChanged.disconnect(self._on_update_layer_property)
        self._visible_checkbox.stateChanged.disconnect(self._on_update_layer_property)
        self._opacity_slider.valueChanged.disconnect(self._on_update_layer_property)
        self._zoom_combobox.currentIndexChanged.disconnect(self._on_zoom_changed)

    def _connect_embroidery_callbacks(self):
        self._pull_compensation_spinbox.valueChanged.connect(self._on_update_embroidery_property)
        self._max_stitch_length_spinbox.valueChanged.connect(self._on_update_embroidery_property)
        self._min_jump_stitch_length_spinbox.valueChanged.connect(
            self._on_update_embroidery_property
        )
        self._initial_angle_spinbox.valueChanged.connect(self._on_update_embroidery_property)
        self._fill_method_combo.currentIndexChanged.connect(self._on_update_embroidery_property)

    def _disconnect_embroidery_callbacks(self):
        self._pull_compensation_spinbox.valueChanged.disconnect(self._on_update_embroidery_property)
        self._max_stitch_length_spinbox.valueChanged.disconnect(self._on_update_embroidery_property)
        self._min_jump_stitch_length_spinbox.valueChanged.disconnect(
            self._on_update_embroidery_property
        )
        self._initial_angle_spinbox.valueChanged.disconnect(self._on_update_embroidery_property)
        self._fill_method_combo.currentIndexChanged.disconnect(self._on_update_embroidery_property)

    def _connect_layer_and_partition_callbacks(self):
        self._layer_list.currentItemChanged.connect(self._on_change_layer)
        self._partition_list.currentItemChanged.connect(self._on_change_partition)
        self._partition_list.itemDoubleClicked.connect(self._on_double_click_partition)

    def _disconnect_layer_and_partition_callbacks(self):
        self._layer_list.currentItemChanged.disconnect(self._on_change_layer)
        self._partition_list.currentItemChanged.disconnect(self._on_change_partition)
        self._partition_list.itemDoubleClicked.disconnect(self._on_double_click_partition)

    def _load_settings(self):
        # Save defaults before restoring saved settings
        # FIXME: Probably there is a more efficient way to do it.
        # get_global_preferences().set_default_window_geometry(self.saveGeometry())
        # get_global_preferences().set_default_window_state(
        #     self.saveState(get_global_preferences().STATE_VERSION)
        # )

        prefs = get_global_preferences()
        geometry = prefs.get_window_geometry()
        if geometry is not None:
            self.restoreGeometry(geometry)
        state = prefs.get_window_state()
        if state is not None:
            self.restoreState(state)

    def _save_settings(self):
        prefs = get_global_preferences()
        prefs.set_window_geometry(self.saveGeometry())
        prefs.set_window_state(self.saveState(prefs.STATE_VERSION))
        prefs.save_recent_files()

    def _update_window_title(self):
        title = "Pixem"
        if self._state is not None:
            if self._state.project_filename is not None:
                title = f"{os.path.basename(self._state.project_filename)} - {title}"
            else:
                title = f"(untitled) - {title}"
        self.setWindowTitle(title)

    def _open_filename(self, filename: str) -> None:
        state = State.load_from_filename(filename)
        if state is None:
            logger.warning(f"Failed to load state from filename {filename}")
            return

        self._setup_state(state)

        selected_layer_idx = -1
        selected_partition_idx = -1
        selected_layer = self._state.selected_layer

        self._disconnect_layer_and_partition_callbacks()
        self._layer_list.clear()
        self._partition_list.clear()

        for i, layer in enumerate(self._state.layers):
            item = QListWidgetItem(layer.name)
            item.setData(Qt.UserRole, layer.uuid)
            self._layer_list.addItem(item)
            if selected_layer is not None and layer.uuid == selected_layer.uuid:
                selected_layer_idx = i

        if selected_layer is not None:
            selected_partition_uuid = selected_layer.current_partition_uuid
            for i, partition_key in enumerate(selected_layer.partitions):
                partition = selected_layer.partitions[partition_key]
                item = QListWidgetItem(partition.name)
                item.setData(Qt.UserRole, partition_key)
                self._partition_list.addItem(item)
                if partition_key == selected_partition_uuid:
                    selected_partition_idx = i

        self._connect_layer_and_partition_callbacks()

        # This will trigger "on_" callback
        if selected_layer_idx >= 0:
            self._layer_list.setCurrentRow(selected_layer_idx)
        if selected_partition_idx >= 0:
            self._partition_list.setCurrentRow(selected_partition_idx)

        self._disconnect_property_callbacks()
        index = 3  # Default: 100%
        for i, zoom_factor in enumerate(self._zoom_factors):
            if abs(self._state.zoom_factor - zoom_factor) <= 0.01:
                index = i
                break

        self._zoom_combobox.setCurrentIndex(index)
        self._connect_property_callbacks()

        # FIXME: update state should be done in one method
        self._update_qactions()
        self._canvas.recalculate_fixed_size()
        self.update()

        self._update_window_title()
        get_global_preferences().add_recent_file(filename)
        self._populate_recent_menu()

    def _setup_state(self, state: State):
        self._state = state
        self._canvas.state = state
        self._state.layer_property_changed.connect(self._on_layer_property_changed_from_state)
        self._state.state_property_changed.connect(self._on_state_property_changed_from_state)

        self._undo_action.triggered.connect(self._state.undo_stack.undo)
        self._redo_action.triggered.connect(self._state.undo_stack.redo)
        self._state.undo_stack.indexChanged.connect(self._on_undo_stack_index_changed)

        self._undo_view.setStack(self._state.undo_stack)
        self._undo_dock.setEnabled(True)

    def _cleanup_state(self):
        if self._state is not None:
            self._state.layer_property_changed.disconnect(
                self._on_layer_property_changed_from_state
            )
            self._state.state_property_changed.disconnect(
                self._on_state_property_changed_from_state
            )
            self._undo_action.triggered.disconnect(self._state.undo_stack.undo)
            self._redo_action.triggered.disconnect(self._state.undo_stack.redo)
            self._state.undo_stack.indexChanged.disconnect(self._on_undo_stack_index_changed)
        self._undo_action.setEnabled(False)
        self._redo_action.setEnabled(False)

        self._state = None
        self._canvas.state = None
        self._undo_view.setStack(QUndoStack())
        self._undo_dock.setEnabled(False)

    def _add_layer(self, layer: Layer):
        # Order matters. First create partitions, then add it
        parser = ImageParser(layer.image)
        layer.partitions = parser.partitions

        self._state.add_layer(layer)
        item = QListWidgetItem(layer.name)
        item.setData(Qt.UserRole, layer.uuid)

        self._disconnect_layer_and_partition_callbacks()
        self._layer_list.addItem(item)
        for partition_key, partition in layer.partitions.items():
            item = QListWidgetItem(partition.name)
            item.setData(Qt.UserRole, partition_key)
            self._partition_list.addItem(item)
        self._connect_layer_and_partition_callbacks()

        # Order matters: first layer, then partition
        # Triggers on_change_layer
        self._layer_list.setCurrentRow(len(self._state.layers) - 1)
        # Triggers on_change_partition
        if len(layer.partitions) > 0:
            self._partition_list.setCurrentRow(0)

        self._canvas.recalculate_fixed_size()
        self.update()

    def _populate_partitions(self, layer: Layer):
        # Called from on_change_layer
        self._disconnect_layer_and_partition_callbacks()
        self._partition_list.clear()
        self._connect_layer_and_partition_callbacks()

        if len(layer.partitions) == 0:
            # Sanity check
            layer.current_partition_uuid = None
            logger.warning(
                f"Failed to select partition, perhaps layer {layer.uuid} has not been analyzed yet"
            )
            return

        selected_partition_idx = -1
        # First: add all items
        for i, (partition_key, partition) in enumerate(layer.partitions.items()):
            item = QListWidgetItem(partition.name)
            item.setData(Qt.UserRole, partition_key)
            self._partition_list.addItem(item)
            if layer.current_partition_uuid == partition_key:
                selected_partition_idx = i

        # Second: select the correct one if present
        if selected_partition_idx >= 0:
            self._partition_list.setCurrentRow(selected_partition_idx)

    def _populate_property_editor(self, properties: LayerProperties) -> None:
        self._disconnect_property_callbacks()
        self._name_edit.setText(properties.name)
        self._position_x_spinbox.setValue(properties.position[0])
        self._position_y_spinbox.setValue(properties.position[1])
        self._rotation_slider.setValue(round(properties.rotation))
        self._rotation_spinbox.setValue(round(properties.rotation))
        self._pixel_width_spinbox.setValue(properties.pixel_size[0])
        self._pixel_height_spinbox.setValue(properties.pixel_size[1])
        self._visible_checkbox.setChecked(properties.visible)
        self._opacity_slider.setValue(round(properties.opacity * 100))
        self._connect_property_callbacks()

    def _populate_embroidery_editor(self, embroidery_params: EmbroideryParameters):
        self._disconnect_embroidery_callbacks()
        self._pull_compensation_spinbox.setValue(embroidery_params.pull_compensation_mm)
        self._max_stitch_length_spinbox.setValue(embroidery_params.max_stitch_length_mm)
        self._min_jump_stitch_length_spinbox.setValue(embroidery_params.min_jump_stitch_length_mm)
        self._initial_angle_spinbox.setValue(embroidery_params.initial_angle_degrees)
        index = self._fill_method_combo.findData(embroidery_params.fill_method)
        if index != -1:
            self._fill_method_combo.setCurrentIndex(index)
        self._connect_embroidery_callbacks()

    #
    # pyside6 events
    #
    def closeEvent(self, event: QCloseEvent):
        if self._state and not self._state.undo_stack.isClean():
            reply = QMessageBox.question(
                self,
                self.tr("Warning"),
                self.tr("Changes will be lost. Continue?"),
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
    # Slots (callbacks, events):
    #
    @Slot()
    def _on_new_project(self) -> None:
        # FIXME: If an existing state is dirty, it should ask for "are you sure"
        state = State()
        self._setup_state(state)
        # Triggers on_change_layer / on_change_partition, but not an issue
        self._layer_list.clear()
        self._partition_list.clear()

        self._disconnect_property_callbacks()
        self._zoom_combobox.setCurrentIndex(DEFAULT_ZOOM_FACTOR_IDX)
        self._connect_property_callbacks()
        self._connect_embroidery_callbacks()

        # FIXME: update state should be done in one method
        self._update_qactions()
        self._canvas.recalculate_fixed_size()
        self.update()

        self._update_window_title()

    @Slot()
    def _on_open_image_or_project(self) -> None:
        # FIXME: If an existing state is dirty, it should ask for "are you sure"
        options = QFileDialog.Options()  # For more options if needed
        filename, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Open Pixem Project File"),
            "",
            self.tr(
                "All Supported Files (*.pixemproj *.png *.jpg *.bmp );;Pixem project (*.pixemproj);;All files (*)"
            ),
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

    @Slot()
    def _on_recent_file(self) -> None:
        filename = self.sender().data()
        self._open_filename(filename)

    @Slot()
    def _on_clear_recent_files(self) -> None:
        get_global_preferences().clear_recent_files()
        self._populate_recent_menu()

    @Slot()
    def _on_save_project(self) -> None:
        filename = self._state.project_filename
        if filename is None:
            self._on_save_project_as()
            return
        self._state.save_to_filename(filename)

    @Slot()
    def _on_save_project_as(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self, self.tr("Save Project"), "", self.tr("Pixem files (*.pixemproj);;All files (*)")
        )
        if filename:
            _, ext = os.path.splitext(filename)
            if ext != ".pixemproj":
                filename = filename + ".pixemproj"
            self._state.save_to_filename(filename)
            self._update_window_title()
            get_global_preferences().add_recent_file(filename)
            self._populate_recent_menu()

    @Slot()
    def _on_export_project(self) -> None:
        filename = self._state.properties.export_filename
        if filename is None or len(filename) == 0 or not os.path.exists(filename):
            self._on_export_project_as()
            return

        self._state.export_to_filename(filename)

    @Slot()
    def _on_export_project_as(self) -> None:
        dialog = ExportDialog(self._state.properties.export_filename)
        if dialog.exec() == QDialog.Accepted:
            filename = dialog.get_filename()
            self._state.export_to_filename(filename)

    @Slot()
    def _on_close_project(self) -> None:
        if self._state and not self._state.undo_stack.isClean():
            reply = QMessageBox.question(
                self,
                self.tr("Warning"),
                self.tr("Changes will be lost. Continue?"),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply == QMessageBox.No:
                return

        self._cleanup_state()

        self._disconnect_layer_and_partition_callbacks()
        self._layer_list.clear()
        self._partition_list.clear()
        self._connect_layer_and_partition_callbacks()

        # FIXME: update state should be done in one method
        self._update_qactions()
        self._canvas.recalculate_fixed_size()
        self.update()

        self._update_window_title()

    @Slot()
    def _on_exit_application(self) -> None:
        QApplication.quit()

    @Slot()
    def _on_show_hoop_size(self, action: QAction) -> None:
        is_checked = action.isChecked()
        get_global_preferences().set_hoop_visible(is_checked)
        self._canvas.on_preferences_updated()
        self._canvas.update()
        self.update()

    @Slot()
    def _on_reset_layout(self) -> None:
        prefs = get_global_preferences()
        default_geometry = prefs.get_default_window_geometry()
        default_state = prefs.get_default_window_state()
        self.restoreGeometry(default_geometry)
        self.restoreState(default_state, prefs.STATE_VERSION)

        self.setGeometry(
            QStyle.alignedRect(
                Qt.LayoutDirection.LeftToRight,
                Qt.AlignmentFlag.AlignCenter,
                self.size(),
                QGuiApplication.primaryScreen().geometry(),
            )
        )

    @Slot()
    def _on_preferences(self) -> None:
        hoop_size = get_global_preferences().get_hoop_size()
        if self._state is not None:
            hoop_size = self._state.hoop_size
        dialog = PreferenceDialog(hoop_size)
        if dialog.exec() == QDialog.Accepted:
            if self._state:
                self._state.hoop_size = get_global_preferences().get_hoop_size()

    @Slot()
    def _on_layer_add_image(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self, self.tr("Open Image"), "", self.tr("Images (*.png *.jpg *.bmp);;All files (*)")
        )
        if file_name:
            layer = ImageLayer(file_name)
            layer.name = f"ImageLayer {len(self._state.layers) + 1}"
            self._add_layer(layer)

    @Slot()
    def _on_layer_add_text(self) -> None:
        dialog = FontDialog()
        if dialog.exec() == QDialog.Accepted:
            text, font_name = dialog.get_data()
            layer = TextLayer(text, font_name)
            layer.name = f"TextLayer {len(self._state.layers) + 1}"
            self._add_layer(layer)

    @Slot()
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

    @Slot()
    def _on_layer_align(self):
        s = self.sender()
        if self._state is None or self._state.selected_layer is None:
            return
        x, y = self._state.selected_layer.calculate_pos_for_align(s.data(), self._state.hoop_size)
        self._position_x_spinbox.setValue(x)
        self._position_y_spinbox.setValue(y)

    @Slot()
    def _on_zoom_changed(self, index: int) -> None:
        self._state.zoom_factor = self._zoom_factors[index]

    @Slot()
    def _on_change_layer(self, current: QListWidgetItem, previous: QListWidgetItem) -> None:
        enabled = current is not None
        self._property_editor.setEnabled(enabled)
        self._embroidery_params_editor.setEnabled(enabled)
        if enabled:
            idx = self._layer_list.row(current)
            layer = self._state.layers[idx]

            self._state.current_layer_uuid = layer.uuid

            self._populate_partitions(layer)
            self._populate_property_editor(layer.properties)
            self._populate_embroidery_editor(layer.embroidery_params)
        else:
            if self._state is not None:
                self._state.current_layer_uuid = None

    @Slot()
    def _on_layer_rows_moved(self, parent, start, end, destination):
        if self._state is None:
            logger.warning("Cannot reorder layers, no active state")
            return
        layers = self._state.layers
        new_layers = []
        for row in range(self._layer_list.count()):
            item = self._layer_list.item(row)
            layer_uuid = item.data(Qt.UserRole)
            for layer in layers:
                if layer.uuid == layer_uuid:
                    new_layers.append(layer)
                    break
        self._state.layers = new_layers

    @Slot()
    def _on_change_partition(self, current: QListWidgetItem, previous: QListWidgetItem) -> None:
        enabled = current is not None
        selected_layer = self._state.selected_layer
        new_uuid = None
        if enabled:
            new_uuid = current.data(Qt.UserRole)

        if selected_layer is not None:
            selected_layer.current_partition_uuid = new_uuid

        self._canvas.update()
        self.update()

    @Slot()
    def _on_double_click_partition(self, current: QListWidgetItem) -> None:
        if current is None:
            return

        self._on_partition_edit()

    @Slot()
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

    @Slot()
    def _on_partition_rows_moved(self, parent, start, end, destination):
        if self._state is None or self._state.selected_layer is None:
            logger.warning("Cannot reorder partitions, no layer selected")
            return
        layer = self._state.selected_layer
        partitions = layer.partitions

        # reorder dict keys. Dictionary mantains order
        new_partitions = {}
        for row in range(self._partition_list.count()):
            item = self._partition_list.item(row)
            partition_uuid = item.data(Qt.UserRole)
            new_partitions[partition_uuid] = partitions[partition_uuid]
        layer.partitions = new_partitions

    @Slot()
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

    @Slot()
    def _on_update_embroidery_property(self) -> None:
        current_layer = self._state.selected_layer
        enabled = current_layer is not None
        self._embroidery_params_editor.setEnabled(enabled)
        if enabled:
            embroidery_params = EmbroideryParameters(
                pull_compensation_mm=self._pull_compensation_spinbox.value(),
                max_stitch_length_mm=self._max_stitch_length_spinbox.value(),
                min_jump_stitch_length_mm=self._min_jump_stitch_length_spinbox.value(),
                initial_angle_degrees=self._initial_angle_spinbox.value(),
                fill_method=self._fill_method_combo.currentData(),
            )
            current_layer.embroidery_params = embroidery_params

    @Slot()
    def _on_show_about_dialog(self) -> None:
        dialog = AboutDialog()
        dialog.exec()

    @Slot()
    def _on_position_changed_from_canvas(self, position: QPointF):
        self._position_x_spinbox.setValue(position.x())
        self._position_y_spinbox.setValue(position.y())

    @Slot()
    def _on_layer_selection_changed_from_canvas(self, layer_uuid: str):
        for i in range(self._layer_list.count()):
            item = self._layer_list.item(i)
            if item.data(Qt.UserRole) == layer_uuid:
                self._layer_list.setCurrentRow(i)
                break

    @Slot()
    def _on_layer_property_changed_from_state(self, layer: Layer):
        if self._state is None:
            logger.warning("Unexpected state. Should not be none")
            return
        if self._state.selected_layer != layer:
            logger.warning(
                f"Unexpected selected layer. Got '{layer.name}', expected: '{self._state.selected_layer.name}'"
            )
            return

        self._populate_property_editor(layer.properties)

        # Update Layer Name. Could have been changed from the editor
        item = self._layer_list.item(self._layer_list.currentRow())
        if item.data(Qt.UserRole) == layer.uuid:
            item.setText(layer.name)

        self._update_qactions()
        self._canvas.recalculate_fixed_size()
        self.update()

    @Slot()
    def _on_state_property_changed_from_state(
        self, flag: StatePropertyFlags, properties: StateProperties
    ):
        if flag not in [
            StatePropertyFlags.HOOP_SIZE,
            StatePropertyFlags.ZOOM_FACTOR,
            StatePropertyFlags.CURRENT_LAYER_UUID,
        ]:
            return
        if flag == StatePropertyFlags.HOOP_SIZE:
            self._canvas.on_preferences_updated()

        if flag == StatePropertyFlags.HOOP_SIZE or flag == StatePropertyFlags.ZOOM_FACTOR:
            self._canvas.recalculate_fixed_size()
            self._canvas.update()
            self.update()

    @Slot()
    def _on_canvas_mode_move(self):
        self._canvas_mode_move_action.setChecked(True)
        self._canvas_mode_drawing_action.setChecked(False)
        self._canvas.mode = Canvas.Mode.MOVE

    @Slot()
    def _on_canvas_mode_drawing(self):
        self._canvas_mode_move_action.setChecked(False)
        self._canvas_mode_drawing_action.setChecked(True)
        self._canvas.mode = Canvas.Mode.DRAWING

    @Slot()
    def _on_undo_stack_index_changed(self, index: int):
        if self._state:
            self._undo_action.setEnabled(self._state.undo_stack.canUndo())
            self._redo_action.setEnabled(self._state.undo_stack.canRedo())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Pixem")
    app.setOrganizationName("Retro Moe")
    app.setOrganizationDomain("retro.moe")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
