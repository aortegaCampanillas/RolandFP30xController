"""Interpreta CC 0 / CC 32 + Program Change en uno o varios canales MIDI."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import mido


@dataclass
class _BankHold:
    bank_msb: int = 0
    bank_lsb: int = 0


class BankProgramParser:
    """
    Mantiene el último banco por canal y devuelve (msb, lsb, program_doc) al PC.

    El FP-30X suele *transmitir* cambios de tono desde panel en el canal 1, mientras
    que la parte teclado/SMF Internal sigue el tono en el canal 4 para recepción.
    """

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
        self._hold: dict[int, _BankHold] = {c0: _BankHold() for c0 in self._ch0_set}

    def feed(self, msg: mido.Message) -> tuple[int, int, int] | None:
        if msg.is_meta or msg.type in ("sysex", "clock", "start", "stop", "continue"):
            return None
        if not hasattr(msg, "channel"):
            return None
        ch0 = msg.channel
        if ch0 not in self._ch0_set:
            return None
        st = self._hold[ch0]
        if msg.type == "control_change":
            if msg.control == 0:
                st.bank_msb = msg.value
            elif msg.control == 32:
                st.bank_lsb = msg.value
            return None
        if msg.type == "program_change":
            prog_doc = msg.program + 1
            return (st.bank_msb, st.bank_lsb, prog_doc)
        return None
