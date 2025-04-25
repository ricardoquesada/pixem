# Pixem
# Copyright 2024 - Ricardo Quesada

import logging
import os.path
from dataclasses import asdict
from typing import TextIO

from layer import EmbroideryParameters, Layer

INCHES_TO_MM = 25.4

logger = logging.getLogger(__name__)


class ExportToSvg:
    def __init__(self, filename: str, hoop_size: tuple[float, float]):
        self._export_filename = filename
        self._hoop_size = hoop_size
        logger.info(f"Exporting to SVG {self._export_filename}")

        self._layers: list[Layer] = []

    def _write_rect_svg(
        self,
        file: TextIO,
        layer_idx: int,
        x: int,
        y: int,
        pixel_size: tuple[float, float],
        color: str,
        angle: int,
        embroidery_params: EmbroideryParameters,
    ) -> None:
        file.write(
            f'<rect x="{x * pixel_size[0]}" y="{y * pixel_size[1]}" '
            f'width="{pixel_size[0]}" height="{pixel_size[1]}" '
            f'fill="{color}" '
            f'id="pixel_{layer_idx}_{x}_{y}_{angle}" '
            f'style="display:inline;stroke:none" '
            f'inkstitch:fill_method="{embroidery_params.fill_method}" '
            f'inkstitch:angle="{angle}" '
            f'inkstitch:max_stitch_length_mm="{embroidery_params.max_stitch_length_mm}" '
            f'inkstitch:pull_compensation_mm="{embroidery_params.pull_compensation_mm}" '
            f'inkstitch:fill_underlay="{embroidery_params.fill_underlay}" '
        )
        # To be backward compatible. Not sure what is the default one when the parameter is not defined.
        if embroidery_params.min_jump_stitch_length_mm > 0.0:
            file.write(
                f'inkstitch:min_jump_stitch_length_mm="{embroidery_params.min_jump_stitch_length_mm}" '
            )
        file.write("/>\n")

    def write_to_svg(self):
        logger.info(f"writing SVG {self._export_filename}")
        with open(self._export_filename, "w") as f:
            f.write('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n')
            f.write(
                f"<svg\n"
                f'  width="{round(self._hoop_size[0] * INCHES_TO_MM)}mm"\n'
                f'  height="{round(self._hoop_size[1] * INCHES_TO_MM)}mm"\n'
                f'  viewBox="0 0 {round(self._hoop_size[0] * INCHES_TO_MM)}'
                f' {round(self._hoop_size[1] * INCHES_TO_MM)}"\n'
                f'  version="1.1"\n'
                f'  id="svg8"\n'
                f'  xmlns="http://www.w3.org/2000/svg"\n'
                f'  xmlns:svg="http://www.w3.org/2000/svg"\n'
                f'  xmlns:inkstitch="http://inkstitch.org/namespace"\n'
                ">\n"
            )
            f.write(f'<title id="title1023">{os.path.basename(self._export_filename)}</title>\n')
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
                f'  spacingx="{self._layers[0].properties.pixel_size[0]}"\n'
                f'  spacingy="{self._layers[0].properties.pixel_size[1]}"\n'
                '  enabled="true"\n'
                '  visible="true"\n'
                "/>\n"
            )
            f.write("</sodipodi:namedview>\n")
            f.write("<defs\n" '  id="defs1"\n' "/>\n")

            for layer_idx, layer in enumerate(self._layers):
                f.write(f"<!--  layer uuid: {layer.uuid}, name: {layer.name} -->\n")
                f.write(
                    "<!-- layer embroidery params\n"
                    f'  {asdict(layer.embroidery_params)}"\n'
                    "-->\n"
                )
                name = layer.name
                pixel_size = layer.properties.pixel_size
                translate = layer.properties.position
                rotation = layer.properties.rotation
                rotation_anchor_x = layer.image.width() * pixel_size[0] / 2
                rotation_anchor_y = layer.image.height() * pixel_size[1] / 2
                partitions = layer.partitions
                f.write(
                    f'<g id="{name}" transform="'
                    f"translate({translate[0]} {translate[1]}) "
                    f"rotate({rotation} {rotation_anchor_x} {rotation_anchor_y}) "
                    "scale(1 1)"
                    '">\n'
                )

                for partition_key in partitions:
                    # Each partition is a list of list. Each list is a connected graph.
                    partition = partitions[partition_key]
                    path = partition.path
                    color = partition.color
                    part_id = f"partition_{layer_idx}_{partition.name}"
                    part_id = part_id.replace("#", "")
                    f.write(f'<g id="{part_id}">\n')
                    for coord in path:
                        # coord is a tuple (x,y)
                        x, y = coord
                        if (x + y) % 2 == 0:
                            angle = layer.embroidery_params.even_pixel_angle_degrees
                        else:
                            angle = layer.embroidery_params.odd_pixel_angle_degrees
                        self._write_rect_svg(
                            f,
                            layer_idx,
                            x,
                            y,
                            pixel_size,
                            color,
                            angle,
                            layer.embroidery_params,
                        )

                    # partition
                    f.write("</g>\n")
                # layer
                f.write("</g>\n")
            f.write("</svg>\n")

    def add_layer(self, layer: Layer):
        self._layers.append(layer)
