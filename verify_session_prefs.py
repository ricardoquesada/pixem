import sys
import unittest
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append("src")


from preferences import get_global_preferences


class TestSessionRestoration(unittest.TestCase):
    def setUp(self):
        # Mock QSettings to avoid messing with real config
        self.mock_settings = MagicMock()
        with patch("preferences.QSettings", return_value=self.mock_settings):
            # Reset singleton
            import preferences

            preferences._global_preferences = None
            self.prefs = get_global_preferences()

    def test_save_and_restore_files(self):
        files = ["/tmp/file1.pixemproj", "/tmp/file2.pixemproj"]

        # Test Saving
        self.prefs.set_open_files(files)
        self.mock_settings.setValue.assert_any_call("files/open_files", files)

        # Test Restoring
        self.mock_settings.value.side_effect = lambda key, defaultValue=None: (
            files if key == "files/open_files" else defaultValue
        )
        restored_files = self.prefs.get_open_files()
        self.assertEqual(restored_files, files)

    def test_active_file(self):
        active_file = "/tmp/file2.pixemproj"

        # Test Saving
        self.prefs.set_active_file(active_file)
        self.mock_settings.setValue.assert_any_call("files/active_file", active_file)

        # Test Restoring
        self.mock_settings.value.side_effect = lambda key, defaultValue=None: (
            active_file if key == "files/active_file" else defaultValue
        )
        restored_active = self.prefs.get_active_file()
        self.assertEqual(restored_active, active_file)


if __name__ == "__main__":
    unittest.main()
