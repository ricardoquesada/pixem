# Pixem
# Copyright 2024 - Ricardo Quesada

import logging
import uuid

from coloraide import Color
from PySide6.QtGui import QColor, QImage

from partition import Partition
from path_finder import PathFinder
from shape import Rect

logger = logging.getLogger(__name__)


class ImageParser:
    """
    Parses a QImage into a set of embroidery-ready partitions.

    This class analyzes the pixels of an image, groups them by color, and
    determines the optimal stitching order within each color group. It creates
    "partitions," where each partition contains a single color and is represented
    as a sequence of shapes (Rects for pixels and Paths for connecting jumps).

    The process involves:
    1.  Reading the QImage into an internal grid, ignoring transparent pixels.
    2.  Building a graph of connected, same-colored pixels.
    3.  For each color, ordering all its pixels into a single sequence,
        connecting any disconnected areas with calculated jump-stitch paths.
    4.  Storing the final result in a dictionary of Partition objects.
    """

    OFFSETS = {
        "NW": (-1, -1),
        "N": (0, -1),
        "NE": (1, -1),
        "E": (1, 0),
        "SE": (1, 1),
        "S": (0, 1),
        "SW": (-1, 1),
        "W": (-1, 0),
    }

    def __init__(self, image: QImage, background_color: QColor | None = None):
        """
        Initializes the ImageParser and processes the given image.

        Args:
            image: The QImage to be parsed.
            background_color: The background color to compare against for sorting.
        """
        self._path_finder = PathFinder(image)

        width, height = image.width(), image.height()

        self._jump_stitches = 0

        # One graph per color, since weights changes from color to color
        self._partitions = {}

        # Group the ones that are touching/same-color together
        g = self._create_color_graph(width, height)

        # Sort colors based on distance to background color
        # If no background color, sort by lightness (legacy behavior)
        if background_color is None:
            sorted_colors = sorted(g.keys(), key=lambda c: Color(f"#{c:06x}").get("oklab.l"))
        else:
            # Sort by distance to background color (descending)
            # Furthest colors first (drawn at bottom), Closest colors last (drawn on top)
            bg = Color(background_color.name())
            sorted_colors = sorted(
                g.keys(),
                key=lambda c: Color(f"#{c:06x}").delta_e(bg, method="2000"),
                reverse=True,
            )

        for color in sorted_colors:
            self._create_single_partition_for_color(g[color], color)

    def _create_single_partition_for_color(self, image_graph: dict, color: int) -> None:
        """
        Create a single partition for the given color.
        Nodes are ordered by performing a Depth-First Search (DFS) across all
        connected components within the color group. If components are
        disconnected, a Path object, consisting of only horizontal and
        vertical lines, is created to connect them.
        :param image_graph: a dict that contains the nodes and their edges.
        :param color: The color of the partition.
        :return: None
        """
        name = f"#{color:06x}_0"
        color_str = f"#{color:06x}"

        rects = [Rect(x, y) for x, y in image_graph.keys()]
        shapes = self._path_finder.optimize_route(color, rects)

        if not shapes:
            return

        partition = Partition(shapes, name, color_str)
        partition_uuid = str(uuid.uuid4())
        self._partitions[partition_uuid] = partition

    def _create_color_graph(self, width, height) -> dict:
        # Creates a dictionary of key=color, value=dict of nodes and its edges
        # Each color is a list of nodes
        d = {}
        directions = ["NW", "N", "NE", "E", "SE", "S", "SW", "W"]

        for x in range(width):
            for y in range(height):
                color = self._path_finder.get_pixel_color(x, y)
                if color == -1:
                    continue
                if color not in d:
                    d[color] = {}
                neighbors = []
                for direction in directions:
                    offset = self.OFFSETS[direction]
                    new_x = x + offset[0]
                    new_y = y + offset[1]
                    new_color = self._path_finder.get_pixel_color(new_x, new_y)
                    if new_color != color:
                        continue
                    neighbors.append((new_x, new_y))
                d[color][(x, y)] = neighbors
        return d

    @property
    def partitions(self) -> dict[str, Partition]:
        return self._partitions
