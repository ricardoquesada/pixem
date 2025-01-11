# Copyright 2025 Ricardo Quesada
import typing

from PySide6.QtCore import (
    QSettings,
)


class Settings:
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


if __name__ == "__main__":
    settings = Settings()
    print(f"State: {settings.get_window_state()}")
    print(f"Geometry: {settings.get_window_geometry()}")
    print(f"Default State: {settings.get_default_window_state()}")
    print(f"Default Geometry: {settings.get_default_window_geometry()}")
    print(f"Hoop visible: {settings.get_hoop_visible()}")
