"""Parseo de mensajes SysEx Roland DT1 entrantes."""

from __future__ import annotations

import mido

from roland_fp30x_controller.midi.messages import (
    FP30X_MODEL_ID,
    ROLAND_CMD_DT1,
    ROLAND_DEVICE_ID,
    ROLAND_ID,
)

# Índice del primer byte de dirección dentro de msg.data (tras ROLAND_ID, DEVICE_ID, MODEL_ID×4, CMD)
_ADDR_OFFSET = 7  # data[0..6] = id, dev, m0, m1, m2, m3, cmd
_MIN_DT1_DATA_LEN = _ADDR_OFFSET + 4 + 1 + 1  # addr×4 + ≥1 dato + checksum


def parse_roland_dt1(
    msg: mido.Message,
) -> tuple[tuple[int, int, int, int], tuple[int, ...]] | None:
    """Devuelve (address, data_bytes) si el mensaje es un DT1 del FP-30X, o None.

    El último byte del payload es el checksum y se descarta del resultado.
    """
    if msg.type != "sysex":
        return None
    d = msg.data
    if len(d) < _MIN_DT1_DATA_LEN:
        return None
    if d[0] != ROLAND_ID:
        return None
    if d[1] != ROLAND_DEVICE_ID:
        return None
    if tuple(d[2:6]) != FP30X_MODEL_ID:
        return None
    if d[6] != ROLAND_CMD_DT1:
        return None
    addr = (d[7], d[8], d[9], d[10])
    # d[11 .. -1] son los bytes de datos; d[-1] es el checksum
    data = tuple(d[11:-1])
    if not data:
        return None
    return addr, data
