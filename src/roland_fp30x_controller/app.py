from __future__ import annotations

import argparse
import sys

from PySide6.QtWidgets import QApplication

import roland_fp30x_controller.midi  # noqa: F401 — exporta API MIDI pública
from roland_fp30x_controller.ui.main_window import MainWindow


def run(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    # Compatibilidad con /verbose (estilo Windows); en Python lo habitual es --verbose o -v.
    filtered: list[str] = []
    verbose_slash = False
    for item in argv:
        if item == "/verbose":
            verbose_slash = True
        else:
            filtered.append(item)
    parser = argparse.ArgumentParser(
        prog="roland_fp30x_controller",
        description="Controlador MIDI para Roland FP-30X.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Escribe en stderr todo el MIDI enviado y recibido (trazas).",
    )
    args, qt_argv = parser.parse_known_args(filtered)
    verbose = args.verbose or verbose_slash
    app = QApplication([sys.argv[0], *qt_argv])
    window = MainWindow(verbose=verbose)
    window.show()
    return app.exec()
