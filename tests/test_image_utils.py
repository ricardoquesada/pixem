import os
import sys
import unittest

# Ensure src is in path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from PySide6.QtGui import QColor, QImage

from image_utils import (
    _ascii_to_petscii_screencode,
    base64_string_to_qimage,
    qimage_to_base64_string,
    rotated_rectangle_dimensions,
)


class TestImageUtils(unittest.TestCase):
    def test_base64_roundtrip(self):
        # Create a simple image
        image = QImage(10, 10, QImage.Format_ARGB32)
        image.fill(QColor("red"))

        # Encode
        b64_str = qimage_to_base64_string(image, "PNG")
        self.assertIsNotNone(b64_str)
        self.assertGreater(len(b64_str), 0)

        # Decode
        decoded_image = base64_string_to_qimage(b64_str)
        self.assertFalse(decoded_image.isNull())
        self.assertEqual(decoded_image.width(), 10)
        self.assertEqual(decoded_image.height(), 10)
        self.assertEqual(decoded_image.pixelColor(0, 0), QColor("red"))

    def test_base64_none_input(self):
        self.assertIsNone(qimage_to_base64_string(None))

    def test_base64_invalid_string(self):
        # Invalid base64 string
        img = base64_string_to_qimage("NotValidBase64!!")
        # Should return null image (isNull() == True)
        self.assertTrue(img.isNull())

    def test_ascii_to_petscii(self):
        # Test valid conversions
        # 'A' (65) -> PETSCII 193 -> Screen Code 65
        self.assertEqual(_ascii_to_petscii_screencode("A"), 65)
        # 'a' (97) -> PETSCII 65 -> Screen Code 1
        self.assertEqual(_ascii_to_petscii_screencode("a"), 1)

        # '@' (64) -> PETSCII 64 (0x40).
        # Logic: if <= 63: change nothing? Wait.
        # table[64] = 0xC0 (192).
        # 192 is <= 223? No. <= 254? Yes.
        # Logic: if <= 223: petscii -= 128.
        # 192 - 128 = 64.
        self.assertEqual(_ascii_to_petscii_screencode("@"), 0)

        # ' ' (32) -> table[32] = 0x20 (32).
        # if <= 31: +128. else if <= 63: pass.
        # So 32 remains 32.
        self.assertEqual(_ascii_to_petscii_screencode(" "), 32)

        # Invalid input
        self.assertIsNone(_ascii_to_petscii_screencode("AB"))  # Too long

    def test_rotated_rectangle_dimensions(self):
        # 0 degrees
        w, h = rotated_rectangle_dimensions(100, 50, 0)
        self.assertAlmostEqual(w, 100)
        self.assertAlmostEqual(h, 50)

        # 90 degrees
        w, h = rotated_rectangle_dimensions(100, 50, 90)
        self.assertAlmostEqual(w, 50)
        self.assertAlmostEqual(h, 100)

        # 180 degrees
        w, h = rotated_rectangle_dimensions(100, 50, 180)
        self.assertAlmostEqual(w, 100)
        self.assertAlmostEqual(h, 50)

        # 45 degrees
        # cos(45) = sin(45) ~= 0.7071
        # w = 100*0.7071 + 50*0.7071 = 150*0.7071 = 106.065
        # h = 100*0.7071 + 50*0.7071 = 106.065
        w, h = rotated_rectangle_dimensions(100, 50, 45)
        self.assertAlmostEqual(w, 106.066, places=3)
        self.assertAlmostEqual(h, 106.066, places=3)


if __name__ == "__main__":
    unittest.main()
