import os
import sys
import unittest

# Ensure src is in path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from PySide6.QtGui import QColor, QImage

from layer import Layer, LayerProperties
from state import State
from undo_commands import AddLayerCommand, DeleteLayerCommand, UpdateLayerPropertiesCommand


class TestUndoCommands(unittest.TestCase):
    def setUp(self):
        self.state = State()
        image = QImage(10, 10, QImage.Format_ARGB32)
        image.fill(QColor("red"))
        self.layer = Layer(image)
        self.layer.name = "Undo Layer"

    def test_add_layer_command(self):
        cmd = AddLayerCommand(self.state, self.layer, None)

        # Initial: Layer not in state (assuming command doesn't auto-redo on init unless pushed to stack)
        # Usually QUndoCommand doesn't executed in init.
        # But wait, looking at typical implementations, creating it might validly do nothing until redo() is called.
        self.assertEqual(len(self.state.layers), 0)

        cmd.redo()
        self.assertEqual(len(self.state.layers), 1)
        self.assertEqual(self.state.layers[0], self.layer)

        cmd.undo()
        self.assertEqual(len(self.state.layers), 0)

        cmd.redo()
        self.assertEqual(len(self.state.layers), 1)

    def test_delete_layer_command(self):
        # Setup: Layer must be in state first
        self.state.add_layer(self.layer)
        self.assertEqual(len(self.state.layers), 1)

        cmd = DeleteLayerCommand(self.state, self.layer, None)

        cmd.redo()
        self.assertEqual(len(self.state.layers), 0)

        cmd.undo()
        self.assertEqual(len(self.state.layers), 1)
        self.assertEqual(self.state.layers[0], self.layer)

    def test_update_layer_properties_command(self):
        self.state.add_layer(self.layer)

        new_props = LayerProperties()
        new_props.name = "Renamed Layer"
        new_props.opacity = 0.5

        cmd = UpdateLayerPropertiesCommand(self.state, self.layer, new_props, None)

        cmd.redo()
        self.assertEqual(self.layer.name, "Renamed Layer")
        self.assertEqual(self.layer.opacity, 0.5)

        cmd.undo()
        self.assertEqual(self.layer.name, "Undo Layer")
        self.assertEqual(self.layer.opacity, 1.0)  # Default

        cmd.redo()
        self.assertEqual(self.layer.name, "Renamed Layer")


if __name__ == "__main__":
    unittest.main()
