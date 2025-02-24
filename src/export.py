# Pixem
# Copyright 2024 - Ricardo Quesada
import argparse
import logging

# Argument Defaults
DEFAULT_ASPECT_RATIO = "pal"
DEFAULT_FILL_MODE = "satin_s"
DEFAULT_HOOP_SIZE_IN = (5, 7)
DEFAULT_PIXEL_SIZE_MM = (2.65, 2.65)

# Conf dictionary Keys
KEY_FILL_MODE = "fill_mode"
KEY_GROUPS = "groups"
KEY_HOOP_SIZE_IN = "hoop_size"
KEY_NODES_PATH = "nodes_path"
KEY_PIXEL_SIZE_MM = "pixel_size"

INCHES_TO_MM = 25.4

logger = logging.getLogger(__name__)  # __name__ gets the current module's name


class ExportToSVG:
    VERSION = "0.1"

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

    def __init__(
        self,
        groups: dict,
        hoop_size: tuple,
        pixel_size: tuple,
        fill_mode: str,
        translate: tuple = (0.0, 0.0),
        scale: tuple = (1.0, 1.0),
        rotation: float = 0,
    ):
        """
        Creates an SVG file from a PNG image, representing each pixel as a rectangle.

        Args:
            hoop_size: Tuple that defines the hoop size in inches.
            pixel_size: Represents the pixel size in mm.
            fill_mode: Fill mode to use
        """

        # key: color
        # value: lists of neighboring pixels
        self._pixel_groups = {}

        self._conf = {KEY_GROUPS: {}}

        args = [
            (pixel_size, KEY_PIXEL_SIZE_MM, DEFAULT_PIXEL_SIZE_MM),
            (hoop_size, KEY_HOOP_SIZE_IN, DEFAULT_HOOP_SIZE_IN),
            (fill_mode, KEY_FILL_MODE, DEFAULT_FILL_MODE),
        ]
        for arg in args:
            self.set_conf_value(arg[0], arg[1], arg[2])

        # Backward compatible
        self._fill_mode = self.FILL_PARAMS[self._conf[KEY_FILL_MODE]]
        self._pixel_size = self._conf[KEY_PIXEL_SIZE_MM]
        self._hoop_size = self._conf[KEY_HOOP_SIZE_IN]

        self._translate = translate
        self._scale = scale
        self._rotation = rotation

        self._pixel_groups = groups

    def set_conf_value(self, arg_value, key, default):
        # Priority:
        #   1. argument
        #   2. conf
        #   3. default
        if arg_value is not None:
            self._conf[key] = arg_value

        if key not in self._conf or self._conf[key] is None:
            self._conf[key] = default

    def write_rect_svg(self, file, x, y, pixel_size, color, angle):
        fill_method = self._fill_mode["fillmode"]
        max_stitch_len = self._fill_mode["max_stitch_len"]
        file.write(
            f'<rect x="{x * pixel_size[0]}" y="{y * pixel_size[1]}" '
            f'width="{pixel_size[0]}" height="{pixel_size[1]}" '
            f'fill="{color}" '
            f'id="pixel_{x}_{y}_{angle}" '
            f'style="display:inline;stroke:none" '
            f'inkstitch:fill_method="{fill_method}" '
            f'inkstitch:angle="{angle}" '
            f'inkstitch:max_stitch_length_mm="{max_stitch_len}" '
            "/>\n"
        )

    def write_to_svg(self, output_path):
        logger.info(f"writing SVG {output_path}")
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
                f'  spacingx="{self._pixel_size[0]}"\n'
                f'  spacingy="{self._pixel_size[1]}"\n'
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
                f'  fill_mode="{self._fill_mode}"\n'
                f'  translate={self._translate}"\n'
                f'  scale={self._scale}"\n'
                f'  rotation={self._rotation}"\n'
                f'  version="{self.VERSION}"\n'
                "-->\n"
            )

            f.write(
                f'<g id="image" transform="translate({self._translate[0]} {self._translate[1]}) rotate({self._rotation }) scale({self._scale[0]} {self._scale[1]})">\n'
            )

            for color in self._pixel_groups:
                # Each color is a list of list. Each list is a connected graph.
                pixels = self._pixel_groups[color][KEY_NODES_PATH]
                f.write(f'<g id="layer_{color}" inkscape:label="color_{color}">\n')
                for pixel in pixels:
                    # pixel is a tuple (x,y)
                    x, y = pixel
                    angle = 0 if ((x + y) % 2 == 0) else 90
                    self.write_rect_svg(f, x, y, self._pixel_size, color, angle)

                f.write("</g>\n")
            f.write("</svg>\n")


def main():
    parser = argparse.ArgumentParser(description="Convert a PNG image to an Ink/Stitch SVG file")
    parser.add_argument("output_svg", help="Path to save the output SVG file.")
    parser.add_argument(
        "-s",
        "--hoop_size",
        metavar="WIDTHxHEIGHT",
        help="Hoop size in the format WIDTHxHEIGHT in inches (e.g., 5x7)",
    )
    parser.add_argument(
        "-p", "--pixel_size", metavar="WIDTHxHEIGHT", help="Pixel size in mm (e.g., 3.25x3.25"
    )
    parser.add_argument(
        "-f",
        "--fill_mode",
        type=str,
        choices=["satin_s", "autofill", "legacy"],
        help="Defines the fill mode to use",
    )

    args = parser.parse_args()

    hoop_size = None
    if args.hoop_size is not None:
        x, y = map(int, args.hoop_size.split("x"))
        hoop_size = (x, y)

    pixel_size = None
    if args.pixel_size is not None:
        x, y = map(float, args.hoop_size.split("x"))
        pixel_size = (x, y)

    print(args)
    tosvg = ExportToSVG(
        hoop_size,
        pixel_size,
        args.fill_mode,
    )
    tosvg.write_to_svg(args.output_svg)


if __name__ == "__main__":
    main()
