import os
import sys
import unittest

# Ensure src is in path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from partition import Partition
from shape import Path, Point, Rect


class TestPartition(unittest.TestCase):
    def setUp(self):
        # Create a simple path with Rects
        self.rects = [Rect(0, 0), Rect(0, 1), Rect(1, 0), Rect(1, 1)]
        self.partition = Partition(self.rects, name="Test Partition", color="#FF0000")

    def test_initialization(self):
        self.assertEqual(self.partition.name, "Test Partition")
        self.assertEqual(self.partition.color, "#FF0000")
        self.assertEqual(len(self.partition.path), 4)
        self.assertEqual(self.partition.pixel_count, 4)

    def test_serialization(self):
        data = self.partition.to_dict()
        self.assertEqual(data["name"], "Test Partition")
        self.assertEqual(data["color"], "#FF0000")
        self.assertEqual(data["size"], 4)
        self.assertEqual(len(data["path"]), 4)

        # Test backward compatibility where path might be just a list of coords,
        # but to_dict now produces {"type": "rect", ...}

        # Create from dict
        new_partition = Partition.from_dict(data)
        self.assertEqual(new_partition.name, "Test Partition")
        self.assertEqual(new_partition.color, "#FF0000")
        self.assertEqual(len(new_partition.path), 4)

        # Verify content
        self.assertIsInstance(new_partition.path[0], Rect)

    def test_path_mixed_types(self):
        # Test partition with both Rect and Path (if applicable for usage)
        # The Partition code supports it.

        shapes = [Rect(0, 0), Path([Point(0, 0), Point(10, 10)])]
        part = Partition(shapes, name="Mixed")

        data = part.to_dict()
        self.assertEqual(len(data["path"]), 2)
        self.assertEqual(data["path"][0]["type"], "rect")
        self.assertEqual(data["path"][1]["type"], "path")

        part_restored = Partition.from_dict(data)
        self.assertEqual(len(part_restored.path), 2)
        self.assertIsInstance(part_restored.path[0], Rect)
        self.assertIsInstance(part_restored.path[1], Path)

    def test_walk_path(self):
        # Need to test walk_path but it's complex as it fills based on neighbors.
        # Let's try a simple fill case.
        # Create a square 2x2
        # (0,0) (1,0)
        # (0,1) (1,1)

        # If we start at (0,0), it should find others if connected?
        # walk_path modifies self._path with "found" nodes.
        # Effectively it's a flood fill or spiral walker that discovers connected components
        # that are in the "path" list (which seems to act as 'valid coordinates' or 'mask'?)
        # Let's verify standard behavior:
        # 1. We provide a list of shapes (the 'mask' or 'pixels').
        # 2. We call walk_path with a start point.
        # 3. It should traverse connected pixels and re-order or filter them?
        # Actually looking at logic:
        # for shape in self._path: path_coords.add(...)
        # stack = [node] ...
        # So it traverses the graph defined by self._path starting from start_point.

        # Let's try to verify it respects connectivity.
        # Disconnected: (0,0) and (2,2)
        shapes = [Rect(0, 0), Rect(2, 2)]
        part = Partition(shapes)

        # Walk from 0,0
        part.walk_path(Partition.WalkMode.SPIRAL_CW, (0, 0))

        # It should probably visit (0,0) and NOT (2,2) because they are not 4-connected?
        # Wait, the code says:
        # "add possible missing nodes... We only add back Rects (pixels)"
        # So it seems to preserve disconnected parts too at the end?
        # The logic at the end of walk_path:
        # for shape in self._path: if coord not in visited: new_path_coords.append(coord)
        # So it re-orders: visited first, then unvisited?

        paths = part.path
        # Should still have 2
        self.assertEqual(len(paths), 2)
        self.assertEqual((paths[0].x, paths[0].y), (0, 0))  # First because visited
        self.assertEqual((paths[1].x, paths[1].y), (2, 2))  # Appended after


if __name__ == "__main__":
    unittest.main()
