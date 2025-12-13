import os
import sys
import unittest

# Ensure src is in path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from PySide6.QtGui import QColor, QImage

from layer import Layer
from state import State


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
        # Verify undo stack exists
        self.assertIsNotNone(self.state.undo_stack)
        # Adding a layer usually pushes a command if done via logic that uses commands,
        # but State.add_layer methods themselves might not push to stack depending on implementation?
        # Checking implementation: State.add_layer just modifies list and emits signal.
        # Commands are usually separate classes that CALL state methods.
        # So here we just verify the state has an undo stack property.
        pass


if __name__ == "__main__":
    unittest.main()
