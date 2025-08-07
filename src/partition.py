# Pixem
# Copyright 2025 - Ricardo Quesada

import logging
import random
from dataclasses import dataclass
from enum import IntEnum, auto
from typing import Self

from shape import Rect, Shape

logger = logging.getLogger(__name__)


class Partition:
    class WalkMode(IntEnum):
        SPIRAL_CW = auto()
        SPIRAL_CCW = auto()
        RANDOM = auto()

    @dataclass
    class Node:
        coord: tuple[int, int]
        dir: str

    def __init__(self, path: list[Shape], name: str | None = None, color: str | None = None):
        self._path = path
        self._name = name
        # color format "#FFFFFF"
        self._color = color

    @staticmethod
    def _rotate_offsets(offsets: list[Node], dir: str) -> list[Node]:
        # offset should be in a way that the opposite direction is the first element.
        # in other words, that the passed direction is the third element
        while offsets[2].dir != dir:
            offsets = offsets[1:] + offsets[:1]
        return offsets

    @classmethod
    def from_dict(cls, d: dict) -> Self:
        shapes = d["path"]
        path = []
        for shape in shapes:
            if isinstance(shape, dict):
                typ = shape["type"]
                if typ == "rect":
                    path.append(Rect(shape["x"], shape["y"]))
                else:
                    raise Exception(f"Unknown shape type: {shape["type"]}")
            elif isinstance(shape, list):
                # Backward compatible
                # Sanity check
                assert isinstance(shape[0], int) and isinstance(shape[1], int)
                path.append(Rect(shape[0], shape[1]))
            else:
                raise Exception(f"Unknown shape type: {shape}")
        part = Partition(path)

        if "name" in d:
            part._name = d["name"]

        if "size" in d and d["size"] != len(path):
            logger.warning(f"Unexpected size in Partition. Wanted {len(path)}, got {d['size']}")

        if "color" in d:
            part._color = d["color"]

        return part

    def to_dict(self) -> dict:
        """Returns a dictionary that represents the Partition"""
        path = []
        for shape in self._path:
            e = {"type": "rect", "x": shape.x, "y": shape.y}
            path.append(e)
        d = {
            "path": path,
            "size": len(self._path),
            "name": self._name,
            "color": self._color,
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
                neighbors = self._find_neighbors(mode, node)
                for neighbor in neighbors:
                    new_coord = neighbor.coord
                    if new_coord not in visited:
                        stack.append(neighbor)

        # add possible missing nodes. Could happen since diagonals are not visited in this algorithm
        for coord in self._path:
            if coord not in new_path:
                new_path.append(coord)
        path = [Rect(shape.x, shape.y) for shape in new_path]
        self._path = path

    def _find_neighbors(self, mode: WalkMode, node: Node) -> list[Node]:
        offsets = [
            Partition.Node((0, 1), "S"),  # down
            Partition.Node((-1, 0), "W"),  # left
            Partition.Node((0, -1), "N"),  # up
            Partition.Node((1, 0), "E"),  # right
        ]
        if mode == Partition.WalkMode.SPIRAL_CW or mode == Partition.WalkMode.SPIRAL_CCW:
            offsets = Partition._rotate_offsets(offsets, node.dir)
        elif mode == Partition.WalkMode.RANDOM:
            random.shuffle(offsets)

        neighbors = []
        for offset in offsets:
            neighbor = (node.coord[0] + offset.coord[0], node.coord[1] + offset.coord[1])
            if neighbor in self._path:
                new_node = Partition.Node(neighbor, offset.dir)
                if mode == Partition.WalkMode.SPIRAL_CW:
                    neighbors.insert(0, new_node)
                else:
                    neighbors.append(new_node)
        return neighbors

    @property
    def path(self) -> list[Shape]:
        return self._path

    @path.setter
    def path(self, value: list[Shape]) -> None:
        self._path = value

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str):
        self._name = value

    @property
    def color(self) -> str:
        return self._color

    @property
    def pixel_count(self) -> int:
        return len(self._path)
