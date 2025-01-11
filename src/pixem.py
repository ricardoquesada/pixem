# Pixem
# Copyright 2024 Ricardo Quesada

import sys

from PySide6.QtCore import (
    QCoreApplication,
)

from PySide6.QtWidgets import (
    QApplication,
)

from main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    QCoreApplication.setApplicationName("Pixem")
    QCoreApplication.setOrganizationName("Retro Moe")
    QCoreApplication.setOrganizationDomain("retro.moe")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
