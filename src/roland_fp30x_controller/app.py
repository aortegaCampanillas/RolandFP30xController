from __future__ import annotations

import argparse
import sys

from PySide6.QtWidgets import QApplication

import roland_fp30x_controller.midi  # noqa: F401 — exporta API MIDI pública
from roland_fp30x_controller.ui.main_window import MainWindow

DARK_STYLE = """
QMainWindow { background-color: #1a1a1e; }

QWidget { background-color: #1a1a1e; color: #e0e0e0; font-size: 14px; }

QScrollArea { border: none; background-color: #1a1a1e; }
QScrollArea > QWidget > QWidget { background-color: #1a1a1e; }

QTabWidget::pane { border: none; background-color: #1a1a1e; margin-top: 0; }
QTabBar { background-color: transparent; qproperty-drawBase: 0; }
QTabBar::tab {
    background-color: transparent;
    color: #888888;
    padding: 10px 24px;
    font-size: 15px;
    border: none;
    border-bottom: 2px solid transparent;
}
QTabBar::tab:selected { color: #e0e0e0; border-bottom: 2px solid #E07828; }
QTabBar::tab:hover:!selected { color: #bbbbbb; }

QSlider::groove:horizontal {
    height: 4px; background: #3a3a3c; border-radius: 2px; margin: 0;
}
QSlider::sub-page:horizontal {
    background: #E07828; height: 4px; border-radius: 2px;
}
QSlider::add-page:horizontal {
    background: #3a3a3c; height: 4px; border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #E07828; border: none;
    width: 22px; height: 22px; border-radius: 11px; margin: -9px 0;
}
QSlider::handle:horizontal:hover { background: #f09040; }
QSlider:disabled::handle:horizontal { background: #555555; }
QSlider:disabled::sub-page:horizontal { background: #444444; }

QPushButton {
    background-color: #2c2c2e; color: #e0e0e0;
    border: 1px solid #484848; border-radius: 8px;
    padding: 8px 18px; font-size: 14px; min-height: 32px;
}
QPushButton:hover { background-color: #3a3a3c; border-color: #5a5a5a; }
QPushButton:pressed { background-color: #1c1c1e; }
QPushButton:disabled { color: #555555; background-color: #252527; border-color: #333333; }

QComboBox {
    background-color: #2c2c2e; color: #e0e0e0;
    border: 1px solid #484848; border-radius: 8px;
    padding: 6px 12px 6px 14px; font-size: 14px; min-height: 32px;
}
QComboBox:hover { border-color: #5a5a5a; }
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 28px;
    border: none;
    border-left: 1px solid #484848;
    border-top-right-radius: 8px;
    border-bottom-right-radius: 8px;
}
QComboBox::down-arrow {
    width: 10px; height: 10px;
}
QComboBox QAbstractItemView {
    background-color: #2c2c2e; color: #e0e0e0;
    selection-background-color: #E07828; selection-color: #ffffff;
    border: 1px solid #484848; border-radius: 8px; outline: none;
    padding: 4px;
}

QLabel { color: #e0e0e0; background-color: transparent; }
QLabel#scaleLabel { color: #666666; font-size: 11px; }
QLabel#valueLabel { color: #E07828; font-weight: bold; }
QLabel#statusLabel { color: #888888; font-size: 12px; }

QCheckBox { color: #e0e0e0; spacing: 8px; }
QCheckBox::indicator {
    width: 22px; height: 22px;
    border: 2px solid #3a3a3c; border-radius: 4px; background: #2c2c2e;
}
QCheckBox::indicator:checked { background-color: #E07828; border-color: #E07828; }
QCheckBox:disabled { color: #555555; }
QCheckBox::indicator:disabled { border-color: #333333; background: #252527; }

QGroupBox { border: none; color: #666666; font-size: 12px; padding-top: 4px; margin-top: 4px; }
QGroupBox::title { subcontrol-origin: margin; left: 0; color: #666666; }

QMessageBox { background-color: #2c2c2e; }
QMessageBox QLabel { color: #e0e0e0; }
"""


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
    app.setStyleSheet(DARK_STYLE)
    window = MainWindow(verbose=verbose)
    window.show()
    return app.exec()
