from __future__ import annotations

import mido

from roland_fp30x_controller.midi import messages as midix
from roland_fp30x_controller.midi.rpn_parser import RpnParser, parse_master_coarse_tuning_sysex


def test_channel_zero() -> None:
    assert midix.channel_zero(1) == 0
    assert midix.channel_zero(16) == 15


def test_gm2_global_reverb_time_sysex() -> None:
    m = midix.gm2_global_reverb_parameter(1, 64)
    assert m.type == "sysex"
    assert list(m.bytes()) == [
        0xF0,
        0x7F,
        0x7F,
        0x04,
        0x05,
        0x01,
        0x01,
        0x01,
        0x01,
        0x01,
        0x01,
        0x40,
        0xF7,
    ]


def test_master_volume_sysex() -> None:
    m = midix.master_volume_realtime(100)
    assert m.type == "sysex"
    ref = mido.Message.from_bytes([0xF0, 0x7F, 0x7F, 0x04, 0x01, 0x00, 0x64, 0xF7])
    assert m.bin() == ref.bin()


def test_bank_program_order() -> None:
    msgs = midix.bank_select_and_program_change(3, 0x10, 0x20, 0x05)
    assert [m.type for m in msgs] == ["control_change", "control_change", "program_change"]
    assert msgs[0].channel == 2 and msgs[0].control == 0 and msgs[0].value == 0x10
    assert msgs[1].control == 32 and msgs[1].value == 0x20
    assert msgs[2].program == 5


def test_bank_program_sequence_latch() -> None:
    with_latch = midix.bank_select_program_sequence(1, 0, 68, 0, latch_after_program=True)
    assert len(with_latch) == 5
    assert with_latch[3].type == "note_on" and with_latch[3].note == 60
    assert with_latch[4].type == "note_off"
    no_latch = midix.bank_select_program_sequence(1, 0, 68, 0, latch_after_program=False)
    assert len(no_latch) == 3


def test_bank_program_latch_parts() -> None:
    core, latch = midix.bank_select_program_and_latch_parts(4, 0, 68, 0)
    assert len(core) == 3 and core[-1].type == "program_change"
    assert core[-1].channel == 3
    assert len(latch) == 2


def test_rpn_coarse_tuning_sequence() -> None:
    msgs = midix.rpn_coarse_tuning(4, -5)
    assert [m.type for m in msgs] == ["control_change"] * 6
    assert [(m.control, m.value) for m in msgs] == [
        (101, 0),
        (100, 2),
        (6, 59),
        (38, 0),
        (101, 127),
        (100, 127),
    ]
    assert all(m.channel == 3 for m in msgs)


def test_rpn_parser_detects_coarse_tuning() -> None:
    p = RpnParser((1, 4))
    assert p.feed_coarse_tuning(mido.Message("control_change", channel=3, control=101, value=0)) is None
    assert p.feed_coarse_tuning(mido.Message("control_change", channel=3, control=100, value=2)) is None
    assert p.feed_coarse_tuning(mido.Message("control_change", channel=3, control=6, value=69)) == 5


def test_master_coarse_tuning_realtime_sysex() -> None:
    m = midix.master_coarse_tuning_realtime(5)
    assert m.type == "sysex"
    assert list(m.bytes()) == [0xF0, 0x7F, 0x7F, 0x04, 0x04, 0x00, 0x45, 0xF7]


def test_app_connect_handshake_sysex() -> None:
    m = midix.app_connect_handshake()
    assert list(m.bytes()) == [0xF0, 0x41, 0x10, 0x00, 0x00, 0x00, 0x28, 0x12, 0x01, 0x00, 0x03, 0x06, 0x01, 0x75, 0xF7]


def test_dual_balance_fp30x_sysex_roundtrip() -> None:
    for v in range(midix.DUAL_BALANCE_PANEL_MIN, midix.DUAL_BALANCE_PANEL_MAX + 1):
        b = midix.dual_balance_sysex_byte(v)
        assert midix.dual_balance_panel_from_sysex_byte(b) == v
    assert midix.dual_balance_sysex_byte(0) == midix.dual_balance_sysex_byte(midix.DUAL_BALANCE_PANEL_MIN)
    assert midix.dual_balance_sysex_byte(18) == midix.dual_balance_sysex_byte(midix.DUAL_BALANCE_PANEL_MAX)


def test_split_balance_fp30x_sysex_roundtrip() -> None:
    for v in range(19):
        b = midix.split_balance_sysex_byte(v)
        assert midix.split_balance_panel_from_sysex_byte(b) == v


def test_split_balance_display_lr_endpoints() -> None:
    assert midix.split_balance_display_lr(0) == (9, 1)
    assert midix.split_balance_display_lr(9) == (9, 9)
    assert midix.split_balance_display_lr(18) == (1, 9)


def test_dual_balance_display_lr_endpoints() -> None:
    assert midix.dual_balance_display_lr(midix.DUAL_BALANCE_PANEL_MIN) == (9, 1)
    assert midix.dual_balance_display_lr(9) == (9, 9)
    assert midix.dual_balance_display_lr(midix.DUAL_BALANCE_PANEL_MAX) == (1, 9)


def test_parse_master_coarse_tuning_sysex() -> None:
    m = mido.Message.from_bytes([0xF0, 0x7F, 0x7F, 0x04, 0x04, 0x00, 0x3C, 0xF7])
    assert parse_master_coarse_tuning_sysex(m) == -4
