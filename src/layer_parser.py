# Pixem
# Copyright 2024 - Ricardo Quesada
import os.path

from PIL import Image
import argparse
import json
import matplotlib.pyplot as plt
import networkx as nx
import toml

# Argument Defaults
DEFAULT_ASPECT_RATIO = "pal"
DEFAULT_FILL_MODE = "satin_s"
DEFAULT_HOOP_SIZE_IN = (5, 7)
DEFAULT_PIXEL_SIZE_MM = 2.65
DEFAULT_ROTATION = 0
DEFAULT_SAW_THRESHOLD = 40

# Conf dictionary Keys
KEY_ASPECT_RATIO = "aspect_ratio"
KEY_FILL_MODE = "fill_mode"
KEY_GROUPS = "groups"
KEY_HOOP_SIZE_IN = "hoop_size"
KEY_INPUT_PNG_FILENAME = "input_png_filename"
KEY_INPUT_PNG_SIZE = "input_png_size"
KEY_NODES_JUMP_STITCHES = "nodes_jump_stitches"
KEY_NODES_PATH = "nodes_path"
KEY_NODES_PATH_SIZE = "nodes_path_size"
KEY_PIXEL_SIZE_MM = "pixel_size"
KEY_ROTATION = "rotation"
KEY_SAW_THRESHOLD = "saw_threshold"
KEY_STARTING_NODE = "starting_node"

INCHES_TO_MM = 25.4


def visualize_tsp(graph):
    nodes = graph.keys()
    edges = []
    for i in graph:
        for j in graph[i]:
            edges.append((i, j))

    G = nx.Graph()
    nx.kamada_kawai_layout(G)
    G.add_nodes_from(nodes)
    G.add_edges_from(edges)

    # Draw the graph
    nx.draw(
        G,
        with_labels=True,
        node_color="skyblue",
        node_size=1500,
        font_size=10,
        font_color="black",
        edge_color="gray",
        width=2,
    )
    plt.show()


def get_node_with_one_neighbor(G):
    # Returns the first node that has a degree of 1
    nodes_with_one_neighbor = [node for node, degree in G.degree() if degree == 1]
    if len(nodes_with_one_neighbor) > 0:
        return nodes_with_one_neighbor[0]
    return None


def get_top_left_node(G):
    curr_node = None
    curr_dist = 1000000
    for node in G.nodes():
        x, y = node
        d = x * x + y * y
        if d < curr_dist:
            curr_dist = d
            curr_node = node
    return curr_node


def iterative_dfs(G, start_node):
    visited = set()
    stack = [start_node]
    ret = []

    while stack:
        node = stack.pop()
        if node not in visited:
            visited.add(node)
            ret.append(node)
            for neighbor in G.neighbors(node):
                stack.append(neighbor)
    return ret


def saw_with_backtracking(G, node, path, longest_path):
    """
    Generates a self-avoiding walk (SAW) in a 2D lattice with holes using backtracking.

    Args:
      G: The graph
      node: The current node of the walk.
      path: The current path of the walk.
      longest_path: longest path so far

    Returns:
      A list of nodes representing the SAW, or None if no valid walk exists.
    """

    if path is None:
        path = [node]

    if len(path) == len(G.nodes):
        return path, longest_path

    possible_nodes = G.neighbors(node)
    for next_node in possible_nodes:
        if next_node not in path:
            path.append(next_node)  # Try this node
            if len(path) > len(longest_path):
                longest_path = path
            new_path, new_longest_path = saw_with_backtracking(G, next_node, path, longest_path)
            if new_path:
                return new_path, new_longest_path  # Found a solution
            path.pop()  # Backtrack: remove the last move

    return None, longest_path  # No valid path found from this point


def rotate_left_list(lst, n):
    """Rotates a list by n positions to the left.

    Args:
        lst: The list to rotate.
        n: The number of positions to rotate.

    Returns:
        The rotated list.
    """
    n = n % len(lst)
    return lst[n:] + lst[:n]


def find_jump_stitches(nodes):
    jump_stitches = 0
    if len(nodes) > 1:
        prev = nodes[0]
        for node in nodes[1:]:
            if (abs(prev[0] - node[0]) > 1) or (abs(prev[1] - node[1]) > 1):
                jump_stitches = jump_stitches + 1
            prev = node
    return jump_stitches


class PixelToSVG:
    VERSION = "0.1"
    # Pixels are not square in PAL:
    # https://hitmen.c02.at/temp/palstuff/
    # Aspect ratio: 0,936:1
    ASPECT_RATIO = {
        "square": 1.0,
        "pal": 0.936,
        "ntsc": 0.750,
    }

    FILL_PARAMS = {
        "autofill": {
            "fillmode": "auto_fill",
            "max_stitch_len": 2.5,
        },
        "satin_s": {
            "fillmode": "auto_fill",
            "max_stitch_len": 1000,
        },
        "legacy": {
            "fillmode": "legacy_fill",
            "max_stitch_len": 2.5,
        },
    }

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

    def __init__(
        self,
        input_png,
        hoop_size,
        pixel_size,
        aspect_ratio,
        fill_mode,
        rotation,
        saw_threshold,
        configuration_filename,
    ):
        """
        Creates an SVG file from a PNG image, representing each pixel as a rectangle.

        Args:
            input_png: The path to the PNG image.
            hoop_size: Tuple that defines the hoop size in inches.
            pixel_size: Represents the pixel size in mm.
            aspect_ratio: Pixel aspect ratio
            fill_mode: Fill mode to use
        """

        try:
            img = Image.open(input_png)
        except FileNotFoundError as e:
            print(f"Error: Image file not found at {input_png}")
            raise e
        except Exception as e:
            print(f"An error occurred: {e}")
            raise e

        img = img.convert("RGBA")
        width, height = img.size

        self._jump_stitches = 0
        self._image = [[-1 for _ in range(height)] for _ in range(width)]

        # key: color
        # value: lists of neighboring pixels
        self._pixel_groups = {}

        self._conf = {KEY_GROUPS: {}}
        self._input_png_filename = input_png

        if configuration_filename is not None:
            self.validate_configuration_filename(configuration_filename)

        args = [
            (rotation, KEY_ROTATION, DEFAULT_ROTATION),
            (pixel_size, KEY_PIXEL_SIZE_MM, DEFAULT_PIXEL_SIZE_MM),
            (hoop_size, KEY_HOOP_SIZE_IN, DEFAULT_HOOP_SIZE_IN),
            (saw_threshold, KEY_SAW_THRESHOLD, DEFAULT_SAW_THRESHOLD),
            (fill_mode, KEY_FILL_MODE, DEFAULT_FILL_MODE),
            (aspect_ratio, KEY_ASPECT_RATIO, DEFAULT_ASPECT_RATIO),
        ]
        for arg in args:
            self.set_conf_value(arg[0], arg[1], arg[2])

        self._conf[KEY_INPUT_PNG_FILENAME] = input_png
        self._conf[KEY_INPUT_PNG_SIZE] = (width, height)

        # Backward compatible
        self._fill_mode = self.FILL_PARAMS[self._conf[KEY_FILL_MODE]]
        self._aspect_ratio = 1.0 / self.ASPECT_RATIO[self._conf[KEY_ASPECT_RATIO]]
        self._pixel_size = self._conf[KEY_PIXEL_SIZE_MM]
        self._hoop_size = self._conf[KEY_HOOP_SIZE_IN]
        self._rotation = self._conf[KEY_ROTATION]
        self._saw_threshold = self._conf[KEY_SAW_THRESHOLD]

        # Put all pixels in matrix
        self.put_pixels_in_matrix(img, width, height)
        # Group the ones that are touching/same-color together
        g = self.create_color_graph(width, height)

        solution = {}
        for color in g:
            subgraph = self.create_solution_graph(g[color], color)
            solution[color] = subgraph
        self._pixel_groups = solution
        self.find_all_jump_stitches()

    def set_conf_value(self, arg_value, key, default):
        # Priority:
        #   1. argument
        #   2. conf
        #   3. default
        if arg_value is not None:
            self._conf[key] = arg_value

        if key not in self._conf or self._conf[key] is None:
            self._conf[key] = default

    def validate_configuration_filename(self, filename):
        # Don't catch the exception, propagate it.
        with open(filename, "r") as f:
            self._conf = json.load(f)

    def put_pixels_in_matrix(self, img, width, height):
        # Put all pixels in matrix
        for y in range(height):
            for x in range(width):
                r, g, b, a = img.getpixel((x, y))
                if a != 255:
                    # Skip transparent pixels
                    continue
                color = (r << 16) + (g << 8) + b
                color = "#" + format(color, "06x")
                self._image[x][y] = color

    def find_all_jump_stitches(self):
        # print number of jump stitches
        jump_stitches = 0
        for color in self._pixel_groups:
            # each color is a jump stitch
            # jump_stitches = jump_stitches + 1
            for nodes in self._pixel_groups[color]:
                # each group of neighbors has a jump stitch
                # jump_stitches = jump_stitches + 1
                jump_stitches = jump_stitches + find_jump_stitches(nodes)
        print(f"Jump stitches: {jump_stitches}")
        self._jump_stitches = jump_stitches

    def create_solution_graph(self, image_graph, color):
        # image_graph is a dict of:
        #   key: node
        #   value: edges
        # visualize_tsp(image_graph)
        nodes = image_graph.keys()
        edges = []
        for node in image_graph:
            for edge in image_graph[node]:
                edges.append((node, edge))

        G = nx.Graph()
        G.add_nodes_from(nodes)
        G.add_edges_from(edges)

        # List of lists
        ret = []

        # The graph might include disconnected nodes, identify them
        # and process each subgraph independently
        S = [G.subgraph(c).copy() for c in nx.connected_components(G)]
        for idx, s in enumerate(S):
            # nx.draw(s, with_labels=True)
            # plt.show()
            nodes = list(s.nodes())

            key = f"{color}_{idx}"
            if key not in self._conf[KEY_GROUPS]:
                self._conf[KEY_GROUPS][key] = {}

            if len(nodes) > 1:
                start_node = self.get_starting_node(s, key)
                if len(s.nodes) < self._saw_threshold:
                    path = None
                    longest_path = []
                    print(f", trying SAW ({len(s.nodes)})", end="")
                    path, longest_path = saw_with_backtracking(s, start_node, path, longest_path)
                    nodes = path
                    if nodes is not None:
                        print("")
                if nodes is None or len(s.nodes) >= self._saw_threshold:
                    print(f", trying DFS ({len(s.nodes)})")
                    nodes = iterative_dfs(s, start_node)
            self._conf[KEY_GROUPS][key][KEY_NODES_PATH] = nodes
            self._conf[KEY_GROUPS][key][KEY_NODES_PATH_SIZE] = len(nodes)
            jump_stitches = find_jump_stitches(nodes)
            self._conf[KEY_GROUPS][key][KEY_NODES_JUMP_STITCHES] = jump_stitches
            print(f"Jump stitches: {jump_stitches} / {len(nodes)}")
            ret.append(nodes)
        return ret

    def get_starting_node(self, G, key):
        print(f"Processing key: {key}:")
        node = None
        if KEY_STARTING_NODE in self._conf[KEY_GROUPS][key]:
            node = self._conf[key][KEY_STARTING_NODE]
            # Returns a list. Convert it to tuple.
            node = tuple(node)
        if node is None:
            node = get_node_with_one_neighbor(G)
        if node is None:
            node = get_top_left_node(G)
        assert node is not None
        print(f"  Starting node: {node}")
        return node

    def create_color_graph(self, width, height):
        # Creates a dictionary of key=color, value=dict of nodes and its edges
        # Each color is a list of nodes
        d = {}
        directions = ["NW", "N", "NE", "E", "SE", "S", "SW", "W"]
        directions = rotate_left_list(directions, abs(self._rotation))
        if self._rotation < 0:
            directions = directions[::-1]

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

    def write_rect_svg(self, file, x, y, pixel_size, color, angle):
        fill_method = self._fill_mode["fillmode"]
        max_stitch_len = self._fill_mode["max_stitch_len"]
        file.write(
            f'<rect x="{x * pixel_size}" y="{y * pixel_size}" '
            f'width="{pixel_size}" height="{pixel_size}" '
            f'fill="{color}" '
            f'id="pixel_{x}_{y}_{angle}" '
            f'style="display:inline;stroke:none" '
            f'inkstitch:fill_method="{fill_method}" '
            f'inkstitch:angle="{angle}" '
            f'inkstitch:max_stitch_length_mm="{max_stitch_len}" '
            "/>\n"
        )

    def write_conf(self):
        filename = os.path.basename(self._input_png_filename)
        filename_no_ext = os.path.splitext(filename)[0]
        conf_filename = os.path.join("conf", f"{filename_no_ext}.toml")
        with open(conf_filename, "w") as output_file:
            # json.dump(self._conf, output_file, indent=4)
            toml.dump(self._conf, output_file)

    def write_to_svg(self, output_path):
        with open(output_path, "w") as f:
            f.write('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n')
            f.write(
                f"<svg\n"
                f'  width="{round(self._hoop_size[0] * INCHES_TO_MM)}mm"\n'
                f'  height="{round(self._hoop_size[1] * INCHES_TO_MM)}mm"\n'
                f'  viewBox="0 0 {round(self._hoop_size[0] * INCHES_TO_MM)}'
                f' {round(self._hoop_size[1] * INCHES_TO_MM)}"\n'
                f'  version="1.1"\n'
                f'  id="{output_path}"\n'
                f'  xmlns="http://www.w3.org/2000/svg"\n'
                f'  xmlns:svg="http://www.w3.org/2000/svg"\n'
                f'  xmlns:inkstitch="http://inkstitch.org/namespace"\n'
                ">\n"
            )
            f.write(
                "<sodipodi:namedview\n"
                '  inkscape:document-units="mm"\n'
                '  inkscape:pagecheckerboard="true"\n'
                '  showgrid="true"\n'
                ">\n"
            )
            f.write(
                "<inkscape:grid\n"
                '  id="grid1"\n'
                '  units="mm"\n'
                '  originx="0"\n'
                '  originy="0"\n'
                f'  spacingx="{self._pixel_size}"\n'
                f'  spacingy="{self._pixel_size * self._aspect_ratio}"\n'
                '  enabled="true"\n'
                '  visible="true"\n'
                "/>\n"
            )
            f.write("</sodipodi:namedview>\n")
            f.write("<defs\n" '  id="defs1"\n' "/>\n")
            f.write(
                "<!-- pixem:params\n"
                f'  pixel_size="{self._pixel_size}"\n'
                f'  hoop_size="{self._hoop_size}"\n'
                f'  aspect_ratio="{self._aspect_ratio}"\n'
                f'  fill_mode="{self._fill_mode}"\n'
                f'  version="{self.VERSION}"\n'
                "-->\n"
            )

            f.write(f'<g id="image" transform="scale(1, {self._aspect_ratio})">\n')
            for color in self._pixel_groups:
                f.write(f"<!-- color {color} -->\n")

                it = 0
                # Each color is a list of list. Each list is a connected graph.
                for pixels in self._pixel_groups[color]:
                    # pixels is [(1,0), (1,2)], [(3,4), (3,5)]
                    f.write(f'<g id="layer_{color}_{it}" inkscape:label="color_{color}_{it}">\n')
                    for pixel in pixels:
                        # pixel is a tuple (x,y)
                        x, y = pixel
                        angle = 0 if ((x + y) % 2 == 0) else 90
                        self.write_rect_svg(f, x, y, self._pixel_size, color, angle)

                    f.write("</g>\n")
                    it = it + 1
            f.write("</g>\n")
            f.write("</svg>\n")


def main():
    parser = argparse.ArgumentParser(description="Convert a PNG image to an Ink/Stitch SVG file")
    parser.add_argument("input_image", help="Path to the input PNG image.")
    parser.add_argument("output_svg", help="Path to save the output SVG file.")
    parser.add_argument(
        "-s",
        "--hoop_size",
        metavar="WIDTHxHEIGHT",
        help="Hoop size in the format WIDTHxHEIGHT in inches (e.g., 5x7)",
    )
    parser.add_argument("-p", "--pixel_size", metavar="SIZE", type=float, help="Pixel size in mm")
    parser.add_argument(
        "-a",
        "--aspect_ratio",
        type=str,
        choices=["pal", "ntsc", "square"],
        help="Pixel aspect ratio",
    )
    parser.add_argument(
        "-f",
        "--fill_mode",
        type=str,
        choices=["satin_s", "autofill", "legacy"],
        help="Defines the fill mode to use",
    )
    parser.add_argument(
        "-r",
        "--rotation",
        type=int,
        choices=[-8, -7, -6, -5, -4, -3, -2, -1, 0, 1, 2, 3, 4, 5, 6, 7],
        help="Where the first neighbor starts",
    )
    parser.add_argument("-t", "--saw_threshold", type=int, help="Where the first neighbor starts")
    parser.add_argument("-c", "--conf", type=str, help="Configuration file")

    args = parser.parse_args()

    hoop_size = None
    if args.hoop_size is not None:
        x, y = map(int, args.hoop_size.split("x"))
        hoop_size = (x, y)

    print(args)
    tosvg = PixelToSVG(
        args.input_image,
        hoop_size,
        args.pixel_size,
        args.aspect_ratio,
        args.fill_mode,
        args.rotation,
        args.saw_threshold,
        args.conf,
    )
    tosvg.write_conf()
    tosvg.write_to_svg(args.output_svg)


if __name__ == "__main__":
    main()
