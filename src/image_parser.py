# Pixem
# Copyright 2024 - Ricardo Quesada

import logging
import uuid

import networkx as nx
from PySide6.QtGui import QColor, QImage

from partition import Partition

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

            partition = Partition(nodes, name, color_str)

            partition_uuid = str(uuid.uuid4())
            if partition_uuid not in self._partitions:
                self._partitions[partition_uuid] = partition

                if len(nodes) > 1:
                    start_node = self._get_starting_node(s)
                    partition.walk_path(Partition.WalkMode.SPIRAL_CW, start_node)

    def _create_single_partition_for_color(self, image_graph: dict, color: int) -> None:
        """
        Create a single partition for the given color
        :param image_graph: a dict that contains the nodes and their edges, but the edges are not used in this function
        :param color: The color of the partition
        :return: None
        """
        name = f"#{color:06x}_0"
        color_str = f"#{color:06x}"
        nodes = list(image_graph.keys())
        partition = Partition(nodes, name, color_str)
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
