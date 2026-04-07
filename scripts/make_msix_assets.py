#!/usr/bin/env python3
"""Genera los assets PNG requeridos para el paquete MSIX de la Windows Store.

Uso:
  python scripts/make_msix_assets.py [output_dir]

output_dir: directorio de salida (defecto: packaging/windows/Assets)

Assets generados (tamaños mínimos requeridos por el Store):
  Square44x44Logo.png    -  44 x  44
  Square150x150Logo.png  - 150 x 150
  Square310x310Logo.png  - 310 x 310
  StoreLogo.png          -  50 x  50
  Wide310x150Logo.png    - 310 x 150  (SVG centrado con padding lateral)
  SplashScreen.png       - 620 x 300  (SVG centrado con padding lateral)
"""
from __future__ import annotations

import sys
from pathlib import Path

SVG_PATH = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "roland_fp30x_controller"
    / "resources"
    / "app_icon.svg"
)

# (nombre_archivo, ancho, alto)
ASSETS: list[tuple[str, int, int]] = [
    ("Square44x44Logo.png", 44, 44),
    ("Square150x150Logo.png", 150, 150),
    ("Square310x310Logo.png", 310, 310),
    ("StoreLogo.png", 50, 50),
    ("Wide310x150Logo.png", 310, 150),
    ("SplashScreen.png", 620, 300),
]


def render_asset(renderer, w: int, h: int, png_path: Path) -> bool:
    from PySide6.QtCore import QRect, Qt
    from PySide6.QtGui import QImage, QPainter

    img = QImage(w, h, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    painter = QPainter(img)

    # El SVG es cuadrado: lo centramos dentro del rectángulo destino.
    size = min(w, h)
    x = (w - size) // 2
    y = (h - size) // 2
    renderer.render(painter, QRect(x, y, size, size))
    painter.end()

    if not img.save(str(png_path), "PNG"):
        print(f"Error: no se pudo guardar {png_path}", file=sys.stderr)
        return False

    print(f"  {png_path.name} ({w}x{h})")
    return True


def main() -> int:
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("packaging/windows/Assets")
    out_dir.mkdir(parents=True, exist_ok=True)

    if not SVG_PATH.is_file():
        print(f"Error: no se encuentra {SVG_PATH}", file=sys.stderr)
        return 1

    from PySide6.QtSvg import QSvgRenderer
    from PySide6.QtWidgets import QApplication

    _app = QApplication.instance() or QApplication(sys.argv[:1])

    renderer = QSvgRenderer(str(SVG_PATH))
    if not renderer.isValid():
        print(f"Error: SVG inválido: {SVG_PATH}", file=sys.stderr)
        return 1

    print(f"Generando assets en {out_dir}/")
    for filename, w, h in ASSETS:
        if not render_asset(renderer, w, h, out_dir / filename):
            return 1

    print("Listo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
