# Pixem
# Copyright 2025 - Ricardo Quesada

import logging
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Self

logger = logging.getLogger(__name__)  # __name__ gets the current module's name


class Partition:
    class WalkMode(Enum):
        SPIRAL_CW = auto()
        SPIRAL_CCW = auto()
        SNAKE_CW = auto()
        SNAKE_CCW = auto()
        SELF_AVOIDANCE_WALK = auto()

    @dataclass
    class Node:
        coord: tuple[int, int]
        dir: str

    def __init__(self, path: list[tuple[int, int]], name: Optional[str] = None):
        self._path = path
        self._size = len(path)
        self._name = name

    @staticmethod
    def _rotate_offsets(offsets: list[Node], dir: str) -> list[Node]:
        # offset should be in a way that the opposite direction is the first element.
        # in other words, that the passed direction is the third element
        while offsets[2].dir != dir:
            offsets = offsets[1:] + offsets[:1]
        return offsets

    def _find_neighbors(self, node: Node) -> list[Node]:
        offsets = [
            Partition.Node((0, 1), "S"),  # down
            Partition.Node((-1, 0), "W"),  # left
            Partition.Node((0, -1), "N"),  # up
            Partition.Node((1, 0), "E"),  # right
        ]

        offsets = Partition._rotate_offsets(offsets, node.dir)
        neighbors = []
        for offset in offsets:
            neighbor = (node.coord[0] + offset.coord[0], node.coord[1] + offset.coord[1])
            if neighbor in self._path:
                new_node = Partition.Node(neighbor, offset.dir)
                neighbors.append(new_node)
        return neighbors

    @classmethod
    def from_dict(cls, d: dict) -> Self:
        path = [(x, y) for x, y in d["path"]]
        part = Partition(path)

        if "name" in d:
            part.name = d["name"]

        if "size" in d and d["size"] != len(path):
            logger.warning(f"Unexpected size in Partition. Wanted {len(path)}, got {d['size']}")

        return part

    def to_dict(self) -> dict:
        """Returns a dictionary that represents the Layer"""
        d = {
            "path": self._path,
            "size": len(self._path),
            "name": self._name,
        }
        return d

    def walk_path(self, mode: WalkMode, start_point: tuple[int, int]) -> None:
        visited = set()
        node = Partition.Node(start_point, "N")

        stack = [node]
        new_path = []

        while stack:
            node = stack.pop()
            coord = node.coord
            if coord not in visited:
                visited.add(coord)
                new_path.append(coord)
                neighbors = self._find_neighbors(node)
                if mode == Partition.WalkMode.SPIRAL_CW:
                    # Walk it in opposite direction
                    neighbors = reversed(neighbors)
                for neighbor in neighbors:
                    new_coord = neighbor.coord
                    if new_coord not in visited:
                        stack.append(neighbor)
        self._path = new_path

    @property
    def path(self) -> list[tuple[int, int]]:
        return self._path

    @path.setter
    def path(self, value: list[tuple[int, int]]) -> None:
        self._path = value
        self._size = len(value)

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str):
        self._name = value
