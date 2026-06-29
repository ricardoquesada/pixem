# Pixem
# Copyright 2026 - Ricardo Quesada

import os
import sys
import unittest

# Ensure src is in path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from partition import Partition
from shape import Path, Point, Rect


class TestPartition(unittest.TestCase):
    def setUp(self):
        # Create a simple route with Rects
        self.rects = [Rect(0, 0), Rect(0, 1), Rect(1, 0), Rect(1, 1)]
        self.partition = Partition(self.rects, name="Test Partition", color="#FF0000")

    def test_initialization(self):
        self.assertEqual(self.partition.name, "Test Partition")
        self.assertEqual(self.partition.color, "#FF0000")
        self.assertEqual(len(self.partition.route), 4)
        self.assertEqual(self.partition.pixel_count, 4)

    def test_serialization(self):
        data = self.partition.to_dict()
        self.assertEqual(data["name"], "Test Partition")
        self.assertEqual(data["color"], "#FF0000")
        self.assertEqual(data["size"], 4)
        self.assertEqual(len(data["route"]), 4)

        # Test backward compatibility: load from legacy dict using "path" key
        legacy_data = {
            "name": "Test Partition",
            "color": "#FF0000",
            "size": 4,
            "path": [
                {"type": "rect", "x": 0, "y": 0},
                {"type": "rect", "x": 0, "y": 1},
                {"type": "rect", "x": 1, "y": 0},
                {"type": "rect", "x": 1, "y": 1},
            ],
        }
        new_partition = Partition.from_dict(legacy_data)
        self.assertEqual(new_partition.name, "Test Partition")
        self.assertEqual(new_partition.color, "#FF0000")
        self.assertEqual(len(new_partition.route), 4)
        self.assertIsInstance(new_partition.route[0], Rect)

        # Test loading from new dict using "route" key
        new_partition_2 = Partition.from_dict(data)
        self.assertEqual(new_partition_2.name, "Test Partition")
        self.assertEqual(len(new_partition_2.route), 4)
        self.assertIsInstance(new_partition_2.route[0], Rect)

    def test_route_mixed_types(self):
        shapes = [Rect(0, 0), Path([Point(0, 0), Point(10, 10)])]
        part = Partition(shapes, name="Mixed")

        data = part.to_dict()
        self.assertEqual(len(data["route"]), 2)
        self.assertEqual(data["route"][0]["type"], "rect")
        self.assertEqual(data["route"][1]["type"], "path")

        part_restored = Partition.from_dict(data)
        self.assertEqual(len(part_restored.route), 2)
        self.assertIsInstance(part_restored.route[0], Rect)
        self.assertIsInstance(part_restored.route[1], Path)

    def test_walk_route(self):
        # Disconnected: (0,0) and (2,2)
        shapes = [Rect(0, 0), Rect(2, 2)]
        part = Partition(shapes)

        # Walk from 0,0
        part.walk_route(Partition.WalkMode.SPIRAL_CW, (0, 0))

        routes = part.route
        self.assertEqual(len(routes), 2)
        self.assertEqual((routes[0].x, routes[0].y), (0, 0))  # First because visited
        self.assertEqual((routes[1].x, routes[1].y), (2, 2))  # Appended after


if __name__ == "__main__":
    unittest.main()
