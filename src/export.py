# Pixem
# Copyright 2024 - Ricardo Quesada

import logging
from dataclasses import asdict, dataclass
from typing import TextIO

INCHES_TO_MM = 25.4

logger = logging.getLogger(__name__)


@dataclass
class ExportParameters:
    filename: str | None
    pull_compensation_mm: float
    max_stitch_length_mm: float
    fill_method: str
    initial_angle_degrees: int


class ExportToSVG:
    VERSION = "0.1"

    def __init__(self, hoop_size: tuple[float, float], export_params: ExportParameters):
        self._export_params = export_params
        self._hoop_size = hoop_size
        logger.info(f"Exporting to SVG {self._export_params}")

        self._layers = []

    def _write_rect_svg(
        self,
        file: TextIO,
        layer_idx: int,
        x: int,
        y: int,
        pixel_size: tuple[int, int],
        color: str,
        angle: int,
    ) -> None:
        file.write(
            f'<rect x="{x * pixel_size[0]}" y="{y * pixel_size[1]}" '
            f'width="{pixel_size[0]}" height="{pixel_size[1]}" '
            f'fill="{color}" '
            f'id="pixel_{layer_idx}_{x}_{y}_{angle}" '
            f'style="display:inline;stroke:none" '
            f'inkstitch:fill_method="{self._export_params.fill_method}" '
            f'inkstitch:angle="{angle}" '
            f'inkstitch:max_stitch_length_mm="{self._export_params.max_stitch_length_mm}" '
            f'inkstitch:pull_compensation_mm="{self._export_params.pull_compensation_mm}" '
            "/>\n"
        )

    def write_to_svg(self):
        logger.info(f"writing SVG {self._export_params.filename}")
        with open(self._export_params.filename, "w") as f:
            f.write('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n')
            f.write(
                f"<svg\n"
                f'  width="{round(self._hoop_size[0] * INCHES_TO_MM)}mm"\n'
                f'  height="{round(self._hoop_size[1] * INCHES_TO_MM)}mm"\n'
                f'  viewBox="0 0 {round(self._hoop_size[0] * INCHES_TO_MM)}'
                f' {round(self._hoop_size[1] * INCHES_TO_MM)}"\n'
                f'  version="1.1"\n'
                f'  id="{self._export_params.fill_method}"\n'
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
                f'  spacingx="{self._layers[0]["pixel_size"][0]}"\n'
                f'  spacingy="{self._layers[0]["pixel_size"][1]}"\n'
                '  enabled="true"\n'
                '  visible="true"\n'
                "/>\n"
            )
            f.write("</sodipodi:namedview>\n")
            f.write("<defs\n" '  id="defs1"\n' "/>\n")
            f.write("<!-- pixem:params\n" f'  {asdict(self._export_params)}"\n' "-->\n")

            for layer_idx, layer in enumerate(self._layers):
                name = layer["name"]
                pixel_size = layer["pixel_size"]
                translate = layer["translate"]
                rotation = layer["rotation"]
                scale = layer["scale"]
                partitions = layer["partitions"]
                f.write(
                    f'<g id="{name}" transform="'
                    f"translate({translate[0]} {translate[1]}) "
                    f"rotate({rotation[0]} {rotation[1]} {rotation[2]}) "
                    f"scale({scale[0]} {scale[1]})"
                    '">\n'
                )

                for partition in partitions:
                    # Each partition is a list of list. Each list is a connected graph.
                    path = partitions[partition].path
                    f.write(f'<g id="partition_{layer_idx}_{partition}">\n')
                    for coord in path:
                        # coord is a tuple (x,y)
                        x, y = coord
                        angle = self._export_params.initial_angle_degrees
                        if (x + y) % 2 == 0:
                            angle += 90
                        color = partition.split("_")[0]
                        self._write_rect_svg(
                            f,
                            layer_idx,
                            x,
                            y,
                            pixel_size,
                            color,
                            angle,
                        )

                    # partition
                    f.write("</g>\n")
                # layer
                f.write("</g>\n")
            f.write("</svg>\n")

    def add_layer(
        self,
        name: str,
        partitions: dict,
        pixel_size: tuple[float, float],
        translate: tuple[float, float],
        scale: tuple,
        rotation: tuple[float, float, float],
    ) -> None:
        entry = {
            "name": name,
            "partitions": partitions,
            "pixel_size": pixel_size,
            "translate": translate,
            "scale": scale,
            "rotation": rotation,
        }
        self._layers.append(entry)
