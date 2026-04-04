from __future__ import annotations

import mido

from roland_fp30x_controller.midi.bank_program_parser import BankProgramParser


def test_parser_program_change_uses_last_bank() -> None:
    p = BankProgramParser(4)
    assert p.feed(mido.Message("control_change", channel=3, control=0, value=16)) is None
    assert p.feed(mido.Message("control_change", channel=3, control=32, value=67)) is None
    r = p.feed(mido.Message("program_change", channel=3, program=0))
    assert r == (16, 67, 1)


def test_parser_ignores_other_channel() -> None:
    p = BankProgramParser((1, 4))
    assert p.feed(mido.Message("program_change", channel=2, program=5)) is None


def test_parser_wrong_channel_no_bank_update() -> None:
    p = BankProgramParser(4)
    p.feed(mido.Message("control_change", channel=0, control=0, value=99))
    r = p.feed(mido.Message("program_change", channel=3, program=0))
    assert r == (0, 0, 1)


def test_parser_channel1_matches_fp30x_panel_tx() -> None:
    """Secuencia como en log real: canal 1, MSB 32 LSB 68, PC 16 → doc 17."""
    p = BankProgramParser((1, 4))
    assert p.feed(mido.Message("control_change", channel=0, control=0, value=32)) is None
    assert p.feed(mido.Message("control_change", channel=0, control=32, value=68)) is None
    r = p.feed(mido.Message("program_change", channel=0, program=16))
    assert r == (32, 68, 17)


def test_parser_banks_independent_per_channel() -> None:
    p = BankProgramParser((1, 4))
    p.feed(mido.Message("control_change", channel=0, control=0, value=10))
    p.feed(mido.Message("control_change", channel=0, control=32, value=20))
    p.feed(mido.Message("control_change", channel=3, control=0, value=16))
    p.feed(mido.Message("control_change", channel=3, control=32, value=67))
    assert p.feed(mido.Message("program_change", channel=0, program=0)) == (10, 20, 1)
    assert p.feed(mido.Message("program_change", channel=3, program=0)) == (16, 67, 1)
