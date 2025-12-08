import os
import sys

from PySide6.QtWidgets import QApplication

# Adjust path to import source
sys.path.append(os.getcwd())
try:
    from PySide6.QtGui import QColor, QImage

    from layer import ImageLayer
    from main_window import MainWindow
except ImportError:
    # If running from tests/ or similar, adjust path
    sys.path.append(os.path.join(os.getcwd(), "../src"))
    from PySide6.QtGui import QColor, QImage

    from layer import ImageLayer
    from main_window import MainWindow


def test_aspect_ratio_ui():
    QApplication.instance() or QApplication(sys.argv)

    window = MainWindow()
    # Create a new project to initialize state
    window._on_new_project()

    # Create a dummy layer
    image = QImage(100, 100, QImage.Format.Format_ARGB32)
    image.fill(QColor("white"))
    layer = ImageLayer(image)
    layer.name = "Test Layer"
    window._add_layer(layer)

    # Access widgets (using private attributes as this is a white-box test)
    width_spin = window._pixel_width_spinbox
    height_spin = window._pixel_height_spinbox
    ratio_combo = window._pixel_aspect_ratio_combo

    print("Initial State:")
    print(f"  Mode: {ratio_combo.currentText()}")
    print(f"  Width: {width_spin.value()}")
    print(f"  Height: {height_spin.value()}")
    print(f"  Height Enabled: {height_spin.isEnabled()}")

    # Test 1: Change to VGA / NTSC
    print("\nTest 1: Change to VGA / NTSC")
    ratio_combo.setCurrentText("VGA / NTSC")
    # Manually trigger signal if programmatic change doesn't trigger it (it usually doesn't for setCurrentText in PySide6? Wait, it depends)
    # Actually, let's call the slot directly to be sure we are testing the logic,
    # capturing the user interaction flow is better but direct slot call is safer for unit test script
    window._on_pixel_aspect_ratio_changed()

    expected_height = width_spin.value() * 1.2
    print(f"  Mode: {ratio_combo.currentText()}")
    print(f"  Height: {height_spin.value()} (Expected: {expected_height})")
    print(f"  Height Enabled: {height_spin.isEnabled()}")

    if abs(height_spin.value() - expected_height) > 0.001:
        print("FAIL: Height incorrect for VGA / NTSC")
        sys.exit(1)
    if height_spin.isEnabled():
        print("FAIL: Height should be disabled")
        sys.exit(1)

    # Test 2: Change Width
    print("\nTest 2: Change Width")
    new_width = 5.0
    width_spin.setValue(new_width)
    window._on_pixel_width_changed()  # Simulate user interaction

    expected_height = new_width * 1.2
    print(f"  Width: {width_spin.value()}")
    print(f"  Height: {height_spin.value()} (Expected: {expected_height})")

    if abs(height_spin.value() - expected_height) > 0.001:
        print("FAIL: Height did not update correctly")
        sys.exit(1)

    # Test 3: Change to PAL-N
    print("\nTest 3: Change to PAL-N")
    ratio_combo.setCurrentText("PAL-N")
    window._on_pixel_aspect_ratio_changed()

    expected_height = new_width * 0.83
    print(f"  Height: {height_spin.value()} (Expected: {expected_height})")

    if abs(height_spin.value() - expected_height) > 0.001:
        print("FAIL: Height incorrect for PAL-N")
        sys.exit(1)

    # Test 4: Change to Freeform
    print("\nTest 4: Change to Freeform")
    ratio_combo.setCurrentText("Freeform")
    window._on_pixel_aspect_ratio_changed()

    print(f"  Height Enabled: {height_spin.isEnabled()}")
    if not height_spin.isEnabled():
        print("FAIL: Height should be enabled")
        sys.exit(1)

    print("\nSUCCESS: All tests passed")


if __name__ == "__main__":
    test_aspect_ratio_ui()
