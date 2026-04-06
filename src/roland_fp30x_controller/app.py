from __future__ import annotations

import argparse
import sys
from pathlib import Path


from PySide6.QtCore import QBuffer, QByteArray, QIODevice, Qt
from PySide6.QtGui import QIcon, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

import roland_fp30x_controller.midi  # noqa: F401 — exporta API MIDI pública
from roland_fp30x_controller.ui.main_window import MainWindow

DARK_STYLE = """
QMainWindow { background-color: #1a1a1e; }

QWidget { background-color: #1a1a1e; color: #e0e0e0; font-size: 13px; }

QScrollArea { border: none; background-color: #1a1a1e; }
QScrollArea > QWidget > QWidget { background-color: #1a1a1e; }

QTabWidget::pane { border: none; background-color: #1a1a1e; margin-top: 0; }
QTabBar { background-color: transparent; qproperty-drawBase: 0; }
QTabBar::tab {
    background-color: transparent;
    color: #888888;
    padding: 6px 14px;
    font-size: 13px;
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
    border: 1px solid #484848; border-radius: 6px;
    padding: 3px 10px; font-size: 13px; min-height: 22px;
}
QPushButton:hover { background-color: #3a3a3c; border-color: #5a5a5a; }
QPushButton:pressed { background-color: #1c1c1e; }
QPushButton:disabled { color: #555555; background-color: #252527; border-color: #333333; }

/* Botones +/- compactos (split point, tono): padding 0 para el glifo */
QPushButton#stepperButton {
    padding: 2px 2px;
    min-width: 28px;
    max-width: 36px;
    min-height: 22px;
    font-size: 15px;
    font-weight: bold;
}

QComboBox {
    background-color: #2c2c2e;
    color: #e0e0e0;
    border: 1px solid #484848;
    border-radius: 6px;
    padding: 2px 8px 2px 8px;
    padding-right: 26px;
    font-size: 13px;
    min-height: 22px;
    combobox-popup: 0;
}
QComboBox:hover:!disabled { border-color: #5a5a5a; }
QComboBox:focus { border-color: #E07828; }
QComboBox:on { border-color: #E07828; }
QComboBox:disabled {
    color: #666666;
    background-color: #252527;
    border-color: #333333;
}
/* Zona de la flecha: sin línea ni recuadro; mismo fondo que el combo */
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 22px;
    border: none;
    background: transparent;
}
QComboBox:disabled::drop-down {
    background: transparent;
}
/* Flecha tipo caret (∨) dibujada con bordes */
QComboBox::down-arrow {
    width: 0;
    height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #a8a8a8;
    margin-right: 7px;
}
QComboBox:hover:!disabled::down-arrow { border-top-color: #e0e0e0; }
QComboBox:on::down-arrow { border-top-color: #E07828; }
QComboBox:disabled::down-arrow {
    border-top-color: #555555;
    border-left-color: transparent;
    border-right-color: transparent;
}
QComboBox QAbstractItemView {
    background-color: #2c2c2e;
    color: #e0e0e0;
    selection-background-color: #E07828;
    selection-color: #ffffff;
    border: 1px solid #484848;
    border-radius: 8px;
    outline: none;
    padding: 4px;
}
QComboBox QAbstractItemView::item {
    min-height: 20px;
    padding: 2px 8px;
    border-radius: 4px;
}
QComboBox QAbstractItemView::item:hover {
    background-color: #3a3a3c;
}
QComboBox QAbstractItemView::item:selected {
    background-color: #E07828;
    color: #ffffff;
}
QComboBox QAbstractItemView QScrollBar:vertical {
    width: 10px;
    background: #252527;
    border: none;
    border-radius: 4px;
    margin: 2px;
}
QComboBox QAbstractItemView QScrollBar::handle:vertical {
    background: #484848;
    border-radius: 4px;
    min-height: 24px;
}
QComboBox QAbstractItemView QScrollBar::handle:vertical:hover {
    background: #5a5a5a;
}
QComboBox QAbstractItemView QScrollBar::add-line:vertical,
QComboBox QAbstractItemView QScrollBar::sub-line:vertical {
    height: 0;
    subcontrol-origin: margin;
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


def _redirect_stderr_to_log_on_windows() -> None:
    """En Windows --windowed, sys.stderr es None y los prints de verbose se pierden.

    Redirige stderr (y stdout) a un fichero de log junto al ejecutable para que
    el modo /verbose produzca output útil. No hace nada en macOS/Linux ni cuando
    ya hay consola.
    """
    if sys.platform != "win32":
        return
    if sys.stderr is not None:
        return  # ya hay consola (p.ej. ejecutado desde cmd.exe con build de consola)
    try:
        log_path = Path(sys.executable).resolve().parent / "pianopilot_verbose.log"
        f = open(log_path, "w", encoding="utf-8", buffering=1)  # noqa: SIM115
        sys.stdout = f
        sys.stderr = f
    except OSError:
        pass  # sin permisos de escritura → sin log, no fatal


def _application_icon() -> QIcon:
    """Icono propio (SVG en paquete); sin marca ni diseño de producto Roland."""
    path = Path(__file__).resolve().parent / "resources" / "app_icon.svg"
    if path.is_file():
        return QIcon(str(path))
    return QIcon()


def _app_icon_svg_path() -> Path:
    return Path(__file__).resolve().parent / "resources" / "app_icon.svg"


def _raster_app_icon_svg_to_png_bytes(svg_path: Path, size: int = 512) -> bytes | None:
    """Rasteriza el SVG a PNG en memoria (para NSImage en macOS). Requiere QApplication viva."""
    renderer = QSvgRenderer(str(svg_path))
    if not renderer.isValid():
        return None
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    painter = QPainter(img)
    renderer.render(painter)
    painter.end()
    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    if not img.save(buf, "PNG"):
        return None
    buf.close()
    return bytes(ba)


def _set_macos_process_icon_from_png(png_bytes: bytes) -> None:
    """Dock y conmutador de apps (p. ej. Cmd+Tab): macOS usa el binario del proceso (Python),
    no `QApplication.setWindowIcon`. Se asigna vía AppKit cuando PyObjC está disponible."""
    if sys.platform != "darwin":
        return
    try:
        from AppKit import NSApplication, NSImage
        from Foundation import NSData
    except ImportError:
        return
    data = NSData.dataWithBytes_length_(png_bytes, len(png_bytes))
    image = NSImage.alloc().initWithData_(data)
    if image is None:
        return
    NSApplication.sharedApplication().setApplicationIconImage_(image)


def run(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    # Compatibilidad con /verbose y /debug (estilo Windows).
    filtered: list[str] = []
    verbose_slash = False
    debug_slash = False
    for item in argv:
        if item == "/verbose":
            verbose_slash = True
        elif item == "/debug":
            debug_slash = True
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
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Activa utilidades de depuracion de la UI, incluido 'Read Piano Values'.",
    )
    args, qt_argv = parser.parse_known_args(filtered)
    verbose = args.verbose or verbose_slash
    debug = args.debug or debug_slash
    if verbose or debug:
        _redirect_stderr_to_log_on_windows()
    app = QApplication([sys.argv[0], *qt_argv])
    app.setWindowIcon(_application_icon())
    if sys.platform == "darwin":
        svg = _app_icon_svg_path()
        if svg.is_file():
            png = _raster_app_icon_svg_to_png_bytes(svg)
            if png:
                _set_macos_process_icon_from_png(png)
    # Fusion hace que QSS se aplique al QComboBox completo. Con el estilo nativo de macOS,
    # Qt mezcla widgets nativos y el stylesheet: línea divisoria y “rectángulo” en vez de flecha.
    app.setStyle("Fusion")
    app.setStyleSheet(DARK_STYLE)
    window = MainWindow(verbose=verbose, debug=debug)
    window.show()
    return app.exec()
