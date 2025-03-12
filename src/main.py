# Pixem
# Copyright 2024 Ricardo Quesada

import logging
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

import rc_resources  # noqa: F401
from main_window import MainWindow

logger = logging.getLogger(__name__)


def main():
    # Configure logging (do this once, ideally at the start of your application)
    logging.basicConfig(
        # filename="pixem.log",
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",  # Customize the date format
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Pixem")
    app.setOrganizationName("Retro Moe")
    app.setOrganizationDomain("moe.retro")
    app.setWindowIcon(QIcon(":/res/icons/pixem.png"))

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
