from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

import roland_fp30x_controller.midi  # noqa: F401 — exporta API MIDI pública
from roland_fp30x_controller.ui.main_window import MainWindow


def run() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()
