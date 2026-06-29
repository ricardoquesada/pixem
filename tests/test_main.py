# Pixem
# Copyright 2026 - Ricardo Quesada

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Ensure src is in path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from PySide6.QtWidgets import QApplication

from main import main
from main_window import MainWindow


class TestMainArgParsing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create QApplication instance if it doesn't exist (needed for MainWindow)
        cls.app = QApplication.instance() or QApplication([])

    @patch("main.QTranslator")
    @patch("main.QApplication")
    @patch("main.MainWindow")
    def test_main_no_args(self, mock_main_window, mock_qapp, mock_qtranslator):
        # Mock sys.argv to have no arguments
        with patch.object(sys, "argv", ["main.py"]):
            # We mock app.exec to exit immediately
            mock_app_instance = MagicMock()
            mock_qapp.instance.return_value = mock_app_instance
            mock_qapp.return_value = mock_app_instance

            # Run main, but catch SystemExit since sys.exit(app.exec()) is called
            with self.assertRaises(SystemExit):
                main()

            mock_main_window.assert_called_once_with(filename=None)

    @patch("main.QTranslator")
    @patch("main.QApplication")
    @patch("main.MainWindow")
    def test_main_with_file_arg(self, mock_main_window, mock_qapp, mock_qtranslator):
        test_file = "examples/guali_adidas.png"
        with patch.object(sys, "argv", ["main.py", test_file]):
            mock_app_instance = MagicMock()
            mock_qapp.instance.return_value = mock_app_instance
            mock_qapp.return_value = mock_app_instance

            with self.assertRaises(SystemExit):
                main()

            mock_main_window.assert_called_once_with(filename=test_file)


class TestMainWindowOpenFile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = MainWindow()

    def tearDown(self):
        # Clean up window
        self.window.close()

    def test_open_image_file_via_cli(self):
        test_file = os.path.join(os.path.dirname(__file__), "../examples/guali_adidas.png")
        self.assertTrue(os.path.exists(test_file), f"Test image not found at {test_file}")

        # Call open_file
        self.window.open_file(test_file)

        # Since open_file parses the image asynchronously, we must pump events
        # until the worker finishes. We wait up to 5 seconds.
        import time

        from PySide6.QtCore import QCoreApplication

        start_time = time.time()
        while len(self.window._active_workers) > 0:
            QCoreApplication.processEvents()
            time.sleep(0.05)
            if time.time() - start_time > 5.0:
                self.fail("Timed out waiting for image parsing to complete")

        # Now verify that the document was created and the layer was added
        self.assertIsNotNone(self.window.active_document)
        self.assertIsNotNone(self.window.state)
        self.assertEqual(len(self.window.state.layers), 1)

        layer = self.window.state.layers[0]
        self.assertEqual(layer.name, "ImageLayer 1")
        # Verify that partitions were created
        self.assertTrue(len(layer.partitions) > 0)

        # Mark state as clean to avoid "unsaved changes" dialog
        self.window.state.undo_stack.setClean()


if __name__ == "__main__":
    unittest.main()
