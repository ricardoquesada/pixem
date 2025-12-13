import os
import sys
import unittest
from dataclasses import FrozenInstanceError

# Ensure src is in path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from shape import Path, Point, Rect, Shape


class TestShape(unittest.TestCase):
    def test_point_initialization(self):
        p = Point(10, 20)
        self.assertEqual(p.x, 10)
        self.assertEqual(p.y, 20)

    def test_point_immutability(self):
        p = Point(10, 20)
        with self.assertRaises(FrozenInstanceError):
            p.x = 30
        with self.assertRaises(FrozenInstanceError):
            p.y = 40

    def test_point_equality(self):
        p1 = Point(1, 2)
        p2 = Point(1, 2)
        p3 = Point(3, 4)
        self.assertEqual(p1, p2)
        self.assertNotEqual(p1, p3)
        self.assertNotEqual(p1, (1, 2))  # Should not equal a tuple

    def test_rect_initialization(self):
        r = Rect(5, 5)
        self.assertEqual(r.x, 5)
        self.assertEqual(r.y, 5)
        self.assertIsInstance(r, Shape)

    def test_rect_immutability(self):
        r = Rect(5, 5)
        with self.assertRaises(FrozenInstanceError):
            r.x = 10

    def test_rect_equality(self):
        r1 = Rect(5, 5)
        r2 = Rect(5, 5)
        r3 = Rect(10, 10)
        self.assertEqual(r1, r2)
        self.assertNotEqual(r1, r3)

    def test_path_initialization(self):
        points = [Point(0, 0), Point(1, 1)]
        path = Path(points)
        self.assertEqual(len(path.path), 2)
        self.assertEqual(path.path, points)

        # Test defensive copy on init
        points.append(Point(2, 2))
        self.assertEqual(len(path.path), 2)  # Should still be 2

    def test_path_mutability(self):
        p1 = Point(0, 0)
        p2 = Point(1, 1)
        path = Path([p1])

        # Append
        path.append_point(p2)
        self.assertEqual(len(path.path), 2)
        self.assertEqual(path.path[1], p2)

        # Delete
        path.delete_point(p1)
        self.assertEqual(len(path.path), 1)
        self.assertEqual(path.path[0], p2)

        # Delete non-existent raises ValueError (list.remove behavior)
        with self.assertRaises(ValueError):
            path.delete_point(p1)

    def test_path_equality(self):
        points = [Point(0, 0), Point(1, 1)]
        path1 = Path(points)
        path2 = Path(points)
        path3 = Path([Point(0, 0)])

        self.assertEqual(path1, path2)
        self.assertNotEqual(path1, path3)


if __name__ == "__main__":
    unittest.main()
