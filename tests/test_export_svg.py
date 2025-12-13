import io
import os
import sys
import unittest
from unittest.mock import MagicMock

# Ensure src is in path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from PySide6.QtGui import QColor, QImage

from export_svg import INCHES_TO_MM, ExportToSvg
from layer import EmbroideryParameters, Layer
from shape import Path, Point, Rect


class TestExportSvg(unittest.TestCase):
    def setUp(self):
        self.filename = "test_export.svg"
        self.hoop_size = (4.0, 4.0)  # Inches
        self.exporter = ExportToSvg(self.filename, self.hoop_size)

    def tearDown(self):
        if os.path.exists(self.filename):
            os.remove(self.filename)

    def test_initialization(self):
        self.assertEqual(self.exporter._export_filename, self.filename)
        self.assertEqual(self.exporter._hoop_size, self.hoop_size)

    def test_write_svg_structure(self):
        # Add a dummy layer
        image = QImage(10, 10, QImage.Format_ARGB32)
        image.fill(QColor("red"))
        layer = Layer(image)
        layer.name = "TestLayer"

        # Mocking properties that might be complex to set up via full object state
        # But Layer object seems simple enough.
        # We need a partition though.

        # Manually inject a partition
        partition = MagicMock()
        partition.name = "ColorPartition"
        partition.color = "#ff0000"

        # Path with one Rect and one Path
        rect = Rect(1, 1)
        path_shape = Path([Point(1, 1), Point(2, 2)])

        partition.path = [rect, path_shape]

        # Layer.partitions is a dict
        layer.partitions = {"#ff0000": partition}

        self.exporter.add_layer(layer)

        # write_to_svg writes to file. We can capture it by mocking open?
        # Or just write to a real temporary file and read it back. Since we are in setUp/tearDown with a file name.

        self.exporter.write_to_svg()

        self.assertTrue(os.path.exists(self.filename))

        with open(self.filename, "r") as f:
            content = f.read()

        # Verify Header
        self.assertIn('<?xml version="1.0" encoding="UTF-8" standalone="no"?>', content)
        self.assertIn("<svg", content)

        # Verify ViewBox dimensions (4 inches * 25.4 = 101.6 mm)
        mm_size = round(4.0 * INCHES_TO_MM)
        self.assertIn(f'width="{mm_size}mm"', content)
        self.assertIn(f'height="{mm_size}mm"', content)

        # Verify Layer
        self.assertIn('id="TestLayer"', content)

        # Verify Partition
        self.assertIn('id="partition_0_ColorPartition"', content)

        # Verify Rect
        # id="pixel_{layer_idx}_{x}_{y}_{angle}"
        # angle depends on even/odd. x=1, y=1 -> x+y=2 -> even.
        # Default even/odd angles are 0?
        # Checking Layer defaults or EmbroideryParameters defaults.
        # EmbroideryParameters defaults: even=0, odd=0 or something?
        # Let's just check for the rect tag presence with x and y attrs
        # x=1 * pixel_size[0]. Default pixel size?
        # Layer.properties.pixel_size default is (1.0, 1.0) usually?

        # Just check basic existence of rect
        self.assertIn("<rect", content)
        self.assertIn('x="', content)  # Might need regex for exact values if not sure of defaults

        # Verify Path
        self.assertIn("<path", content)
        self.assertIn('d="M ', content)

    def test_rect_attributes(self):
        # Create a simplified test for _write_rect_to_svg using StringIO
        output = io.StringIO()

        params = EmbroideryParameters()
        params.fill_method = "zigzag"

        self.exporter._write_rect_to_svg(
            output,
            indent="",
            layer_idx=0,
            x=10,
            y=20,
            pixel_size=(2.0, 2.0),
            color="#00FF00",
            angle=45,
            embroidery_params=params,
        )

        svg = output.getvalue()
        self.assertIn("<rect", svg)
        self.assertIn('x="20.0"', svg)  # 10 * 2.0
        self.assertIn('y="40.0"', svg)  # 20 * 2.0
        self.assertIn('fill="#00FF00"', svg)
        self.assertIn('inkstitch:fill_method="zigzag"', svg)
        self.assertIn('inkstitch:angle="45"', svg)


if __name__ == "__main__":
    unittest.main()
