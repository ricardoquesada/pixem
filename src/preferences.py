# Pixem
# Copyright 2025 - Ricardo Quesada
import logging
import os.path
import typing

from PySide6.QtCore import QObject, QSettings, Signal

logger = logging.getLogger(__name__)


class Preferences(QObject):
    STATE_VERSION = 1
    MAX_RECENT_FILES = 20

    partition_background_color_changed = Signal(str)
    canvas_background_color_changed = Signal(str)
    canvas_hoop_color_changed = Signal(str)
    hoop_visible_changed = Signal(bool)
    hoop_size_changed = Signal(tuple)

    def __init__(self):
        super().__init__()
        self._settings = QSettings()
        self._recent_files = []

        self._load_recent_files()

    def get_window_geometry(self) -> typing.Any:
        return self._settings.value("main_window/window_geometry", defaultValue=None)

    def get_window_state(self) -> typing.Any:
        return self._settings.value("main_window/window_state", defaultValue=None)

    def set_window_geometry(self, geometry: typing.Any) -> None:
        self._settings.setValue("main_window/window_geometry", geometry)

    def set_window_state(self, state: typing.Any) -> None:
        self._settings.setValue("main_window/window_state", state)

    def get_default_window_geometry(self) -> typing.Any:
        return self._settings.value("main_window/default_window_geometry", defaultValue=None)

    def get_default_window_state(self) -> typing.Any:
        return self._settings.value("main_window/default_window_state", defaultValue=None)

    def set_default_window_geometry(self, geometry: typing.Any) -> None:
        self._settings.setValue("main_window/default_window_geometry", geometry)

    def set_default_window_state(self, state: typing.Any) -> None:
        self._settings.setValue("main_window/default_window_state", state)

    def set_hoop_visible(self, visible: bool) -> None:
        current = self.get_hoop_visible()
        if current != visible:
            self._settings.setValue("hoop/visible", visible)
            self.hoop_visible_changed.emit(visible)

    def get_hoop_visible(self) -> bool:
        return bool(self._settings.value("hoop/visible", defaultValue=True))

    def set_hoop_size(self, size: tuple[float, float]) -> None:
        current = self.get_hoop_size()
        if current[0] != size[0] or current[1] != size[1]:
            self._settings.setValue("hoop/size_x", size[0])
            self._settings.setValue("hoop/size_y", size[1])
            self.hoop_size_changed.emit(size)

    def get_hoop_size(self) -> tuple[float, float]:
        x = float(self._settings.value("hoop/size_x", defaultValue=4))
        y = float(self._settings.value("hoop/size_y", defaultValue=4))
        return x, y

    def get_hoop_color_name(self) -> str:
        return str(self._settings.value("hoop/foreground_color", defaultValue="#c0c0c0ff"))

    def set_hoop_color_name(self, color: str):
        current = self.get_hoop_color_name()
        if current != color:
            self._settings.setValue("hoop/foreground_color", color)
            self.canvas_hoop_color_changed.emit(color)

    def set_open_file_on_startup(self, value: bool) -> None:
        self._settings.setValue("files/open_file_on_startup", value)

    def get_open_file_on_startup(self) -> bool:
        return bool(self._settings.value("files/open_file_on_startup", defaultValue=True))

    def get_recent_files(self) -> list[str]:
        return self._recent_files

    def add_recent_file(self, filename: str) -> None:
        if filename in self._recent_files:
            self._recent_files.remove(filename)
        self._recent_files.insert(0, filename)
        if len(self._recent_files) > self.MAX_RECENT_FILES:
            self._recent_files.pop()
        self.save_recent_files()

    def remove_recent_file(self, filename: str) -> None:
        if filename in self._recent_files:
            self._recent_files.remove(filename)
        self.save_recent_files()

    def clear_recent_files(self) -> None:
        self._recent_files.clear()
        self.save_recent_files()

    def save_recent_files(self) -> None:
        self._settings.setValue("files/recent_files", self._recent_files)

    def get_partition_foreground_color_name(self) -> str:
        return str(self._settings.value("partition/foreground_color", defaultValue="#800000ff"))

    def set_partition_foreground_color_name(self, color: str):
        self._settings.setValue("partition/foreground_color", color)

    def get_partition_background_color_name(self) -> str:
        return str(self._settings.value("partition/background_color", defaultValue="#80ff0000"))

    def set_partition_background_color_name(self, color: str):
        current = self.get_partition_background_color_name()
        if current != color:
            self._settings.setValue("partition/background_color", color)
            self.partition_background_color_changed.emit(color)

    def get_canvas_background_color_name(self) -> str:
        return str(self._settings.value("canvas/background_color", defaultValue="#a0a0a0ff"))

    def set_canvas_background_color_name(self, color: str):
        current = self.get_canvas_background_color_name()
        if current != color:
            self._settings.setValue("canvas/background_color", color)
            self.canvas_background_color_changed.emit(color)

    def set_delete_point_enabled(self, enabled: bool) -> None:
        self._settings.setValue("partition/delete_point_enabled", enabled)

    def get_delete_point_enabled(self) -> bool:
        return bool(self._settings.value("partition/delete_point_enabled", defaultValue=False))

    def _load_recent_files(self) -> None:
        recent_files = self._settings.value("files/recent_files", [])
        if isinstance(recent_files, list):
            self._recent_files = recent_files
        elif isinstance(recent_files, str):
            self._recent_files.append(recent_files)

        for filename in self._recent_files:
            if not os.path.exists(filename):
                self._recent_files.remove(filename)


_global_preferences = None


# Singleton
def get_global_preferences() -> Preferences:
    # Using a function to return the global instance so that we can delay
    # the creation of QSettings() after QApplication.setOrganizationName() is called
    global _global_preferences
    if _global_preferences is None:
        _global_preferences = Preferences()
    return _global_preferences


if __name__ == "__main__":
    preferences = get_global_preferences()
    preferences.set_hoop_size((5, 8))

    print(f"State: {preferences.get_window_state()}")
    print(f"Geometry: {preferences.get_window_geometry()}")
    print(f"Default State: {preferences.get_default_window_state()}")
    print(f"Default Geometry: {preferences.get_default_window_geometry()}")
    print(f"Hoop visible: {preferences.get_hoop_visible()}")
    print(f"Hoop size: {preferences.get_hoop_size()}")
