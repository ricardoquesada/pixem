#!/usr/bin/env python3
# Pixem
# Copyright 2024 Ricardo Quesada

import logging
import sys

from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from main_window import MainWindow
from res import rc_resources  # noqa: F401

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

    # System translations
    path = QLibraryInfo.path(QLibraryInfo.TranslationsPath)
    translator = QTranslator(app)
    if translator.load(QLocale.system(), "qtbase", "_", path):
        app.installTranslator(translator)

    translators = {
        "en": ":/translations/en/pixem_en.qm",
        "es": ":/translations/es/pixem_es.qm",
    }

    locale = QLocale.system()
    lang_code = locale.name()[:2]
    logger.info(f"Detected language: {lang_code}")

    if lang_code not in translators:
        lang_code = "en"
    path = translators[lang_code]
    translator = QTranslator()
    if not translator.load(path):
        logger.warning(f"Failed to load: {path}")
    else:
        app.installTranslator(translator)

    app.setApplicationName("Pixem")
    app.setApplicationDisplayName("Pixem")
    app.setDesktopFileName("Pixem")
    app.setOrganizationName("RetroMoe")
    app.setOrganizationDomain("retro.moe")
    app.setWindowIcon(QIcon(":/icons/pixem.png"))

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
