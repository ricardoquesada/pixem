# WIP WIP WIP

from enum import Enum, auto


class Partition:
    class FillMode(Enum):
        SPIRAL_CW = auto()
        SPIRAL_CCW = auto()
        SNAKE_CW = auto()
        SNAKE_CCW = auto()


def _rotate_offsets(offsets: list[tuple[int, int, str]], dir: str) -> list[tuple[int, int, str]]:
    # offset should be in a way that the opposite direction is the first element.
    # in other words, that the passed direction is the third element
    while offsets[2][2] != dir:
        offsets = offsets[1:] + offsets[:1]
    return offsets


def _find_neighbors(node: dict, partition: list[tuple[int, int]]) -> list[dict]:
    # node:
    # {
    #  "coord": (x, y),
    #  "dir": str,
    # }
    offsets = [
        (0, 1, "S"),  # down
        (-1, 0, "W"),  # left
        (0, -1, "N"),  # up
        (1, 0, "E"),  # right
    ]

    offsets = _rotate_offsets(offsets, node["dir"])
    neighbors = []
    for offset in offsets:
        coord = node["coord"]
        neighbor = (coord[0] + offset[0], coord[1] + offset[1])
        if neighbor in partition:
            new_node = {
                "coord": neighbor,
                "dir": offset[2],
            }
            neighbors.insert(0, new_node)
    return neighbors


def order_partition(
    partition: list[tuple[int, int]], start_coord: tuple[int, int], fill_mode: Partition.FillMode
) -> list[tuple[int, int]]:
    visited = set()
    node = {
        "coord": start_coord,
        "dir": "N",
    }

    stack = [node]
    ret = []

    while stack:
        node = stack.pop()
        coord = node["coord"]
        if coord not in visited:
            visited.add(coord)
            ret.append(coord)
            for neighbor in _find_neighbors(node, partition):
                new_coord = neighbor["coord"]
                if new_coord not in visited:
                    stack.append(neighbor)
    return ret
