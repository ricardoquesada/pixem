import sys

from PySide6.QtWidgets import QApplication

sys.path.append("src")
from main_window import MainWindow

if not QApplication.instance():
    app = QApplication([])

window = MainWindow()
if hasattr(window, "_on_layer_duplicate"):
    print("Method exists!")
else:
    print("Method MISSING!")
