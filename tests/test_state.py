import os
import sys
import unittest

# Ensure src is in path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from PySide6.QtGui import QColor, QImage

from layer import Layer
from partition import Partition
from shape import Rect
from state import State
from state_properties import StatePropertyFlags


class TestState(unittest.TestCase):
    def setUp(self):
        self.state = State()
        # Create a dummy layer
        image = QImage(10, 10, QImage.Format_ARGB32)
        image.fill(QColor("blue"))
        self.layer = Layer(image)
        self.layer.name = "Test Layer"

    def test_initialization(self):
        self.assertEqual(len(self.state.layers), 0)
        self.assertIsNone(self.state.selected_layer)
        # Check default properties
        self.assertTrue(self.state.hoop_visible)
        self.assertEqual(self.state.zoom_factor, 1.0)

    def test_add_remove_layer(self):
        # Add
        self.state.add_layer(self.layer)
        self.assertEqual(len(self.state.layers), 1)
        self.assertEqual(self.state.layers[0], self.layer)
        self.assertEqual(self.state.selected_layer, self.layer)

        # Remove
        self.state.delete_layer(self.layer)
        self.assertEqual(len(self.state.layers), 0)
        self.assertIsNone(self.state.selected_layer)

    def test_selection(self):
        self.state.add_layer(self.layer)

        # Create another layer
        layer2 = Layer(QImage(10, 10, QImage.Format_ARGB32))
        layer2.name = "Layer 2"
        self.state.add_layer(layer2)

        self.assertEqual(self.state.selected_layer, layer2)

        # Change selection by UUID
        self.state.selected_layer_uuid = self.layer.uuid
        self.assertEqual(self.state.selected_layer, self.layer)

        # Deselect
        self.state.selected_layer_uuid = None
        self.assertIsNone(self.state.selected_layer)

    def test_selected_layer_uuid_signal(self):
        self.state.add_layer(self.layer)

        signal_received = []

        def on_property_changed(flag, properties):
            signal_received.append((flag, properties))

        self.state.state_property_changed.connect(on_property_changed)

        # Change selection (should not emit if it was already selected)
        self.state.selected_layer_uuid = self.layer.uuid
        self.assertEqual(len(signal_received), 0)

        # Deselect (should emit)
        self.state.selected_layer_uuid = None
        self.assertEqual(len(signal_received), 1)
        self.assertEqual(signal_received[0][0], StatePropertyFlags.SELECTED_LAYER_UUID)

        # Select again (should emit)
        signal_received.clear()
        self.state.selected_layer_uuid = self.layer.uuid
        self.assertEqual(len(signal_received), 1)
        self.assertEqual(signal_received[0][0], StatePropertyFlags.SELECTED_LAYER_UUID)

    def test_reorder_layers(self):
        layer1 = self.layer
        layer2 = Layer(QImage(10, 10, QImage.Format_ARGB32))
        self.state.add_layer(layer1)
        self.state.add_layer(layer2)

        # Initial order: layer1, layer2
        self.assertEqual(self.state.layers, [layer1, layer2])

        # Reorder
        self.state.reorder_layers([layer2, layer1])
        self.assertEqual(self.state.layers, [layer2, layer1])

    def test_basic_serialization(self):
        self.state.add_layer(self.layer)
        self.state.hoop_visible = False

        data = self.state.to_dict()
        self.assertFalse(data["properties"]["hoop_visible"])
        self.assertEqual(len(data["layers"]), 1)
        # Access the first (and only) layer value
        layer_data = next(iter(data["layers"].values()))
        self.assertEqual(layer_data["properties"]["name"], "Test Layer")

        # Minimal restore check
        new_state = State.from_dict(data)
        self.assertFalse(new_state.hoop_visible)
        self.assertEqual(len(new_state.layers), 1)
        # Layers are a list in the State object property, but a dict in serialization
        self.assertEqual(new_state.layers[0].name, "Test Layer")

    def test_undo_stack(self):
        # 1. Test Add Layer Undo/Redo
        self.assertEqual(len(self.state.layers), 0)
        self.state.add_layer(self.layer)
        self.assertEqual(len(self.state.layers), 1)

        self.state.undo_stack.undo()
        self.assertEqual(len(self.state.layers), 0)

        self.state.undo_stack.redo()
        self.assertEqual(len(self.state.layers), 1)
        self.assertEqual(self.state.layers[0], self.layer)

        # 2. Test Update Layer Image/Partitions (Flipping) Undo/Redo
        # Setup initial partition
        initial_partition = Partition([Rect(0, 0)], "Initial", "#FF0000")
        self.layer.partitions = {"part1": initial_partition}

        # Flip (simulate)
        new_image, new_partitions = self.layer.flipped_image_and_partitions(True, False)

        # Apply via state
        self.state.update_layer_image_and_partitions(self.layer, new_image, new_partitions)

        # Verify applied (width is 10, so 10-1-0 = 9)
        self.assertEqual(self.layer.partitions["part1"].route[0], Rect(9, 0))

        # Undo
        self.state.undo_stack.undo()
        self.assertEqual(self.layer.partitions["part1"].route[0], Rect(0, 0))

        # Redo
        self.state.undo_stack.redo()
        self.assertEqual(self.layer.partitions["part1"].route[0], Rect(9, 0))


if __name__ == "__main__":
    unittest.main()
