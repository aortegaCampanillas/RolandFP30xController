#!/usr/bin/env python3
"""Convierte un SVG a PNG usando PySide6 QSvgRenderer.

Uso:
  python scripts/svg_to_png.py <input.svg> <output.png> [size]

size: resolución del cuadrado de salida (defecto: 1024).
"""
from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 3:
        print(f"Uso: {sys.argv[0]} <input.svg> <output.png> [size]", file=sys.stderr)
        return 1

    svg_path = Path(sys.argv[1])
    png_path = Path(sys.argv[2])
    size = int(sys.argv[3]) if len(sys.argv) > 3 else 1024

    if not svg_path.is_file():
        print(f"Error: no se encuentra {svg_path}", file=sys.stderr)
        return 1

    # QApplication mínima (necesaria para QSvgRenderer)
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer
    from PySide6.QtWidgets import QApplication

    _app = QApplication.instance() or QApplication(sys.argv[:1])

    renderer = QSvgRenderer(str(svg_path))
    if not renderer.isValid():
        print(f"Error: SVG inválido: {svg_path}", file=sys.stderr)
        return 1

    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    painter = QPainter(img)
    renderer.render(painter)
    painter.end()

    if not img.save(str(png_path), "PNG"):
        print(f"Error: no se pudo guardar {png_path}", file=sys.stderr)
        return 1

    print(f"Guardado: {png_path} ({size}x{size})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
