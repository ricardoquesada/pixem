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

        self._sort_partitions_by_lightness()

    def _sort_partitions_by_lightness(self):
        sorted_keys = sorted(
            self._partitions.keys(), key=lambda p: Color(self._partitions[p].color).get("oklab.l")
        )
        new_dict = {}
        for key in sorted_keys:
            new_dict[key] = self._partitions[key]
        self._partitions = new_dict

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

    def _get_vertex_graph_for_color(self, color: int, use_weights: bool) -> nx.Graph:
        """
        Builds and caches a networkx.Graph of all valid path vertices.

        The nodes of the graph are the vertices of the pixel grid. An edge
        is created between two vertices if the path segment between them is
        "valid" — meaning it runs alongside at least one non-transparent pixel.

        If use_weights is True, edge weights are determined by the color
        difference of adjacent pixels. Otherwise, all edges have a weight of 1.
        """

        def is_solid(px: int, py: int) -> bool:
            if 0 <= px < w_pixel and 0 <= py < h_pixel:
                return self._image[px][py] != -1
            return False

        def get_weight(px: int, py: int) -> int:
            if not use_weights:
                return 1

            if not (0 <= px < w_pixel and 0 <= py < h_pixel):
                return sys.maxsize

            px_color_val = self._image[px][py]
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
        w_pixel, h_pixel = len(self._image), len(self._image[0])
        w_vertex, h_vertex = w_pixel + 1, h_pixel + 1

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

    def _find_shortest_pixel_path(
        self, color: int, start_node: tuple[int, int], end_node: tuple[int, int], use_weights: bool
    ) -> list[tuple[int, int]] | None:
        """
        Finds the shortest path between two vertices on the pixel grid.

        If use_weights is True, it finds the path with the minimum total weight
        (using Dijkstra), considering color differences. If False, it finds the
        path with the fewest segments (using BFS).

        Args:
            color: The target color for the path.
            start_node: The starting vertex (x, y).
            end_node: The ending vertex (x, y).
            use_weights: Whether to use color-based weights in pathfinding.

        Returns:
            A list of vertices representing the shortest path, or None.
        """
        G = self._get_vertex_graph_for_color(color, use_weights)
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

    def _generate_shapes_for_color(self, color: int, image_graph: dict) -> list[Shape]:
        """
        Generates an optimized list of shapes for a single color by processing
        disconnected blocks (components) intelligently.

        The algorithm is as follows:
        1. Identify all disconnected blocks of pixels for the given color.
        2. Start with the block containing the top-left-most pixel.
        3. Traverse the current block using a greedy nearest-neighbor approach,
           creating Paths for any non-adjacent moves within the block.
        4. Once the block is complete, find the last stitched pixel.
        5. For each remaining block, find the color-weighted shortest path from
           the last stitched pixel to the block's closest pixel.
        6. Choose the block whose path has the fewest *segments*, create a Path
           shape for that jump.
        7. Make that block the current one and repeat from step 3 until all blocks
           are processed.
        """
        if not image_graph:
            return []

        # 1. Identify all disconnected blocks
        G = nx.Graph(image_graph)
        blocks = list(nx.connected_components(G))
        if not blocks:
            return []

        shapes = []

        # 2. Determine starting block
        top_left_pixel = min(G.nodes, key=lambda p: p[0] ** 2 + p[1] ** 2)
        start_block_idx = -1
        for i, block in enumerate(blocks):
            if top_left_pixel in block:
                start_block_idx = i
                break

        current_block_set = blocks.pop(start_block_idx)
        entry_pixel = top_left_pixel
        last_stitched_pixel = None

        # 3. Loop until all blocks are processed
        while current_block_set:
            # --- TRAVERSE WITHIN BLOCK ---
            unstitched_in_block = set(current_block_set)
            pixel_to_stitch = entry_pixel

            while unstitched_in_block:
                shapes.append(Rect(pixel_to_stitch[0], pixel_to_stitch[1]))
                unstitched_in_block.remove(pixel_to_stitch)
                last_stitched_pixel = pixel_to_stitch

                # Find next pixel: prefer direct neighbors
                next_pixel_in_block = None
                neighbors = sorted(image_graph.get(pixel_to_stitch, []), reverse=True)
                for neighbor in neighbors:
                    if neighbor in unstitched_in_block:
                        next_pixel_in_block = neighbor
                        break

                if next_pixel_in_block:
                    # Simple move to neighbor, no path needed
                    pixel_to_stitch = next_pixel_in_block
                elif unstitched_in_block:
                    # No unstitched neighbors, must jump to another part of the same block
                    closest_remaining = _find_closest_node(pixel_to_stitch, unstitched_in_block)

                    path_nodes = self._find_shortest_pixel_path(
                        color, pixel_to_stitch, closest_remaining, use_weights=True
                    )
                    if path_nodes:
                        path_nodes = self._remove_redundant_points_from_start_and_end_nodes(
                            path_nodes
                        )
                        simplified_points = self._simplify_path_to_points(path_nodes)
                        shapes.append(Path(simplified_points))

                    pixel_to_stitch = closest_remaining
                else:
                    # Block is finished
                    break

            # --- JUMP BETWEEN BLOCKS ---
            if not blocks:
                break

            best_path_len = float("inf")
            best_path_nodes = None
            best_target_pixel = None
            best_block_index = -1

            for i, next_block in enumerate(blocks):
                candidate_pixel = _find_closest_node(last_stitched_pixel, next_block)
                path_nodes = self._find_shortest_pixel_path(
                    color, last_stitched_pixel, candidate_pixel, use_weights=True
                )

                if path_nodes and len(path_nodes) < best_path_len:
                    best_path_len = len(path_nodes)
                    best_path_nodes = path_nodes
                    best_target_pixel = candidate_pixel
                    best_block_index = i

            if best_path_nodes:
                path_nodes = self._remove_redundant_points_from_start_and_end_nodes(best_path_nodes)
                simplified_points = self._simplify_path_to_points(path_nodes)
                shapes.append(Path(simplified_points))

                current_block_set = blocks.pop(best_block_index)
                entry_pixel = best_target_pixel
            else:
                logger.error("Could not find a path between any remaining blocks.")
                break

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

        shapes = self._generate_shapes_for_color(color, image_graph)

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
