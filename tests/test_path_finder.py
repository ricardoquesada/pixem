import os
import sys
import unittest

# Ensure src is in path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from PySide6.QtGui import QColor, QImage

from path_finder import PathFinder


class TestPathFinder(unittest.TestCase):
    def setUp(self):
        # Create a simple 5x5 image
        # . . . . .
        # . # # # .
        # . # . # .
        # . # # # .
        # . . . . .
        # # = colored pixel (e.g. red)
        # . = transparent or different color

        self.width = 5
        self.height = 5
        self.image = QImage(self.width, self.height, QImage.Format_ARGB32)
        self.image.fill(QColor("transparent"))

        self.color = QColor("red")
        self.color_int = self.color.rgba() & 0xFFFFFF

        # Draw a box
        for x in range(1, 4):
            self.image.setPixelColor(x, 1, self.color)  # Top
            self.image.setPixelColor(x, 3, self.color)  # Bottom

        self.image.setPixelColor(1, 2, self.color)  # Left
        self.image.setPixelColor(3, 2, self.color)  # Right

        self.pf = PathFinder(self.image)

    def test_initialization(self):
        # Verify internal matrix
        color = self.pf.get_pixel_color(1, 1)
        self.assertEqual(color, self.color_int)

        transparent_color = self.pf.get_pixel_color(0, 0)
        self.assertEqual(transparent_color, -1)

    def test_find_shortest_path_simple(self):
        # Path from (1,1) to (3,1) along top edge
        # Note: Nodes in graph are vertices of pixels.
        # Pixel at (x,y) has top-left vertex (x,y).
        # Vertices are grid points.

        # Find path from top-left of pixel (1,1) to top-right of pixel (3,1) which is vertex (4,1)?
        # Let's check logic: Graph nodes are (x,y).
        # is_solid(x, y) checks pixel at x,y.
        # Edges connect vertices if adjacent pixels are solid.

        start = (1, 1)
        end = (4, 1)
        path = self.pf.find_shortest_pixel_path(self.color_int, start, end, use_weights=False)

        self.assertIsNotNone(path)
        # Path should be straight line: (1,1) -> (2,1) -> (3,1) -> (4,1)
        self.assertEqual(path, [(1, 1), (2, 1), (3, 1), (4, 1)])

    def test_find_shortest_path_around(self):
        # Path from (1,2) to (3,2)
        # Block direct path by ensuring no solid pixels adjacent to the line seg
        # (2,2) is transparent.
        # Also limit (2,1) and (2,3) to be transparent to remove "edges" for (2,2)

        self.image.setPixelColor(2, 1, QColor("transparent"))

        # Re-init pathfinder with new image
        self.pf = PathFinder(self.image)

        start = (1, 2)
        end = (4, 2)
        path = self.pf.find_shortest_pixel_path(self.color_int, start, end, use_weights=False)

        self.assertIsNotNone(path)
        # It must take more than direct steps
        self.assertGreater(len(path), 4)

    def test_simplify_path(self):
        # Straight line path
        path = [(1, 1), (2, 1), (3, 1), (4, 1)]
        points = self.pf.simplify_path_to_points(path)

        # Should simplify to Start and End only
        self.assertEqual(len(points), 2)
        self.assertEqual((points[0].x, points[0].y), (1, 1))
        self.assertEqual((points[-1].x, points[-1].y), (4, 1))

        # L-shape path: (1,1) -> (2,1) -> (2,2)
        path_l = [(1, 1), (2, 1), (2, 2)]
        points_l = self.pf.simplify_path_to_points(path_l)

        # Start, Corner, End
        self.assertEqual(len(points_l), 3)
        self.assertEqual((points_l[0].x, points_l[0].y), (1, 1))
        self.assertEqual((points_l[1].x, points_l[1].y), (2, 1))
        self.assertEqual((points_l[2].x, points_l[2].y), (2, 2))

    def test_remove_redundant_points(self):
        # A path that starts "inside" the start pixel vertices
        # Pixel (1,1) has vertices (1,1), (2,1), (1,2), (2,2).

        # Path: (1,1) -> (2,1) -> (3,1)
        # (1,1) is vertex of pixel (1,1)
        # (2,1) is vertex of pixel (1,1) (and (2,1))
        # (3,1) is NOT vertex of pixel (1,1)

        # Start pixel is defined by first point in path usually?
        # remove_redundant_points_from_start_and_end_nodes infers start pixel from node_path[0]
        # Wait, the method says: "Define the vertices for the start and end pixels based on the path"
        # sx, sy = node_path[0] implies start pixel is at x=sx, y=sy?
        # Actually logic is: start_pixel_vertices = (sx, sy) ... (sx+1, sy+1).
        # This assumes node_path[0] IS the top-left of the start pixel.
        # But a path can start at any corner of the pixel.
        # This logic seems to assume specific graph construction where nodes align with top-left?
        # Let's test with the logic as implemented.

        path = [(1, 1), (2, 1), (3, 1)]
        refined = self.pf.remove_redundant_points_from_start_and_end_nodes(path)

        # (2,1) is still part of start pixel (1,1) verts.
        # (3,1) is not.
        # So "exit point" is (2,1).
        # Expected: [(2,1), (3,1)]?
        # Let's trace:
        # start_idx starts at 0.
        # i=0, p=(1,1). in start_verts? Yes. start_idx=0.
        # i=1, p=(2,1). in start_verts? Yes. start_idx=1.
        # i=2, p=(3,1). in start_verts? No (assuming 3,1 is not in set {(1,1)..(2,2)}). break.
        # So start_idx = 1.
        # Path becomes path[1:] -> [(2,1), (3,1)].

        self.assertEqual(refined, [(2, 1), (3, 1)])


if __name__ == "__main__":
    unittest.main()
