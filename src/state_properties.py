# Pixem
# Copyright 2025 - Ricardo Quesada

from dataclasses import dataclass
from enum import IntFlag, auto


class StatePropertyFlags(IntFlag):
    HOOP_SIZE = auto()
    ZOOM_FACTOR = auto()
    SELECTED_LAYER_UUID = auto()


@dataclass
class StateProperties:
    hoop_size: tuple[float, float]
    zoom_factor: float
    selected_layer_uuid: str | None
    export_filename: str | None = None
