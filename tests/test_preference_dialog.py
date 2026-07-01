# Pixem
# Copyright 2026 - Ricardo Quesada

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Ensure src is in path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from PySide6.QtWidgets import QApplication

from preference_dialog import PreferenceDialog


class MockSettings:
    def __init__(self):
        self.hoop_size = (4.0, 4.0)
        self.hoop_visible = True
        self.partition_foreground_color_name = "#800000ff"
        self.partition_background_color_name = "#80ff0000"
        self.canvas_background_color_name = "#a0a0a0ff"
        self.hoop_color_name = "#c0c0c0ff"
        self.delete_point_enabled = False
        self.open_file_on_startup = True

    def get_hoop_size(self) -> tuple[float, float]:
        return self.hoop_size

    def set_hoop_size(self, size: tuple[float, float]) -> None:
        self.hoop_size = size

    def get_hoop_visible(self) -> bool:
        return self.hoop_visible

    def set_hoop_visible(self, visible: bool) -> None:
        self.hoop_visible = visible

    def get_partition_foreground_color_name(self) -> str:
        return self.partition_foreground_color_name

    def set_partition_foreground_color_name(self, color: str) -> None:
        self.partition_foreground_color_name = color

    def get_partition_background_color_name(self) -> str:
        return self.partition_background_color_name

    def set_partition_background_color_name(self, color: str) -> None:
        self.partition_background_color_name = color

    def get_canvas_background_color_name(self) -> str:
        return self.canvas_background_color_name

    def set_canvas_background_color_name(self, color: str) -> None:
        self.canvas_background_color_name = color

    def get_hoop_color_name(self) -> str:
        return self.hoop_color_name

    def set_hoop_color_name(self, color: str) -> None:
        self.hoop_color_name = color

    def get_delete_point_enabled(self) -> bool:
        return self.delete_point_enabled

    def set_delete_point_enabled(self, enabled: bool) -> None:
        self.delete_point_enabled = enabled

    def get_open_file_on_startup(self) -> bool:
        return self.open_file_on_startup

    def set_open_file_on_startup(self, value: bool) -> None:
        self.open_file_on_startup = value


class TestPreferenceDialog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.mock_global_prefs = MagicMock()
        self.mock_global_prefs.get_canvas_handle_color_name.return_value = "#ff007acd"

        # Patch get_global_preferences to return our mock
        self.patcher = patch(
            "preference_dialog.get_global_preferences", return_value=self.mock_global_prefs
        )
        self.patcher.start()

        self.settings = MockSettings()
        self.dialog = PreferenceDialog(self.settings)

    def tearDown(self):
        self.patcher.stop()

    def test_init_with_preset_size(self):
        # The mock settings has hoop_size (4.0, 4.0)
        # This matches the 4x4 preset.
        self.assertTrue(self.dialog._hoop_4_4_radio.isChecked())
        self.assertFalse(self.dialog._hoop_custom_radio.isChecked())
        self.assertFalse(self.dialog._custom_size_x_spinbox.isEnabled())

    def test_init_with_custom_size(self):
        # Set a size that doesn't match any preset (e.g. 8x8)
        self.settings.hoop_size = (8.0, 8.0)
        dialog = PreferenceDialog(self.settings)

        self.assertTrue(dialog._hoop_custom_radio.isChecked())
        self.assertTrue(dialog._custom_size_x_spinbox.isEnabled())
        self.assertAlmostEqual(dialog._custom_size_x_spinbox.value(), 8.0)
        self.assertAlmostEqual(dialog._custom_size_y_spinbox.value(), 8.0)
        self.assertEqual(dialog._custom_unit_combo.currentIndex(), 0)  # inches by default

    def test_custom_unit_conversion_to_mm(self):
        # Select custom radio
        self.dialog._hoop_custom_radio.setChecked(True)
        self.dialog._custom_size_x_spinbox.setValue(10.0)  # 10 inches
        self.dialog._custom_size_y_spinbox.setValue(5.0)  # 5 inches

        # Switch unit to mm
        self.dialog._custom_unit_combo.setCurrentIndex(1)  # mm

        # Values should be converted to mm (10 * 25.4 = 254.0, 5 * 25.4 = 127.0)
        self.assertAlmostEqual(self.dialog._custom_size_x_spinbox.value(), 254.0)
        self.assertAlmostEqual(self.dialog._custom_size_y_spinbox.value(), 127.0)
        self.assertEqual(self.dialog._custom_size_x_spinbox.suffix(), " mm")
        self.assertEqual(self.dialog._custom_size_x_spinbox.decimals(), 1)

    def test_custom_unit_conversion_to_inches(self):
        # Select custom radio and set to mm
        self.dialog._hoop_custom_radio.setChecked(True)
        self.dialog._custom_unit_combo.setCurrentIndex(1)  # mm
        self.dialog._custom_size_x_spinbox.setValue(100.0)  # 100 mm
        self.dialog._custom_size_y_spinbox.setValue(200.0)  # 200 mm

        # Switch unit to inches
        self.dialog._custom_unit_combo.setCurrentIndex(0)  # inches

        # Values should be converted to inches (100 / 25.4 = 3.937..., 200 / 25.4 = 7.874...)
        self.assertAlmostEqual(self.dialog._custom_size_x_spinbox.value(), 3.937, places=3)
        self.assertAlmostEqual(self.dialog._custom_size_y_spinbox.value(), 7.874, places=3)
        self.assertEqual(self.dialog._custom_size_x_spinbox.suffix(), " in")
        self.assertEqual(self.dialog._custom_size_x_spinbox.decimals(), 3)

    def test_apply_preset(self):
        # Change preset to 5x7
        self.dialog._hoop_5_7_radio.setChecked(True)
        self.dialog._apply()

        self.assertEqual(self.settings.hoop_size, (5.0, 7.0))

    def test_apply_custom_inches(self):
        self.dialog._hoop_custom_radio.setChecked(True)
        self.dialog._custom_unit_combo.setCurrentIndex(0)  # inches
        self.dialog._custom_size_x_spinbox.setValue(6.5)
        self.dialog._custom_size_y_spinbox.setValue(8.5)

        self.dialog._apply()

        self.assertEqual(self.settings.hoop_size, (6.5, 8.5))

    def test_apply_custom_mm(self):
        self.dialog._hoop_custom_radio.setChecked(True)
        self.dialog._custom_unit_combo.setCurrentIndex(1)  # mm
        self.dialog._custom_size_x_spinbox.setValue(100.0)  # 100 mm
        self.dialog._custom_size_y_spinbox.setValue(150.0)  # 150 mm

        self.dialog._apply()

        # Values should be saved in inches (100/25.4, 150/25.4)
        self.assertAlmostEqual(self.settings.hoop_size[0], 100.0 / 25.4)
        self.assertAlmostEqual(self.settings.hoop_size[1], 150.0 / 25.4)


if __name__ == "__main__":
    unittest.main()
