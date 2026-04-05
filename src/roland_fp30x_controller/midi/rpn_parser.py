"""Interpreta secuencias RPN por canal para extraer coarse tuning."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import mido


@dataclass
class _RpnState:
    rpn_msb: int = 127
    rpn_lsb: int = 127


class RpnParser:
    """Devuelve semitonos cuando llega RPN 0,2 (coarse tuning)."""

    def __init__(self, channels_1_16: int | Sequence[int]) -> None:
        if isinstance(channels_1_16, int):
            chs = (channels_1_16,)
        else:
            chs = tuple(channels_1_16)
        if not chs:
            msg = "Se necesita al menos un canal MIDI (1–16)"
            raise ValueError(msg)
        for c in chs:
            if not 1 <= c <= 16:
                msg = "El canal MIDI debe estar entre 1 y 16"
                raise ValueError(msg)
        self._ch0_set = frozenset(c - 1 for c in chs)
        self._state: dict[int, _RpnState] = {c0: _RpnState() for c0 in self._ch0_set}

    def feed_coarse_tuning(self, msg: mido.Message) -> int | None:
        if msg.is_meta or msg.type != "control_change" or not hasattr(msg, "channel"):
            return None
        ch0 = msg.channel
        if ch0 not in self._ch0_set:
            return None
        st = self._state[ch0]
        if msg.control == 101:
            st.rpn_msb = msg.value
            return None
        if msg.control == 100:
            st.rpn_lsb = msg.value
            return None
        if msg.control == 6 and st.rpn_msb == 0 and st.rpn_lsb == 2:
            return msg.value - 64
        return None


def parse_master_coarse_tuning_sysex(msg: mido.Message) -> int | None:
    """Devuelve semitonos si el mensaje es Universal Realtime Master Coarse Tuning."""
    if msg.type != "sysex":
        return None
    data = tuple(msg.data)
    if len(data) != 6:
        return None
    if data[:4] != (0x7F, 0x7F, 0x04, 0x04):
        return None
    value = data[5] - 0x40
    if not -24 <= value <= 24:
        return None
    return value
