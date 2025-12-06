# Pixem
# Copyright 2025 - Ricardo Quesada

import logging
import sys

import networkx as nx
from coloraide import Color
from PySide6.QtGui import QColor, QImage

from shape import Point

logger = logging.getLogger(__name__)


class PathFinder:
    """
    Helper class to find paths in an image.
    It encapsulates the logic for creating graphs implementation of pixels and finding
    shortest paths between them, considering color differences.
    """

    def __init__(self, image: QImage):
        """
        Initializes the PathFinder with a QImage.

        Args:
            image: The QImage to be processed.
        """
        self._image_matrix = []
        self._vertex_graph = {}
        self._width = image.width()
        self._height = image.height()

        self._put_pixels_in_matrix(image)

    def _put_pixels_in_matrix(self, img: QImage):
        """
        Populates an internal 2D list with pixel color data from the QImage.

        Transparent pixels are marked as -1.
        """
        width, height = self._width, self._height
        self._image_matrix = [[-1 for _ in range(height)] for _ in range(width)]

        for y in range(height):
            for x in range(width):
                color: QColor = img.pixelColor(x, y)
                # Returns a qRgb which is ARGB instead of RGBA
                argb = color.rgba()
                a = (argb >> 24) & 0xFF
                if a != 255:
                    # Skip transparent pixels
                    continue
                color_val = argb & 0xFFFFFF
                self._image_matrix[x][y] = color_val

    def get_pixel_color(self, x: int, y: int) -> int:
        """Returns the color of the pixel at (x, y), or -1 if transparent/out of bounds."""
        if 0 <= x < self._width and 0 <= y < self._height:
            return self._image_matrix[x][y]
        return -1

    def get_vertex_graph(self, color: int, use_weights: bool) -> nx.Graph:
        """
        Builds and caches a networkx.Graph of all valid path vertices.

        The nodes of the graph are the vertices of the pixel grid. An edge
        is created between two vertices if the path segment between them is
        "valid" — meaning it runs alongside at least one non-transparent pixel.

        If use_weights is True, edge weights are determined by the color
        difference of adjacent pixels. Otherwise, all edges have a weight of 1.
        """

        def is_solid(px: int, py: int) -> bool:
            if 0 <= px < self._width and 0 <= py < self._height:
                return self._image_matrix[px][py] != -1
            return False

        def get_weight(px: int, py: int) -> int:
            if not use_weights:
                return 1

            if not (0 <= px < self._width and 0 <= py < self._height):
                return sys.maxsize

            px_color_val = self._image_matrix[px][py]
            if px_color_val == -1:
                return sys.maxsize

            color1 = Color(f"#{color:06x}")
            color2 = Color(f"#{px_color_val:06x}")
            delta_e = color1.delta_e(color2, method="2000")
            w = 1 + 0.1 * (delta_e**2)
            return int(w)

        # Use a tuple key to cache both weighted and unweighted graphs
        graph_key = (color, use_weights)
        if graph_key in self._vertex_graph:
            return self._vertex_graph[graph_key]

        G = nx.Graph()
        w_vertex, h_vertex = self._width + 1, self._height + 1

        for y in range(h_vertex):
            for x in range(w_vertex):
                if x + 1 < w_vertex:
                    if is_solid(x, y - 1) or is_solid(x, y):
                        weight = min(get_weight(x, y - 1), get_weight(x, y))
                        G.add_edge((x, y), (x + 1, y), weight=weight)

                if y + 1 < h_vertex:
                    if is_solid(x - 1, y) or is_solid(x, y):
                        weight = min(get_weight(x - 1, y), get_weight(x, y))
                        G.add_edge((x, y), (x, y + 1), weight=weight)

        self._vertex_graph[graph_key] = G
        return self._vertex_graph[graph_key]

    def find_shortest_pixel_path(
        self, color: int, start_node: tuple[int, int], end_node: tuple[int, int], use_weights: bool
    ) -> list[tuple[int, int]] | None:
        """
        Finds the shortest path between two vertices on the pixel grid.

        If use_weights is True, it finds the path with the minimum total weight
        (using Dijkstra), considering color differences. If False, it finds the
        path with the fewest segments (using BFS).
        """
        G = self.get_vertex_graph(color, use_weights)
        try:
            if start_node not in G or end_node not in G:
                logger.warning(
                    f"Start or end node not in vertex graph. Start: {start_node}, End: {end_node}"
                )
                return None
            # When weight is None, it uses BFS (fewest segments). When it's 'weight', it uses Dijkstra.
            weight_arg = "weight" if use_weights else None
            return nx.shortest_path(G, source=start_node, target=end_node, weight=weight_arg)
        except nx.NetworkXNoPath:
            logger.info(f"No path found between {start_node} and {end_node}")
            return None

    def remove_redundant_points_from_start_and_end_nodes(
        self, node_path: list[tuple[int, int]]
    ) -> list[tuple[int, int]]:
        """
        Trims the path to ensure it starts and ends with a single vertex
        belonging to the start and end pixels, respectively.
        """
        if len(node_path) < 2:
            return node_path

        # Define the vertices for the start and end pixels based on the path
        sx, sy = node_path[0]
        start_pixel_vertices = {(sx, sy), (sx + 1, sy), (sx, sy + 1), (sx + 1, sy + 1)}

        ex, ey = node_path[-1]
        end_pixel_vertices = {(ex, ey), (ex + 1, ey), (ex, ey + 1), (ex + 1, ey + 1)}

        # Find the index of the last point in the path that is a vertex of the start pixel.
        # This is the "exit point" from the start pixel.
        start_idx = 0
        for i, p in enumerate(node_path):
            if p in start_pixel_vertices:
                start_idx = i
            else:
                break

        # Find the index of the first point in the path (from the end) that is a vertex of the end
        # pixel. This is the "entry point" to the end pixel.
        end_idx = len(node_path) - 1
        for i, p in enumerate(reversed(node_path)):
            if p in end_pixel_vertices:
                end_idx = len(node_path) - 1 - i
            else:
                break

        # If the calculated start and end indices overlap or create an invalid path,
        # it implies a very short path (e.g., between adjacent pixels). In this
        # case, returning the original path is the safest option.
        if start_idx >= end_idx:
            # Check if start and end are the same point (0 distance)
            if node_path[0] == node_path[-1]:
                return [node_path[0]]
            return node_path

        return node_path[start_idx : end_idx + 1]

    def simplify_path_to_points(self, node_path: list[tuple[int, int]]) -> list[Point]:
        """
        Converts a list of path vertices into a simplified list of Points.

        It simplifies the path by keeping only the start, end, and corner
        points, effectively removing redundant collinear points.
        """
        if len(node_path) < 2:
            points = [Point(n[0], n[1]) for n in node_path]
            return points

        simplified = [Point(node_path[0][0], node_path[0][1])]
        for i in range(1, len(node_path) - 1):
            p_prev = node_path[i - 1]
            p_curr = node_path[i]
            p_next = node_path[i + 1]

            # Check for change in direction
            dx1 = p_curr[0] - p_prev[0]
            dy1 = p_curr[1] - p_prev[1]
            dx2 = p_next[0] - p_curr[0]
            dy2 = p_next[1] - p_curr[1]

            if dx1 != dx2 or dy1 != dy2:
                simplified.append(Point(p_curr[0], p_curr[1]))

        simplified.append(Point(node_path[-1][0], node_path[-1][1]))

        return simplified
