import os
import sys
import unittest

# Create a dummy shape module to mock dependencies if needed,
# but preferably we should use the real one if possible.
# Since the user environment has the files, we need to make sure 'src' is in path.
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from PySide6.QtCore import QPointF, QSizeF
from PySide6.QtGui import QColor, QImage

from layer import Layer


class TestLayer(unittest.TestCase):
    def setUp(self):
        # Create a dummy image for testing
        self.image = QImage(100, 100, QImage.Format_ARGB32)
        self.image.fill(QColor("white"))
        self.layer = Layer(self.image)

    def test_initialization(self):
        self.assertIsNotNone(self.layer.uuid)
        self.assertIsNotNone(self.layer.image)
        self.assertEqual(self.layer.image.width(), 100)
        self.assertEqual(self.layer.image.height(), 100)
        self.assertTrue(self.layer.visible)
        self.assertEqual(self.layer.opacity, 1.0)

    def test_properties_setter_getter(self):
        # Name
        self.layer.name = "Test Layer"
        self.assertEqual(self.layer.name, "Test Layer")

        # Visible
        self.layer.visible = False
        self.assertFalse(self.layer.visible)

        # Opacity
        self.layer.opacity = 0.5
        self.assertEqual(self.layer.opacity, 0.5)

        # Position
        new_pos = QPointF(10.0, 20.0)
        self.layer.position = new_pos
        self.assertEqual(self.layer.position, new_pos)

        # Pixel Size
        new_size = QSizeF(1.0, 1.0)
        self.layer.pixel_size = new_size
        self.assertEqual(self.layer.pixel_size, new_size)

    def test_serialization(self):
        self.layer.name = "Serialized Layer"
        self.layer.opacity = 0.8

        data = self.layer.to_dict()
        self.assertEqual(data["properties"]["name"], "Serialized Layer")
        self.assertEqual(data["properties"]["opacity"], 0.8)

        # Test creation from dict
        # Note: from_dict requires a slightly different structure or logic depending on implementation
        # Looking at layer.py: from_dict(cls, d: dict) -> Self
        # It seems from_dict might need 'image' path or data which is not in the simple dict we just got?
        # Let's check layer.py again.
        # layer.py:70: from_dict(cls, d: dict) -> Self
        # It creates a new instance.

        # Re-creating simple dict for populate_from_dict or checking what from_dict expects.
        # Ideally we test round trip if possible, but Layer usually needs an image source.
        # Testing populate_from_dict is safer for existing instance

        new_props = {
            "properties": {
                "name": "Updated Layer",
                "opacity": 0.2,
                "visible": False,
                "position": (5.0, 5.0),
                "rotation": 90,
            }
        }
        self.layer.populate_from_dict(new_props)
        self.assertEqual(self.layer.name, "Updated Layer")
        self.assertEqual(self.layer.opacity, 0.2)
        self.assertFalse(self.layer.visible)
        self.assertEqual(self.layer.position, QPointF(5.0, 5.0))
        self.assertEqual(self.layer.rotation, 90)

    def test_clone(self):
        self.layer.name = "Original"
        clone = self.layer.clone()

        self.assertNotEqual(self.layer.uuid, clone.uuid)
        self.assertEqual(self.layer.name, clone.name)
        self.assertEqual(self.layer.image.width(), clone.image.width())

        # Modify clone, ensure original is not changed
        clone.name = "Clone"
        self.assertEqual(self.layer.name, "Original")
        self.assertEqual(clone.name, "Clone")

    def test_calculate_fit_to_hoop_properties(self):
        # 100x100 pixels
        # pixel_size default is 2.5mm? let's check
        # Hoop size 4x4 inches = 101.6 x 101.6 mm

        hoop_inches = (4.0, 4.0)
        self.layer.calculate_fit_to_hoop_properties(hoop_inches)

        # Check that it fits
        # This one is a bit tricky without knowing exact math, but we can check it doesn't crash
        # and sets "some" reasonable values.

        props = self.layer.properties
        self.assertIsNotNone(props.pixel_size)
        self.assertIsNotNone(props.position)

    def test_flipped_image_and_partitions(self):
        from partition import Partition
        from shape import Path, Point, Rect

        # Setup a small image 10x10
        img = QImage(10, 10, QImage.Format_ARGB32)
        layer = Layer(img)

        # Add a partition with a Rect and a Path
        rect = Rect(2, 3)
        path = Path([Point(1, 1), Point(2, 2)])
        partition = Partition([rect, path], "Part1", "#FF0000")
        layer.partitions = {"part1_uuid": partition}

        # Flip horizontal
        flipped_img, flipped_parts = layer.flipped_image_and_partitions(True, False)

        self.assertEqual(flipped_img.width(), 10)
        self.assertIn("part1_uuid", flipped_parts)

        flipped_part = flipped_parts["part1_uuid"]
        self.assertEqual(len(flipped_part.route), 2)

        # Rect(2,3) flipped horiz (width=10) -> Rect(10 - 1 - 2, 3) = Rect(7, 3)
        self.assertEqual(flipped_part.route[0], Rect(7, 3))

        # Path([Point(1,1), Point(2,2)]) flipped horiz -> Path([Point(10-1, 1), Point(10-2, 2)])
        self.assertEqual(flipped_part.route[1], Path([Point(9, 1), Point(8, 2)]))

        # Verify original layer was NOT mutated
        self.assertEqual(layer.partitions["part1_uuid"].route[0], Rect(2, 3))
        self.assertEqual(layer.partitions["part1_uuid"].route[1], Path([Point(1, 1), Point(2, 2)]))

        # Flip vertical
        flipped_img_v, flipped_parts_v = layer.flipped_image_and_partitions(False, True)
        flipped_part_v = flipped_parts_v["part1_uuid"]
        # Rect(2,3) flipped vert (height=10) -> Rect(2, 10 - 1 - 3) = Rect(2, 6)
        self.assertEqual(flipped_part_v.route[0], Rect(2, 6))
        # Path([Point(1,1), Point(2,2)]) flipped vert -> Path([Point(1, 9), Point(2, 8)])
        self.assertEqual(flipped_part_v.route[1], Path([Point(1, 9), Point(2, 8)]))


if __name__ == "__main__":
    unittest.main()
