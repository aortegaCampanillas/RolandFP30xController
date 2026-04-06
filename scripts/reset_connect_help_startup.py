#!/usr/bin/env python3
"""Quita el ajuste «no volver a mostrar la ayuda de conexión al arrancar».

Si marcaste esa casilla en el diálogo que aparece al iniciar la app, el valor se
guarda en QSettings bajo la clave ``connect_help_skip_startup``. Este script la
elimina para que la próxima vez que arranques la aplicación vuelva a mostrarse
la ayuda (si no la abres desde el botón Ayuda, que no modifica ese flag).

Uso (desde la raíz del repo, con el venv activado):

    python scripts/reset_connect_help_startup.py
"""

from __future__ import annotations

import sys

from PySide6.QtCore import QCoreApplication, QSettings

_ORG = "RolandFP30xController"
_APP = "RolandFP30xController"
_KEY = "connect_help_skip_startup"


def main() -> int:
    _ = QCoreApplication(sys.argv)
    settings = QSettings(_ORG, _APP)
    had = settings.contains(_KEY)
    settings.remove(_KEY)
    settings.sync()
    if settings.status() != QSettings.Status.NoError:
        print("Error al sincronizar QSettings.", file=sys.stderr)
        return 1
    if had:
        print(f"Eliminada la clave «{_KEY}»: la ayuda al arranque volverá a mostrarse.")
    else:
        print(f"No existía «{_KEY}»; no hacía falta limpiar nada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
