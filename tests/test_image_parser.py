import os
import sys
import unittest

# Ensure src is in path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from PySide6.QtGui import QColor, QImage

from image_parser import ImageParser


class TestImageParser(unittest.TestCase):
    def test_initialization_single_color(self):
        # 3x3 image, all red
        image = QImage(3, 3, QImage.Format_ARGB32)
        image.fill(QColor("red"))

        parser = ImageParser(image)
        partitions = parser.partitions

        # Should have 1 partition for red
        self.assertEqual(len(partitions), 1)
        partition = next(iter(partitions.values()))
        self.assertEqual(partition.color, "#ff0000")  # QColor("red").name() is #ff0000
        # 9 pixels
        self.assertEqual(partition.pixel_count, 9)

    def test_initialization_two_colors(self):
        # 3x3 image
        # R R R
        # B B B
        # B B B
        image = QImage(3, 3, QImage.Format_ARGB32)
        image.fill(QColor("blue"))

        # Set top row to red
        for x in range(3):
            image.setPixelColor(x, 0, QColor("red"))

        parser = ImageParser(image)
        partitions = parser.partitions

        # Should have 2 partitions: Red and Blue
        self.assertEqual(len(partitions), 2)

        colors = sorted([p.color for p in partitions.values()])
        self.assertEqual(colors, ["#0000ff", "#ff0000"])

        # Verify sizes
        # Red: 3 pixels
        # Blue: 6 pixels
        for p in partitions.values():
            if p.color == "#ff0000":
                self.assertEqual(p.pixel_count, 3)
            elif p.color == "#0000ff":
                self.assertEqual(p.pixel_count, 6)

    def test_disconnected_same_color(self):
        # 3x3 image
        # R B R  <-- Two disconnected Red regions
        # B B B
        # B B B
        image = QImage(3, 3, QImage.Format_ARGB32)
        image.fill(QColor("blue"))

        image.setPixelColor(0, 0, QColor("red"))
        image.setPixelColor(2, 0, QColor("red"))

        parser = ImageParser(image)
        partitions = parser.partitions

        # Should still be 2 partitions because same color is grouped
        # unless the parser splits them?
        # Checking implementation of ImageParser:
        # _generate_shapes_for_color: "Identify all disconnected blocks... group them?"
        # ImageParser description says "groups them by color" and "creates partitions".
        # Usually it creates ONE partition per color, containing multiple shapes if needed.
        # Let's verify that assumption.

        self.assertEqual(len(partitions), 2)

        red_partition = None
        for p in partitions.values():
            if p.color == "#ff0000":
                red_partition = p
                break

        # The parser connects disconnected regions of the same color with a Path.
        # So we expect: Rect(pixel 1) -> Path(jump) -> Rect(pixel 2)
        # Total shapes: 3
        self.assertEqual(len(red_partition.path), 3)

        shapes = red_partition.path
        from shape import Path, Rect

        self.assertIsInstance(shapes[0], Rect)
        self.assertIsInstance(shapes[1], Path)
        self.assertIsInstance(shapes[2], Rect)

    def test_background_color_ignore(self):
        # 3x3 image, all red
        image = QImage(3, 3, QImage.Format_ARGB32)
        image.fill(QColor("red"))

        # Set background as red
        bg_color = QColor("red")

        parser = ImageParser(image, background_color=bg_color)
        partitions = parser.partitions

        # If background matches the only color, should we get 0 partitions?
        # ImageParser usually ignores background?
        # Let's check constructor or logic.
        # "background_color: The background color to compare against for sorting."
        # It might just affect sorting, not exclusion.
        # If it doesn't exclude, then we still get 1 partition.
        # If the user intent was "remove background", that might be different.
        # Let's assume for now it produces the partition.
        # Wait, if I'm not sure, I should check the code.
        # Viewing image_parser.py earlier suggests it iterates over all colors in `_create_color_graph`.
        # It doesn't seem to explicitly exclude `background_color` from partition creation loop.

        self.assertEqual(len(partitions), 1)


if __name__ == "__main__":
    unittest.main()
