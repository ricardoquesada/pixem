# Pixem
# Copyright 2025 - Ricardo Quesada

from dataclasses import dataclass
from enum import IntFlag, auto


class StatePropertyFlags(IntFlag):
    HOOP_SIZE = auto()
    ZOOM_FACTOR = auto()
    SELECTED_LAYER_UUID = auto()
    HOOP_VISIBLE = auto()
    HOOP_COLOR = auto()
    CANVAS_BACKGROUND_COLOR = auto()
    PARTITION_FOREGROUND_COLOR = auto()
    PARTITION_BACKGROUND_COLOR = auto()


@dataclass
class StateProperties:
    hoop_size: tuple[float, float]
    zoom_factor: float
    selected_layer_uuid: str | None
    hoop_visible: bool
    hoop_color: str
    canvas_background_color: str
    partition_foreground_color: str
    partition_background_color: str
    export_filename: str | None = None
