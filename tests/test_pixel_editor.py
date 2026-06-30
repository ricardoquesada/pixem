# Pixem
# Copyright 2026 - Ricardo Quesada

import os
import sys
import unittest

# Ensure src is in path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from pixel_editor_dialog import PixelEditorDialog, PixelImageWidget


class TestPixelEditor(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        # Create a simple 4x4 image with 2 colors + transparency
        self.image = QImage(4, 4, QImage.Format_ARGB32)
        self.image.fill(Qt.GlobalColor.transparent)
        self.image.setPixelColor(0, 0, QColor("red"))
        self.image.setPixelColor(1, 0, QColor("red"))
        self.image.setPixelColor(0, 1, QColor("blue"))
        # Rest is transparent

        self.widget = PixelImageWidget(self.image)

    def test_initial_image_state(self):
        img = self.widget.get_image()
        self.assertEqual(img.width(), 4)
        self.assertEqual(img.height(), 4)
        self.assertEqual(img.pixelColor(0, 0), QColor("red"))
        self.assertEqual(img.pixelColor(0, 1), QColor("blue"))
        self.assertEqual(img.pixelColor(2, 2).alpha(), 0)

    def test_pencil_tool_draws(self):
        self.widget.set_tool(PixelImageWidget.Tool.PENCIL)
        self.widget.set_active_color(QColor("green"))
        # Draw on (2, 2)
        self.widget._apply_tool(QPoint(2, 2))
        self.assertEqual(self.widget.get_image().pixelColor(2, 2), QColor("green"))

    def test_eraser_tool_erases(self):
        self.widget.set_tool(PixelImageWidget.Tool.ERASER)
        # Erase (0, 0) which is red
        self.widget._apply_tool(QPoint(0, 0))
        self.assertEqual(self.widget.get_image().pixelColor(0, 0).alpha(), 0)

    def test_eyedropper_tool_picks_color(self):
        self.widget.set_tool(PixelImageWidget.Tool.COLOR_PICKER)

        picked_colors = []
        self.widget.color_picked.connect(picked_colors.append)

        # Pick (0, 0) -> red
        self.widget._apply_tool(QPoint(0, 0))
        self.assertEqual(len(picked_colors), 1)
        self.assertEqual(picked_colors[0], QColor("red"))

        # Pick (0, 1) -> blue
        self.widget._apply_tool(QPoint(0, 1))
        self.assertEqual(len(picked_colors), 2)
        self.assertEqual(picked_colors[1], QColor("blue"))

    def test_dialog_palette_extraction(self):
        dialog = PixelEditorDialog(self.image)
        # Unique colors should be red (#FF0000) and blue (#0000FF)
        # Transparent is excluded.
        self.assertEqual(dialog._palette_list.count(), 2)

        color0 = dialog._palette_list.item(0).data(Qt.UserRole)
        color1 = dialog._palette_list.item(1).data(Qt.UserRole)

        # Colors are sorted by rgba
        colors = {color0.name(), color1.name()}
        self.assertEqual(colors, {QColor("red").name(), QColor("blue").name()})

    def test_dialog_add_color_to_palette(self):
        dialog = PixelEditorDialog(self.image)
        self.assertEqual(dialog._palette_list.count(), 2)

        dialog._add_color_to_palette_widget(QColor("green"))
        self.assertEqual(dialog._palette_list.count(), 3)

        # Check that the last item is green
        last_item = dialog._palette_list.item(2)
        self.assertEqual(last_item.data(Qt.UserRole), QColor("green"))

    def test_dialog_eyedropper_updates_palette_and_tool(self):
        dialog = PixelEditorDialog(self.image)
        self.assertEqual(dialog._palette_list.count(), 2)

        # Eyedrop a new color (green)
        dialog._on_color_picked(QColor("green"))

        # Palette should now have 3 colors
        self.assertEqual(dialog._palette_list.count(), 3)
        # Active tool should be Pencil
        self.assertTrue(dialog._mode_actions[PixelImageWidget.Tool.PENCIL].isChecked())

        # Eyedrop transparent
        dialog._on_color_picked(QColor(Qt.GlobalColor.transparent))
        # Palette size should not change (transparent is not added)
        self.assertEqual(dialog._palette_list.count(), 3)
        # Active tool should be Eraser
        self.assertTrue(dialog._mode_actions[PixelImageWidget.Tool.ERASER].isChecked())


if __name__ == "__main__":
    unittest.main()
