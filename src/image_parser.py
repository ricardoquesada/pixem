# Pixem
# Copyright 2024 - Ricardo Quesada

import logging
import uuid

import networkx as nx
from coloraide import Color
from PySide6.QtGui import QColor, QImage

from partition import Partition
from path_finder import PathFinder
from shape import Path, Rect, Shape

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
        7. If no reachable blocks are found (islands), "teleport" to the
           geometrically closest island without creating a path.
        8. Make that block the current one and repeat from step 3 until all blocks
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

                    path_nodes = self._path_finder.find_shortest_pixel_path(
                        color, pixel_to_stitch, closest_remaining, use_weights=True
                    )
                    if path_nodes:
                        path_nodes = (
                            self._path_finder.remove_redundant_points_from_start_and_end_nodes(
                                path_nodes
                            )
                        )
                        simplified_points = self._path_finder.simplify_path_to_points(path_nodes)
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
                path_nodes = self._path_finder.find_shortest_pixel_path(
                    color, last_stitched_pixel, candidate_pixel, use_weights=True
                )

                if path_nodes and len(path_nodes) < best_path_len:
                    best_path_len = len(path_nodes)
                    best_path_nodes = path_nodes
                    best_target_pixel = candidate_pixel
                    best_block_index = i

            if best_path_nodes:
                # Case 1: Found a reachable block
                path_nodes = self._path_finder.remove_redundant_points_from_start_and_end_nodes(
                    best_path_nodes
                )
                simplified_points = self._path_finder.simplify_path_to_points(path_nodes)
                shapes.append(Path(simplified_points))

                current_block_set = blocks.pop(best_block_index)
                entry_pixel = best_target_pixel
            else:
                # Case 2: No reachable blocks, must jump to an island
                logger.info(
                    f"No reachable blocks from {last_stitched_pixel}. Finding closest island."
                )
                all_remaining_nodes = {node for block in blocks for node in block}
                closest_island_pixel = _find_closest_node(last_stitched_pixel, all_remaining_nodes)

                island_block_index = -1
                for i, block in enumerate(blocks):
                    if closest_island_pixel in block:
                        island_block_index = i
                        break

                if island_block_index != -1:
                    # No path shape is generated for this "teleport"
                    current_block_set = blocks.pop(island_block_index)
                    entry_pixel = closest_island_pixel
                else:
                    logger.error("Could not find block for closest island pixel. Aborting.")
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
