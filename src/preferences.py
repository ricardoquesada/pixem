# Pixem
# Copyright 2025 - Ricardo Quesada
import logging
import os.path
import typing

from PySide6.QtCore import QSettings

logger = logging.getLogger(__name__)


class Preferences:
    STATE_VERSION = 1
    MAX_RECENT_FILES = 5

    def __init__(self):
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
        self._settings.setValue("hoop/visible", visible)

    def get_hoop_visible(self) -> bool:
        return bool(self._settings.value("hoop/visible", defaultValue=True))

    def set_hoop_size(self, size: tuple[float, float]) -> None:
        logger.info(f"hoop size: {size}")
        self._settings.setValue("hoop/size_x", size[0])
        self._settings.setValue("hoop/size_y", size[1])

    def get_hoop_size(self) -> tuple[float, float]:
        x = float(self._settings.value("hoop/size_x", defaultValue=4))
        y = float(self._settings.value("hoop/size_y", defaultValue=4))
        logger.info(f"ret hoop size: {x} {y}")
        return x, y

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

    def _load_recent_files(self) -> None:
        recent_files = self._settings.value("files/recent_files", [])
        if isinstance(recent_files, list):
            self._recent_files = recent_files
        elif isinstance(recent_files, str):
            self._recent_files.append(recent_files)

        for filename in self._recent_files:
            if not os.path.exists(filename):
                self._recent_files.remove(filename)


# Singleton
global_preferences = Preferences()

if __name__ == "__main__":
    preferences = global_preferences
    preferences.set_hoop_size((5, 8))

    print(f"State: {preferences.get_window_state()}")
    print(f"Geometry: {preferences.get_window_geometry()}")
    print(f"Default State: {preferences.get_default_window_state()}")
    print(f"Default Geometry: {preferences.get_default_window_geometry()}")
    print(f"Hoop visible: {preferences.get_hoop_visible()}")
    print(f"Hoop size: {preferences.get_hoop_size()}")
