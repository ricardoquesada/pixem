# Pixem
# Copyright 2024 - Ricardo Quesada

import logging
import uuid
from collections import deque

import networkx as nx
from PySide6.QtGui import QColor, QImage

from partition import Partition
from shape import Path, Point, Rect, Shape

logger = logging.getLogger(__name__)


def _get_node_with_one_neighbor(G):
    # Returns the first node that has a degree of 1
    nodes_with_one_neighbor = [node for node, degree in G.degree() if degree == 1]
    if len(nodes_with_one_neighbor) > 0:
        return nodes_with_one_neighbor[0]
    return None


def _get_top_left_node(G):
    curr_node = None
    curr_dist = 1000000
    for node in G.nodes():
        x, y = node
        d = x * x + y * y
        if d < curr_dist:
            curr_dist = d
            curr_node = node
    return curr_node


class ImageParser:
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

    def __init__(self, image: QImage, one_partition_per_color: bool = True):
        width, height = image.width(), image.height()

        self._jump_stitches = 0
        self._image = [[-1 for _ in range(height)] for _ in range(width)]

        self._partitions = {}

        # Put all pixels in matrix
        self._put_pixels_in_matrix(image, width, height)
        # Group the ones that are touching/same-color together
        g = self._create_color_graph(width, height)

        for color in g:
            if one_partition_per_color:
                self._create_single_partition_for_color(g[color], color)
            else:
                self._create_multiple_partitions_for_color(g[color], color)

    def _set_conf_value(self, arg_value, key, default):
        # Priority:
        #   1. argument
        #   2. conf
        #   3. default
        if arg_value is not None:
            self._conf[key] = arg_value

        if key not in self._conf or self._conf[key] is None:
            self._conf[key] = default

    def _put_pixels_in_matrix(self, img: QImage, width: int, height: int):
        # Put all pixels in matrix
        for y in range(height):
            for x in range(width):
                color: QColor = img.pixelColor(x, y)
                # Returns a qRgb which is ARGB instead of RGBA
                argb = color.rgba()
                a = (argb >> 24) & 0xFF
                if a != 255:
                    # Skip transparent pixels
                    continue
                self._image[x][y] = argb & 0xFFFFFF

    def _create_multiple_partitions_for_color(self, image_graph: dict, color: int) -> None:
        """
        Create multiple partitions for the given color. The partitions are created based on whether the nodes are connected.
        This used to be the old behavior. Keeping it in case it is needed again.
        :param image_graph: The dict that contains the nodes and the edges.
        :param color: The color of the partition.
        :return: None
        """
        # image_graph is a dict of:
        #   key: node
        #   value: edges
        nodes = image_graph.keys()
        edges = []
        for node in image_graph:
            for edge in image_graph[node]:
                edges.append((node, edge))

        G = nx.Graph()
        G.add_nodes_from(nodes)
        G.add_edges_from(edges)

        # The graph might include disconnected nodes, identify them
        # and process each subgraph independently
        S = [G.subgraph(c).copy() for c in nx.connected_components(G)]
        for idx, s in enumerate(S):
            # nx.draw(s, with_labels=True)
            # plt.show()
            nodes = list(s.nodes())

            name = f"#{color:06x}_{idx}"
            color_str = f"#{color:06x}"

            shapes = [Rect(node[0], node[1]) for node in nodes]
            partition = Partition(shapes, name, color_str)

            partition_uuid = str(uuid.uuid4())
            if partition_uuid not in self._partitions:
                self._partitions[partition_uuid] = partition

                if len(nodes) > 1:
                    start_node = self._get_starting_node(s)
                    partition.walk_path(Partition.WalkMode.SPIRAL_CW, start_node)

    def _get_ordered_nodes_for_color(self, image_graph: dict) -> list[tuple[int, int]]:
        """
        Performs a Depth-First Search on the color graph to get a single
        ordered list of all nodes, traversing disconnected components.
        """
        all_nodes = list(image_graph.keys())
        if not all_nodes:
            return []

        ordered_nodes = []
        visited = set()

        # We iterate through all nodes to handle disconnected components
        for node in all_nodes:
            if node not in visited:
                # This node is part of a new, unvisited component.
                # Start a new DFS from here.
                stack = [node]

                while stack:
                    current_node = stack.pop()
                    if current_node not in visited:
                        visited.add(current_node)
                        ordered_nodes.append(current_node)

                        # Add unvisited neighbors to the stack.
                        # Sorting neighbors makes the traversal deterministic.
                        neighbors = sorted(image_graph.get(current_node, []), reverse=True)
                        for neighbor in neighbors:
                            if neighbor not in visited:
                                stack.append(neighbor)
        return ordered_nodes

    def _find_shortest_pixel_path(
        self, start_node: tuple[int, int], end_node: tuple[int, int]
    ) -> list[tuple[int, int]] | None:
        """
        Finds the shortest path between two nodes on the image grid using BFS.
        The path can traverse any non-transparent pixel.
        """
        width, height = len(self._image), len(self._image[0])
        queue = deque([(start_node, [start_node])])
        visited = {start_node}

        while queue:
            current, path = queue.popleft()

            if current == end_node:
                return path

            x, y = current
            # Using 4-directional movement for rectilinear paths
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = x + dx, y + dy

                if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in visited:
                    if self._image[nx][ny] != -1:
                        visited.add((nx, ny))
                        new_path = list(path)
                        new_path.append((nx, ny))
                        queue.append(((nx, ny), new_path))
        return None  # No path found

    def _simplify_path_to_points(self, node_path: list[tuple[int, int]]) -> list[Point]:
        """
        Converts a list of nodes (e.g., from BFS) into a simplified list of
        Points, keeping only the start, end, and corner points.
        """
        if len(node_path) < 2:
            return [Point(n[0], n[1]) for n in node_path]

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

    def _create_shapes_from_ordered_nodes(
        self, ordered_nodes: list[tuple[int, int]], image_graph: dict
    ) -> list[Shape]:
        """
        Builds a list of Rect and Path shapes from an ordered list of nodes.
        Inserts rectilinear Path objects to connect non-neighboring nodes.
        """
        if not ordered_nodes:
            return []

        shapes = []
        for i in range(len(ordered_nodes) - 1):
            current_node = ordered_nodes[i]
            next_node = ordered_nodes[i + 1]

            # Add the rect for the current node
            shapes.append(Rect(current_node[0], current_node[1]))

            # Check if the next node is a neighbor. If not, add a path.
            if next_node not in image_graph.get(current_node, []):
                path_nodes = self._find_shortest_pixel_path(current_node, next_node)

                if path_nodes:
                    # The path from BFS includes the start and end nodes.
                    # We want the Path object to represent the full connection.
                    simplified_points = self._simplify_path_to_points(path_nodes)
                    shapes.append(Path(simplified_points))
                else:
                    # Fallback for safety, e.g. if islands are separated by transparency
                    x1, y1 = current_node
                    x2, y2 = next_node
                    p1 = Point(x1, y1)
                    p2 = Point(x2, y2)

                    # Create a rectilinear path (only horizontal/vertical segments).
                    if x1 == x2 or y1 == y2:
                        shapes.append(Path([p1, p2]))
                    else:
                        p_intermediate = Point(x2, y1)
                        shapes.append(Path([p1, p_intermediate, p2]))

        # Add the last rect
        shapes.append(Rect(ordered_nodes[-1][0], ordered_nodes[-1][1]))
        return shapes

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

        ordered_nodes = self._get_ordered_nodes_for_color(image_graph)
        if not ordered_nodes:
            return

        shapes = self._create_shapes_from_ordered_nodes(ordered_nodes, image_graph)

        partition = Partition(shapes, name, color_str)
        partition_uuid = str(uuid.uuid4())
        self._partitions[partition_uuid] = partition

    def _get_starting_node(self, G):
        node = _get_node_with_one_neighbor(G)
        if node is None:
            node = _get_top_left_node(G)
        assert node is not None
        return node

    def _create_color_graph(self, width, height) -> dict:
        # Creates a dictionary of key=color, value=dict of nodes and its edges
        # Each color is a list of nodes
        d = {}
        directions = ["NW", "N", "NE", "E", "SE", "S", "SW", "W"]

        for x in range(width):
            for y in range(height):
                if self._image[x][y] == -1:
                    continue
                color = self._image[x][y]
                if color not in d:
                    d[color] = {}
                neighbors = []
                for direction in directions:
                    offset = self.OFFSETS[direction]
                    new_x = x + offset[0]
                    new_y = y + offset[1]
                    if new_x < 0 or new_x >= width or new_y < 0 or new_y >= height:
                        continue
                    new_color = self._image[new_x][new_y]
                    if new_color != color:
                        continue
                    neighbors.append((new_x, new_y))
                d[color][(x, y)] = neighbors
        return d

    @property
    def conf(self):
        return self._conf

    @property
    def partitions(self) -> dict[str, Partition]:
        return self._partitions
