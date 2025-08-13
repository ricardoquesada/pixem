# Pixem
# Copyright 2024 - Ricardo Quesada

import logging
import sys
import uuid

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

    def __init__(self, image: QImage):
        width, height = image.width(), image.height()

        self._jump_stitches = 0
        self._image = [[-1 for _ in range(height)] for _ in range(width)]

        # One graph per color, since weights changes from color to color
        self._vertex_graph = {}
        self._partitions = {}

        # Put all pixels in matrix
        self._put_pixels_in_matrix(image, width, height)
        # Group the ones that are touching/same-color together
        g = self._create_color_graph(width, height)

        for color in g:
            self._create_single_partition_for_color(g[color], color)

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
                color = argb & 0xFFFFFF
                self._image[x][y] = color

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

    def _get_vertex_graph_for_color(self, color: int) -> nx.Graph:
        """
        Builds and caches a networkx.Graph of all valid path vertices.

        The nodes of the graph are the vertices of the pixel grid. An edge
        is created between two vertices if the path segment between them is
        "valid" — meaning it runs alongside at least one non-transparent pixel.
        """
        if color in self._vertex_graph:
            return self._vertex_graph[color]

        G = nx.Graph()
        w_pixel, h_pixel = len(self._image), len(self._image[0])
        w_vertex, h_vertex = w_pixel + 1, h_pixel + 1

        def is_solid(px: int, py: int) -> bool:
            if 0 <= px < w_pixel and 0 <= py < h_pixel:
                return self._image[px][py] != -1
            return False

        def get_weight(px: int, py: int) -> int:
            if not (0 <= px < w_pixel and 0 <= py < h_pixel):
                return sys.maxsize

            px_color = self._image[px][py]
            r_diff = abs(((px_color >> 16) & 0xFF) - ((color >> 16) & 0xFF))
            g_diff = abs(((px_color >> 8) & 0xFF) - ((color >> 8) & 0xFF))
            b_diff = abs((px_color & 0xFF) - (color & 0xFF))
            total_diff = r_diff + g_diff + b_diff
            # Using a quadratic function for an exponential-like growth. This
            # penalizes paths over dissimilar colors more heavily than a
            # linear function. The factor (0.04) is a tunable parameter
            # that controls the steepness of the curve.
            w = 1 + 0.04 * (total_diff**2)
            return int(w)

        for y in range(h_vertex):
            for x in range(w_vertex):
                # Check for horizontal connection to the right
                if x + 1 < w_vertex:
                    # Path from (x,y) to (x+1,y) is between pixels (x, y-1) and (x, y)
                    if is_solid(x, y - 1) or is_solid(x, y):
                        weight = min(get_weight(x, y - 1), get_weight(x, y))
                        G.add_edge((x, y), (x + 1, y), weight=weight)

                # Check for vertical connection downwards
                if y + 1 < h_vertex:
                    # Path from (x,y) to (x,y+1) is between pixels (x-1, y) and (x, y)
                    if is_solid(x - 1, y) or is_solid(x, y):
                        weight = min(get_weight(x - 1, y), get_weight(x, y))
                        G.add_edge((x, y), (x, y + 1), weight=weight)

        self._vertex_graph[color] = G
        return self._vertex_graph[color]

    def _find_shortest_pixel_path(
        self, color: int, start_node: tuple[int, int], end_node: tuple[int, int]
    ) -> list[tuple[int, int]] | None:
        """
        Finds the shortest rectilinear path between two vertices on the pixel grid
        by leveraging a pre-built graph of all valid path segments.
        """
        G = self._get_vertex_graph_for_color(color)
        try:
            # Check if nodes exist in graph to prevent NetworkXError
            if start_node not in G or end_node not in G:
                logger.warning(
                    f"Start or end node not in vertex graph. Start: {start_node}, End: {end_node}"
                )
                return None
            return nx.shortest_path(G, source=start_node, target=end_node, weight="weight")
        except nx.NetworkXNoPath:
            # Probably an island
            logger.info(f"No path found between {start_node} and {end_node}")
            return None

    def _simplify_path_to_points(self, node_path: list[tuple[int, int]]) -> list[Point]:
        """
        Converts a list of nodes (e.g., from BFS) into a simplified list of
        Points, keeping only the start, end, and corner points. It also
        verifies that each point in the path corresponds to a non-transparent
        pixel (an "existing rect" in the image).
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

    def _create_shapes_from_ordered_nodes(
        self, color: int, ordered_nodes: list[tuple[int, int]], image_graph: dict
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
                path_nodes = self._find_shortest_pixel_path(color, current_node, next_node)

                if path_nodes:
                    # The path from BFS includes the start and end nodes.
                    simplified_points = self._simplify_path_to_points(path_nodes)
                    shapes.append(Path(simplified_points))
                else:
                    # TODO: Think if we want to connect island. Probably not
                    if False:
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

        shapes = self._create_shapes_from_ordered_nodes(color, ordered_nodes, image_graph)

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
