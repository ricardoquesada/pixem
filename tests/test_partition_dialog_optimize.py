import os
import sys
import unittest

# Ensure src is in path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from partition import Partition
from partition_dialog import PartitionDialog

# Import resources to register :/ prefix
from res import rc_resources  # noqa: F401
from shape import Path, Rect


class TestPartitionDialogOptimize(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        # Create a simple 8x8 image
        self.image = QImage(8, 8, QImage.Format_ARGB32)
        self.image.fill(QColor("transparent"))

        # We will draw pixels of partition color (red) in two separate blocks:
        # Block 1: (1, 1) and (1, 2)
        # Block 2: (4, 4) and (4, 5)
        self.color = QColor("red")
        self.color_str = "#ff0000"
        self.color_int = self.color.rgba() & 0xFFFFFF

        self.image.setPixelColor(1, 1, self.color)
        self.image.setPixelColor(1, 2, self.color)
        self.image.setPixelColor(4, 4, self.color)
        self.image.setPixelColor(4, 5, self.color)

        # Draw a solid bridge of another color (blue) between the two blocks
        # so the pathfinder can find a route (hugging the blue color)
        self.bridge_color = QColor("blue")
        self.image.setPixelColor(2, 2, self.bridge_color)
        self.image.setPixelColor(3, 2, self.bridge_color)
        self.image.setPixelColor(3, 3, self.bridge_color)
        self.image.setPixelColor(3, 4, self.bridge_color)

        # Create route with unoptimized order:
        # Let's say: [Rect(1,2), Rect(4,5), Rect(1,1), Rect(4,4)]
        self.initial_route = [
            Rect(1, 2),
            Rect(4, 5),
            Rect(1, 1),
            Rect(4, 4),
        ]
        self.partition = Partition(list(self.initial_route), name="test_part", color=self.color_str)
        self.dialog = PartitionDialog(self.image, self.partition)

    def tearDown(self):
        self.dialog.close()

    def test_full_optimization(self):
        widget = self.dialog._image_widget
        # Verify initial state
        self.assertEqual(len(widget._original_shapes), 4)
        self.assertEqual(widget._original_shapes, self.initial_route)

        # Trigger Optimize Route
        self.dialog._action_optimize.trigger()

        # The route should now be optimized:
        # It should traverse block 1 first, then jump to block 2 (creating a Path), then traverse block 2.
        # Expected optimized original shapes list length should be 5 (4 rects + 1 path)
        opt_shapes = widget._original_shapes
        self.assertEqual(len(opt_shapes), 5)

        # Verify it starts with block 1 pixels and ends with block 2 pixels
        self.assertIsInstance(opt_shapes[0], Rect)
        self.assertIsInstance(opt_shapes[1], Rect)
        self.assertIsInstance(opt_shapes[2], Path)
        self.assertIsInstance(opt_shapes[3], Rect)
        self.assertIsInstance(opt_shapes[4], Rect)

        # Answer A3: "Select all shapes in the new optimized route"
        self.assertEqual(widget._selected_shapes, opt_shapes)

        # Verify Undo
        self.assertTrue(self.dialog.undo_stack.canUndo())
        self.dialog.undo_stack.undo()
        self.assertEqual(widget._original_shapes, self.initial_route)
        self.assertEqual(widget._selected_shapes, [])

        # Verify Redo
        self.assertTrue(self.dialog.undo_stack.canRedo())
        self.dialog.undo_stack.redo()
        self.assertEqual(widget._original_shapes, opt_shapes)
        self.assertEqual(widget._selected_shapes, opt_shapes)

    def test_subset_optimization(self):
        widget = self.dialog._image_widget
        list_widget = self.dialog._list_widget

        # Select only shapes at index 1 and 3: Rect(4, 5) and Rect(4, 4)
        # These are both in Block 2.
        list_widget.item(1).setSelected(True)
        list_widget.item(3).setSelected(True)

        # Verify they are selected
        selected_shapes = [item.data(Qt.UserRole) for item in list_widget.selectedItems()]
        self.assertEqual(len(selected_shapes), 2)
        self.assertEqual(widget._selected_shapes, selected_shapes)

        # Trigger Optimize Route (only optimizes the selected subset)
        # B2 pixels are (4,4) and (4,5). The optimized order should start at the top-leftmost which is (4,4) then (4,5).
        # Since they are contiguous, no jump path is needed between them.
        self.dialog._action_optimize.trigger()

        # The non-selected items (Rect(1,2) at index 0, Rect(1,1) at index 2) should remain in their positions.
        # The selected items at index 1 and 3 should be replaced by optimized subset at the first index (1).
        # So we expect: [Rect(1, 2), Rect(4, 4), Rect(4, 5), Rect(1, 1)]
        expected_route = [
            Rect(1, 2),
            Rect(4, 4),
            Rect(4, 5),
            Rect(1, 1),
        ]
        self.assertEqual(widget._original_shapes, expected_route)

        # The selected shapes should be updated to the new optimized subset
        self.assertEqual(widget._selected_shapes, [Rect(4, 4), Rect(4, 5)])

        # Undo should restore original route and selection
        self.dialog.undo_stack.undo()
        self.assertEqual(widget._original_shapes, self.initial_route)
        self.assertEqual(widget._selected_shapes, selected_shapes)


if __name__ == "__main__":
    unittest.main()
