from __future__ import annotations

from typing import Any

import mido
from PySide6.QtCore import QThread, Signal


class MidiInWorker(QThread):
    """Lee mensajes MIDI de entrada en un hilo aparte (no bloquea la UI)."""

    message_received = Signal(object)

    def __init__(self, port_name: str) -> None:
        super().__init__()
        self._port_name = port_name
        self._port: Any = None

    def run(self) -> None:
        port = mido.open_input(self._port_name)
        self._port = port
        if self.isInterruptionRequested():
            port.close()
            self._port = None
            return
        try:
            for msg in port:
                if self.isInterruptionRequested():
                    break
                self.message_received.emit(msg)
        finally:
            if self._port is not None:
                try:
                    self._port.close()
                except OSError:
                    pass
                self._port = None

    def stop_safely(self) -> None:
        self.requestInterruption()
        p = self._port
        if p is not None:
            try:
                p.close()
            except OSError:
                pass
