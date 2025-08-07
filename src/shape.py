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


class Rect(Shape):
    pass


class Line(Shape):
    def __init__(self, x: int, y: int, position: LinePosition):
        super().__init__(x, y)
        self.position = position
