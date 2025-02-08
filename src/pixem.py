# Pixem
# Copyright 2024 Ricardo Quesada

import sys
import logging

from PySide6.QtCore import (
    QCoreApplication,
)

from PySide6.QtWidgets import (
    QApplication,
)

from main_window import MainWindow

logger = logging.getLogger(__name__)  # __name__ gets the current module's name


def main():
    # Configure logging (do this once, ideally at the start of your application)
    logging.basicConfig(
        # filename="pixem.log",
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",  # Customize the date format
    )

    app = QApplication(sys.argv)
    QCoreApplication.setApplicationName("Pixem")
    QCoreApplication.setOrganizationName("Retro Moe")
    QCoreApplication.setOrganizationDomain("retro.moe")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
