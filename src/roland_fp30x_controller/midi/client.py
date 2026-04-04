from __future__ import annotations

import time
from collections.abc import Iterable
from typing import Any

import mido

mido.set_backend("mido.backends.rtmidi")


class MidiOutClient:
    """Salida MIDI (mido + backend python-rtmidi)."""

    def __init__(self) -> None:
        self._port: Any = None

    @property
    def is_open(self) -> bool:
        return self._port is not None

    def open(self, port_name: str) -> None:
        self.close()
        self._port = mido.open_output(port_name)

    def close(self) -> None:
        if self._port is not None:
            self._port.close()
            self._port = None

    def send(self, message: mido.Message) -> None:
        if self._port is None:
            msg = "No hay puerto MIDI de salida abierto"
            raise RuntimeError(msg)
        self._port.send(message)

    def send_all(self, messages: Iterable[mido.Message]) -> None:
        for m in messages:
            self.send(m)

    def send_all_spaced(
        self, messages: Iterable[mido.Message], gap_s: float = 0.0
    ) -> None:
        first = True
        for m in messages:
            if not first and gap_s > 0:
                time.sleep(gap_s)
            first = False
            self.send(m)
