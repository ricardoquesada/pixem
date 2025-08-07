# Pixem
# Copyright 2025 - Ricardo Quesada

from enum import IntEnum, auto


class LinePosition(IntEnum):
    TOP = auto()
    BOTTOM = auto()
    LEFT = auto()
    RIGHT = auto()


class Shape:
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y

    def __eq__(self, other):
        """Overrides the default '==' behavior."""
        if not isinstance(other, Rect):
            return NotImplemented

        # If it is, compare the attributes you care about.
        return self.x == other.x and self.y == other.y


class Rect(Shape):
    pass


class Line(Shape):
    def __init__(self, x: int, y: int, position: LinePosition):
        super().__init__(x, y)
        self.position = position
