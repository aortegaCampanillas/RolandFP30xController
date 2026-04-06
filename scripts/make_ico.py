#!/usr/bin/env python3
"""Genera app_icon.ico (multi-resolución) desde el SVG de la aplicación.

Uso:
  python scripts/make_ico.py [output.ico]

Requiere: PySide6 (ya instalado como dependencia), Pillow (pip install pillow).
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

SVG_PATH = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "roland_fp30x_controller"
    / "resources"
    / "app_icon.svg"
)
# Tamaños estándar para .ico de Windows (Explorer, barra de tareas, ALT+TAB…)
ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]


def main() -> int:
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("app_icon.ico")

    if not SVG_PATH.is_file():
        print(f"Error: no se encuentra {SVG_PATH}", file=sys.stderr)
        return 1

    try:
        from PIL import Image
    except ImportError:
        print("Error: instala Pillow  →  pip install pillow", file=sys.stderr)
        return 1

    from PySide6.QtCore import Qt
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer
    from PySide6.QtWidgets import QApplication

    _app = QApplication.instance() or QApplication(sys.argv[:1])

    renderer = QSvgRenderer(str(SVG_PATH))
    if not renderer.isValid():
        print(f"Error: SVG inválido: {SVG_PATH}", file=sys.stderr)
        return 1

    pil_images: list[Image.Image] = []
    with tempfile.TemporaryDirectory() as tmp:
        for size in ICO_SIZES:
            img = QImage(size, size, QImage.Format.Format_ARGB32)
            img.fill(Qt.GlobalColor.transparent)
            painter = QPainter(img)
            renderer.render(painter)
            painter.end()

            png_path = Path(tmp) / f"icon_{size}.png"
            if not img.save(str(png_path), "PNG"):
                print(f"Error: no se pudo renderizar {size}x{size}", file=sys.stderr)
                return 1

            pil_images.append(Image.open(png_path).convert("RGBA"))
            # Mantener abierto hasta guardar el ICO (Pillow lee lazy)
            pil_images[-1].load()

    pil_images[0].save(
        str(out_path),
        format="ICO",
        sizes=[(s, s) for s in ICO_SIZES],
        append_images=pil_images[1:],
    )
    print(f"Generado: {out_path} ({', '.join(str(s) for s in ICO_SIZES)} px)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
