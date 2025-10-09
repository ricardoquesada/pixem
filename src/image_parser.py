# Pixem
# Copyright 2024 - Ricardo Quesada

import logging
import sys
import uuid

import networkx as nx
from coloraide import Color
from PySide6.QtGui import QColor, QImage

from partition import Partition
from shape import Path, Point, Rect, Shape

logger = logging.getLogger(__name__)


def _get_node_with_one_neighbor(G):
    """
    Finds a node in the graph with exactly one neighbor (a leaf node).

    This is useful for finding a natural starting or ending point for a path
    traversal in a graph that is not a cycle.

    Args:
        G: A networkx.Graph object.

    Returns:
        The first node found with a degree of 1, or None if no such node exists.
    """
    return next((node for node, degree in G.degree() if degree == 1), None)


def _get_top_left_node(G):
    """
    Finds the node in the graph that is closest to the (0,0) origin.

    This serves as a deterministic starting point for graph traversal when
    no other obvious starting node (like a leaf node) is available.

    Args:
        G: A networkx.Graph object.

    Returns:
        The node (tuple of x, y) closest to the origin.
    """
    curr_node = None
    curr_dist = float("inf")
    for node in G.nodes():
        x, y = node
        d = x * x + y * y
        if d < curr_dist:
            curr_dist = d
            curr_node = node
    return curr_node


def _find_closest_node(target_node, candidate_nodes):
    """Finds the node in candidate_nodes with the shortest rectilinear distance to target_node."""
    closest_node = None
    min_dist = float("inf")
    tx, ty = target_node
    for node in candidate_nodes:
        nx, ny = node
        dist = abs(tx - nx) + abs(ty - ny)
        if dist < min_dist:
            min_dist = dist
            closest_node = node
    return closest_node


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

    def __init__(self, image: QImage):
        """
        Initializes the ImageParser and processes the given image.

        Args:
            image: The QImage to be parsed.
        """
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

    def _put_pixels_in_matrix(self, img: QImage, width: int, height: int):
        """
        Populates an internal 2D list with pixel color data from the QImage.

        Transparent pixels are marked as -1.

        Args:
            img: The source QImage.
            width: The width of the image.
            height: The height of the image.
        """
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
        Orders all nodes of a color by traversing connected components.
        After traversing a component, it jumps to the closest unvisited node
        to continue the traversal, ensuring a geometrically optimized path.

        Args:
            image_graph: An adjacency list representation of the graph for a single color.

        Returns:
            A list of all nodes (pixels) for the color, in a single traversal order.
        """
        unvisited_nodes = set(image_graph.keys())
        if not unvisited_nodes:
            return []

        ordered_nodes = []
        last_node = None

        while unvisited_nodes:
            # If this is the first component, start with the top-leftmost node.
            # Otherwise, start with the node closest to the end of the last component.
            if last_node is None:
                start_node = min(unvisited_nodes, key=lambda p: p[0] * p[0] + p[1] * p[1])
            else:
                start_node = _find_closest_node(last_node, unvisited_nodes)

            # Perform DFS for the current component starting from start_node.
            stack = [start_node]
            component_nodes_in_dfs_order = []

            while stack:
                node_to_visit = stack.pop()
                if node_to_visit in unvisited_nodes:
                    unvisited_nodes.remove(node_to_visit)
                    component_nodes_in_dfs_order.append(node_to_visit)

                    # Add unvisited neighbors to the stack.
                    # Sorting neighbors makes the traversal deterministic.
                    neighbors = sorted(image_graph.get(node_to_visit, []), reverse=True)
                    for neighbor in neighbors:
                        if neighbor in unvisited_nodes:
                            stack.append(neighbor)

            ordered_nodes.extend(component_nodes_in_dfs_order)
            if component_nodes_in_dfs_order:
                last_node = component_nodes_in_dfs_order[-1]

        return ordered_nodes

    def _get_vertex_graph_for_color(self, color: int) -> nx.Graph:
        """
        Builds and caches a networkx.Graph of all valid path vertices.

        The nodes of the graph are the vertices of the pixel grid. An edge
        is created between two vertices if the path segment between them is
        "valid" — meaning it runs alongside at least one non-transparent pixel.
        """

        def is_solid(px: int, py: int) -> bool:
            if 0 <= px < w_pixel and 0 <= py < h_pixel:
                return self._image[px][py] != -1
            return False

        def get_weight(px: int, py: int) -> int:
            if not (0 <= px < w_pixel and 0 <= py < h_pixel):
                return sys.maxsize

            px_color_val = self._image[px][py]
            if px_color_val == -1:
                return sys.maxsize

            # Target color for the path
            color1 = Color(f"#{color:06x}")

            # Color of the pixel we are evaluating
            color2 = Color(f"#{px_color_val:06x}")

            # Calculate the perceptual color difference using CIEDE2000
            delta_e = color1.delta_e(color2, method="2000")

            # The weight should be low for similar colors (low delta_e) and high for different ones.
            # Using a quadratic function penalizes paths over dissimilar colors more heavily.
            w = 1 + 0.1 * (delta_e**2)
            return int(w)

        if color in self._vertex_graph:
            return self._vertex_graph[color]

        G = nx.Graph()
        w_pixel, h_pixel = len(self._image), len(self._image[0])
        w_vertex, h_vertex = w_pixel + 1, h_pixel + 1

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
        Finds the shortest rectilinear path between two vertices on the pixel grid.

        This method leverages a pre-built graph of all valid path segments for a
        given color, where edge weights are determined by the color difference
        of adjacent pixels. It uses Dijkstra's algorithm (via networkx) to find
        the path with the minimum total weight.

        This is used to create jump stitches between disconnected areas of the
        same color.

        Args:
            color: The target color for the path. The path will try to follow
                   pixels of this color.
            start_node: The starting vertex (x, y).
            end_node: The ending vertex (x, y).

        Returns:
            A list of vertices representing the shortest path, or None if no
            path exists.
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

    def _remove_redundant_points_from_start_and_end_nodes(
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
            return node_path

        return node_path[start_idx : end_idx + 1]

    def _simplify_path_to_points(self, node_path: list[tuple[int, int]]) -> list[Point]:
        """
        Converts a list of path vertices into a simplified list of Points.

        It simplifies the path by keeping only the start, end, and corner
        points, effectively removing redundant collinear points.

        Args:
            node_path: A list of (x, y) tuples representing the vertices of a path.

        Returns:
            A simplified list of Point objects.
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
                    path_nodes = self._remove_redundant_points_from_start_and_end_nodes(path_nodes)
                    simplified_points = self._simplify_path_to_points(path_nodes)
                    shapes.append(Path(simplified_points))
                else:
                    # If no path is found (e.g., islands separated by transparency),
                    # we currently do not connect them.
                    logger.info(f"Could not find a path to connect {current_node} and {next_node}")

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
    def partitions(self) -> dict[str, Partition]:
        return self._partitions
