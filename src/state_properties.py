# Pixem
# Copyright 2025 - Ricardo Quesada

from dataclasses import dataclass
from enum import Enum


class StatePropertyFlags(int, Enum):
    HOOP_SIZE = 1 << 0
    ZOOM_FACTOR = 1 << 1
    CURRENT_LAYER_UUID = 1 << 2


@dataclass
class StateProperties:
    hoop_size: tuple[float, float]
    zoom_factor: float
    current_layer_uuid: str | None
    export_filename: str | None = None
