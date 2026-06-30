# Pixem
# Copyright 2026 - Ricardo Quesada

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Ensure src is in path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from PySide6.QtWidgets import QApplication

from document import Document
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
            if time.time() - start_time > 15.0:
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


class TestMainWindowTabs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = MainWindow()

    def tearDown(self):
        # Mark all states as clean to avoid "unsaved changes" dialog on close
        for i in range(self.window._tab_widget.count()):
            doc = self.window._tab_widget.widget(i)
            if isinstance(doc, Document):
                doc.state.undo_stack.setClean()
        self.window.close()

    def test_tab_dirty_indicator(self):
        # 1. Create a new project (should have 1 tab "Untitled")
        self.window._on_new_project()
        self.assertEqual(self.window._tab_widget.count(), 1)
        self.assertEqual(self.window._tab_widget.tabText(0), "Untitled")
        self.assertEqual(self.window.windowTitle(), "(untitled) - Pixem")

        # 2. Make a change (add a layer)
        from PySide6.QtGui import QImage

        from layer import ImageLayer

        layer = ImageLayer(QImage(10, 10, QImage.Format_ARGB32))
        self.window.state.add_layer(layer)

        # 3. Verify tab title has asterisk and window title has asterisk
        self.assertEqual(self.window._tab_widget.tabText(0), "Untitled*")
        self.assertEqual(self.window.windowTitle(), "(untitled)* - Pixem")

        # 4. Undo the change
        self.window.state.undo_stack.undo()

        # 5. Verify tab title and window title are clean again
        self.assertEqual(self.window._tab_widget.tabText(0), "Untitled")
        self.assertEqual(self.window.windowTitle(), "(untitled) - Pixem")

        # 6. Make it dirty again
        self.window.state.add_layer(layer)
        self.assertEqual(self.window._tab_widget.tabText(0), "Untitled*")

        # 7. Save the project to a temp file
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".pixemproj", delete=False) as tmp:
            temp_filename = tmp.name

        try:
            # We simulate save by calling save_to_filename on state.
            # This should trigger cleanChanged and update the tab.
            self.window.state.save_to_filename(temp_filename)

            # Verify tab title is now the filename and NOT dirty
            expected_title = os.path.basename(temp_filename)
            self.assertEqual(self.window._tab_widget.tabText(0), expected_title)
            self.assertEqual(self.window.windowTitle(), f"{expected_title} - Pixem")
        finally:
            if os.path.exists(temp_filename):
                os.remove(temp_filename)


if __name__ == "__main__":
    unittest.main()
