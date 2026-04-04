from __future__ import annotations

import mido

from roland_fp30x_controller.midi import messages as midix


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
