# Pixem
# Copyright 2026 - Ricardo Quesada

import os
import sys
import unittest

# Ensure src is in path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from PySide6.QtCore import QPointF, QSizeF
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from canvas import Canvas
from layer import Layer
from preferences import get_global_preferences
from state import State


class TestCanvasSnapping(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.state = State()
        self.canvas = Canvas(self.state)

        # Create a dummy layer
        image = QImage(10, 10, QImage.Format_ARGB32)
        image.fill(QColor("red"))
        self.layer1 = Layer(image)
        self.layer1.position = QPointF(10.0, 10.0)
        self.layer1.pixel_size = QSizeF(1.0, 1.0)  # 10x10 mm

        self.state.add_layer(self.layer1)

        # Configure preferences for testing
        self.prefs = get_global_preferences()
        self.prefs.set_grid_size_mm(10.0)
        self.prefs.set_snap_to_grid(True)
        self.prefs.set_snap_to_hoop(True)
        self.prefs.set_snap_to_layers(True)

    def test_snap_point_to_grid(self):
        self.prefs.set_snap_to_grid(True)
        self.prefs.set_snap_to_hoop(False)
        self.prefs.set_snap_to_layers(False)

        # Scale is 5.0 (zoom=1.0), threshold is 8/5 = 1.6mm
        # Point at (9.0, 10.5) is within 1.6mm of (10.0, 10.0)
        pt = QPointF(9.0, 10.5)
        snapped = self.canvas._snap_point(pt)
        self.assertEqual(snapped, QPointF(10.0, 10.0))
        self.assertEqual(self.canvas._snap_guide_x, 10.0)
        self.assertEqual(self.canvas._snap_guide_y, 10.0)

        # Point at (8.0, 10.5) is 2.0mm away in X, which is outside threshold
        # So it should only snap Y (10.5 -> 10.0), X should remain 8.0
        pt2 = QPointF(8.0, 10.5)
        self.canvas._snap_guide_x = None
        self.canvas._snap_guide_y = None
        snapped2 = self.canvas._snap_point(pt2)
        self.assertEqual(snapped2, QPointF(8.0, 10.0))
        self.assertIsNone(self.canvas._snap_guide_x)
        self.assertEqual(self.canvas._snap_guide_y, 10.0)

    def test_snap_point_to_hoop(self):
        self.prefs.set_snap_to_grid(False)
        self.prefs.set_snap_to_hoop(True)
        self.prefs.set_snap_to_layers(False)

        # Hoop is 4x4 inches = 101.6 x 101.6 mm
        # Point at (1.0, 100.9) is within 1.6mm of (0.0, 101.6)
        pt = QPointF(1.0, 100.9)
        snapped = self.canvas._snap_point(pt)
        self.assertEqual(snapped, QPointF(0.0, 101.6))
        self.assertEqual(self.canvas._snap_guide_x, 0.0)
        self.assertEqual(self.canvas._snap_guide_y, 101.6)

    def test_snap_position_to_grid(self):
        self.prefs.set_snap_to_grid(True)
        self.prefs.set_snap_to_hoop(False)
        self.prefs.set_snap_to_layers(False)

        # Layer1 is 10x10 mm.
        # Candidate position (9.5, 9.5)
        # Top-left corner (9.5, 9.5) is close to (10.0, 10.0)
        # It should snap the whole layer to (10.0, 10.0)
        candidate = QPointF(9.5, 9.5)
        snapped = self.canvas._snap_position(self.layer1, candidate)
        self.assertEqual(snapped, QPointF(10.0, 10.0))
        self.assertEqual(self.canvas._snap_guide_x, 10.0)
        self.assertEqual(self.canvas._snap_guide_y, 10.0)

    def test_snap_position_to_other_layer(self):
        self.prefs.set_snap_to_grid(False)
        self.prefs.set_snap_to_hoop(False)
        self.prefs.set_snap_to_layers(True)

        # Create a second layer
        image2 = QImage(10, 10, QImage.Format_ARGB32)
        self.layer2 = Layer(image2)
        self.layer2.position = QPointF(30.0, 30.0)
        self.layer2.pixel_size = QSizeF(1.0, 1.0)  # 10x10 mm
        self.state.add_layer(self.layer2)

        # Layer1 is at (10, 10) [size 10x10], so its bottom-right is at (20, 20)
        # If we move Layer2 (size 10x10) so its top-left is at (20.5, 20.5)
        # It should snap to Layer1's bottom-right corner (20, 20)
        candidate = QPointF(20.5, 20.5)
        snapped = self.canvas._snap_position(self.layer2, candidate)
        self.assertEqual(snapped, QPointF(20.0, 20.0))
        self.assertEqual(self.canvas._snap_guide_x, 20.0)
        self.assertEqual(self.canvas._snap_guide_y, 20.0)

    def test_no_snapping_when_disabled(self):
        self.prefs.set_snap_to_grid(False)
        self.prefs.set_snap_to_hoop(False)
        self.prefs.set_snap_to_layers(False)

        pt = QPointF(9.5, 9.5)
        self.canvas._snap_guide_x = None
        self.canvas._snap_guide_y = None
        snapped = self.canvas._snap_point(pt)
        self.assertEqual(snapped, pt)
        self.assertIsNone(self.canvas._snap_guide_x)
        self.assertIsNone(self.canvas._snap_guide_y)

    def test_canvas_grid_preference_slots(self):
        # Initial cached values (matching setUp)
        self.assertEqual(self.canvas._cached_grid_visible, False)
        self.assertEqual(self.canvas._cached_grid_size, 10.0)

        # Trigger slot for visibility
        self.canvas._on_grid_visible_changed(True)
        self.assertEqual(self.canvas._cached_grid_visible, True)

        # Trigger slot for size
        self.canvas._on_grid_size_changed(15.0)
        self.assertEqual(self.canvas._cached_grid_size, 15.0)


if __name__ == "__main__":
    unittest.main()
