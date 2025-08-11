# Pixem
# Copyright 2025 - Ricardo Quesada

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class Point:
    """Represents a point in 2D space.

    Using a frozen dataclass makes instances immutable, hashable, and
    provides an __eq__ method automatically.
    """

    x: int
    y: int


class Shape(ABC):
    """An abstract base class for all shape types.

    It defines the common interface that all concrete shapes must implement.
    By setting __hash__ = None, we make all subclasses unhashable by default.
    This is the correct behavior for mutable objects. Subclasses that are
    immutable can override this and implement their own __hash__.
    """

    __hash__ = None

    @abstractmethod
    def __eq__(self, other):
        """All subclasses must implement equality comparison."""
        raise NotImplementedError


@dataclass(frozen=True)
class Rect(Shape):
    """Represents an immutable point defined by its position in the grid.
    This point represents a Rect when exported to Ink/Stitch. That's why it is
    called a Rect.

    As a frozen dataclass, it automatically gets __init__, __repr__, __eq__,
    and __hash__ methods. It's hashable because it's immutable.
    """

    x: int
    y: int
    # The dataclass automatically provides __eq__ and __hash__
    # which satisfy the abstract methods from Shape.


class Path(Shape):
    """Represents a mutable path composed of a sequence of points."""

    def __init__(self, path: list[Point]):
        """Initializes the Path with a list of points.

        A defensive copy of the path is made to prevent external
        modifications to the list from affecting the Path's state.
        """
        super().__init__()
        self.path = list(path)  # Defensive copy

    def __eq__(self, other):
        """Overrides the default '==' behavior."""
        if not isinstance(other, Path):
            return NotImplemented
        return self.path == other.path

    def append_point(self, point: Point):
        """Appends a point to the end of the path."""
        self.path.append(point)

    def delete_point(self, point: Point):
        """Deletes the first occurrence of a point from the path."""
        self.path.remove(point)
