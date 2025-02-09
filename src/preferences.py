# Copyright 2025 Ricardo Quesada
import typing

from PySide6.QtCore import (
    QSettings,
)


class Preferences:
    STATE_VERSION = 1

    def __init__(self):
        self.settings = QSettings()

    def get_window_geometry(self) -> typing.Any:
        return self.settings.value("main_window/window_geometry", defaultValue=None)

    def get_window_state(self) -> typing.Any:
        return self.settings.value("main_window/window_state", defaultValue=None)

    def set_window_geometry(self, geometry: typing.Any) -> None:
        self.settings.setValue("main_window/window_geometry", geometry)

    def set_window_state(self, state: typing.Any) -> None:
        self.settings.setValue("main_window/window_state", state)

    def get_default_window_geometry(self) -> typing.Any:
        return self.settings.value("main_window/default_window_geometry", defaultValue=None)

    def get_default_window_state(self) -> typing.Any:
        return self.settings.value("main_window/default_window_state", defaultValue=None)

    def set_default_window_geometry(self, geometry: typing.Any) -> None:
        self.settings.setValue("main_window/default_window_geometry", geometry)

    def set_default_window_state(self, state: typing.Any) -> None:
        self.settings.setValue("main_window/default_window_state", state)

    def set_hoop_visible(self, visible: bool) -> None:
        self.settings.setValue("hoop/visible", visible)

    def get_hoop_visible(self) -> bool:
        return bool(self.settings.value("hoop/visible", defaultValue=True))

    def set_hoop_size(self, size: tuple) -> None:
        self.settings.setValue("hoop/size_x", size[0])
        self.settings.setValue("hoop/size_y", size[1])

    def get_hoop_size(self) -> tuple:
        x = int(self.settings.value("hoop/size_x", defaultValue=4))
        y = int(self.settings.value("hoop/size_y", defaultValue=4))
        return x, y


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
