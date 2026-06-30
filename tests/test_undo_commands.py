import os
import sys
import unittest
from unittest.mock import MagicMock

# Ensure src is in path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from PySide6.QtGui import QColor, QImage

from layer import Layer, LayerProperties
from partition import Partition
from partition_dialog import UpdateShapesCommand
from shape import Rect
from state import State
from undo_commands import (
    AddLayerCommand,
    DeleteLayerCommand,
    UpdateLayerImageCommand,
    UpdateLayerPropertiesCommand,
)


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

    def test_update_layer_image_command(self):
        self.state.add_layer(self.layer)

        new_image = QImage(5, 5, QImage.Format_ARGB32)
        new_image.fill(QColor("blue"))

        new_partitions = {"part1": Partition([])}

        cmd = UpdateLayerImageCommand(self.state, self.layer, new_image, new_partitions, None)

        cmd.redo()
        self.assertEqual(self.layer.image.width(), 5)
        self.assertEqual(self.layer.image.pixelColor(0, 0), QColor("blue"))
        self.assertEqual(self.layer.partitions, new_partitions)

        cmd.undo()
        self.assertEqual(self.layer.image.width(), 10)
        self.assertEqual(self.layer.image.pixelColor(0, 0), QColor("red"))
        self.assertEqual(self.layer.partitions, {})


class TestPartitionDialogUndo(unittest.TestCase):
    def test_update_shapes_command(self):
        dialog = MagicMock()

        old_selected = [Rect(1, 1)]
        old_original = [Rect(1, 1), Rect(2, 2)]
        new_selected = [Rect(2, 2)]
        new_original = [Rect(2, 2), Rect(1, 1)]

        cmd = UpdateShapesCommand(
            dialog, "Test Command", old_selected, old_original, new_selected, new_original
        )

        # Test redo
        cmd.redo()
        dialog._image_widget.set_original_shapes.assert_called_with(new_original)
        dialog._image_widget.set_selected_shapes.assert_called_with(new_selected)
        dialog._image_widget._rebuild_cache.assert_called()
        dialog.update_shapes.assert_called_with(new_selected, new_original)
        dialog._image_widget.update.assert_called()

        # Test undo
        cmd.undo()
        dialog._image_widget.set_original_shapes.assert_called_with(old_original)
        dialog._image_widget.set_selected_shapes.assert_called_with(old_selected)
        dialog._image_widget._rebuild_cache.assert_called()
        dialog.update_shapes.assert_called_with(old_selected, old_original)
        dialog._image_widget.update.assert_called()


if __name__ == "__main__":
    unittest.main()
