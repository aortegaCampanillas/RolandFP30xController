from __future__ import annotations

import mido

ROLAND_ID = 0x41
ROLAND_DEVICE_ID = 0x10
FP30X_MODEL_ID = (0x00, 0x00, 0x00, 0x28)
ROLAND_CMD_RQ1 = 0x11
ROLAND_CMD_DT1 = 0x12


def channel_zero(channel_1_16: int) -> int:
    if not 1 <= channel_1_16 <= 16:
        msg = "El canal MIDI debe estar entre 1 y 16"
        raise ValueError(msg)
    return channel_1_16 - 1


# Pausa breve entre mensajes: evita que el FP-30X agrupe mal CC0/CC32/PC en algunos drivers.
DEFAULT_MESSAGE_GAP_S = 0.02
# Tiempo extra tras Program Change antes del Note On de enganche (procesamiento interno).
POST_PROGRAM_CHANGE_LATCH_DELAY_S = 0.08


def bank_select_and_program_change(
    channel_1_16: int, bank_msb: int, bank_lsb: int, program_0_127: int
) -> list[mido.Message]:
    ch = channel_zero(channel_1_16)
    if not 0 <= bank_msb <= 127 or not 0 <= bank_lsb <= 127:
        msg = "Bank MSB/LSB deben estar entre 0 y 127"
        raise ValueError(msg)
    if not 0 <= program_0_127 <= 127:
        msg = "Program change debe estar entre 0 y 127"
        raise ValueError(msg)
    return [
        mido.Message("control_change", channel=ch, control=0, value=bank_msb),
        mido.Message("control_change", channel=ch, control=32, value=bank_lsb),
        mido.Message("program_change", channel=ch, program=program_0_127),
    ]


def bank_select_program_sequence(
    channel_1_16: int,
    bank_msb: int,
    bank_lsb: int,
    program_0_127: int,
    *,
    latch_after_program: bool = True,
    latch_note: int = 60,
    latch_velocity: int = 1,
) -> list[mido.Message]:
    """
    Igual que bank_select_and_program_change, y opcionalmente Note On/Off muy breves.

    El manual FP-30X indica que el sonido cambia a partir del *siguiente Note On*
    tras el Program Change; sin tocar el teclado parece que «no hace nada».
    """
    core, latch = bank_select_program_and_latch_parts(
        channel_1_16,
        bank_msb,
        bank_lsb,
        program_0_127,
        latch_after_program=latch_after_program,
        latch_note=latch_note,
        latch_velocity=latch_velocity,
    )
    return [*core, *latch]


def bank_select_program_and_latch_parts(
    channel_1_16: int,
    bank_msb: int,
    bank_lsb: int,
    program_0_127: int,
    *,
    latch_after_program: bool = True,
    latch_note: int = 60,
    latch_velocity: int = 1,
) -> tuple[list[mido.Message], list[mido.Message]]:
    """
    Parte 1: CC0, CC32, Program Change. Parte 2: Note On/Off de enganche (o vacía).
    Entre ambas conviene esperar POST_PROGRAM_CHANGE_LATCH_DELAY_S al enviar.
    """
    if not 0 <= latch_note <= 127 or not 1 <= latch_velocity <= 127:
        msg = "Nota de enganche fuera de rango"
        raise ValueError(msg)
    core = bank_select_and_program_change(
        channel_1_16, bank_msb, bank_lsb, program_0_127
    )
    if not latch_after_program:
        return core, []
    ch = channel_zero(channel_1_16)
    latch = [
        mido.Message("note_on", channel=ch, note=latch_note, velocity=latch_velocity),
        mido.Message("note_off", channel=ch, note=latch_note, velocity=0),
    ]
    return core, latch


def control_change(channel_1_16: int, control: int, value: int) -> mido.Message:
    ch = channel_zero(channel_1_16)
    if not 0 <= control <= 127 or not 0 <= value <= 127:
        msg = "Control y valor deben estar entre 0 y 127"
        raise ValueError(msg)
    return mido.Message("control_change", channel=ch, control=control, value=value)


def rpn_coarse_tuning(channel_1_16: int, semitones: int) -> list[mido.Message]:
    """
    RPN 0,2 (Coarse Tuning): 64 = 0 semitonos.

    Se envía además Null RPN (127/127) para dejar el selector limpio.
    """
    if not -64 <= semitones <= 63:
        msg = "La transposición debe estar entre -64 y 63 semitonos"
        raise ValueError(msg)
    value = semitones + 64
    return [
        control_change(channel_1_16, 101, 0),
        control_change(channel_1_16, 100, 2),
        control_change(channel_1_16, 6, value),
        control_change(channel_1_16, 38, 0),
        control_change(channel_1_16, 101, 127),
        control_change(channel_1_16, 100, 127),
    ]


def master_coarse_tuning_realtime(semitones: int) -> mido.Message:
    """
    Universal Realtime SysEx Master Coarse Tuning.

    FP-30X MIDI Implementation:
    F0 7F 7F 04 04 ll mm F7
    ll se ignora; mm = 0x40 + semitonos, rango soportado -24..+24.
    """
    if not -24 <= semitones <= 24:
        msg = "La transposición debe estar entre -24 y 24 semitonos"
        raise ValueError(msg)
    return mido.Message("sysex", data=(0x7F, 0x7F, 0x04, 0x04, 0x00, semitones + 0x40))


def roland_checksum(values: Iterable[int]) -> int:
    return (128 - (sum(values) % 128)) % 128


def roland_data_request_1(address: tuple[int, int, int, int], size: tuple[int, int, int, int]) -> mido.Message:
    payload = [*address, *size]
    return mido.Message(
        "sysex",
        data=(
            ROLAND_ID,
            ROLAND_DEVICE_ID,
            *FP30X_MODEL_ID,
            ROLAND_CMD_RQ1,
            *payload,
            roland_checksum(payload),
        ),
    )


def roland_data_set_1(address: tuple[int, int, int, int], data: Iterable[int]) -> mido.Message:
    data_tuple = tuple(data)
    payload = [*address, *data_tuple]
    return mido.Message(
        "sysex",
        data=(
            ROLAND_ID,
            ROLAND_DEVICE_ID,
            *FP30X_MODEL_ID,
            ROLAND_CMD_DT1,
            *payload,
            roland_checksum(payload),
        ),
    )


def metronome_probe_on() -> mido.Message:
    return roland_data_set_1((0x01, 0x00, 0x03, 0x06), (0x01,))


def master_volume_realtime(value_0_127: int) -> mido.Message:
    if not 0 <= value_0_127 <= 127:
        msg = "Master Volume debe estar entre 0 y 127"
        raise ValueError(msg)
    return mido.Message("sysex", data=(0x7F, 0x7F, 0x04, 0x01, 0x00, value_0_127))


def gm2_global_reverb_parameter(parameter_pp: int, value_0_127: int) -> mido.Message:
    """
    GM2 Universal Realtime — Global Parameter Control, ranura Reverb (0101).
    Ver FP-30X MIDI Implementation: pp=0 tipo, pp=1 tiempo de cola.
    """
    if not 0 <= parameter_pp <= 127 or not 0 <= value_0_127 <= 127:
        msg = "Parámetro o valor de reverb fuera de rango"
        raise ValueError(msg)
    return mido.Message(
        "sysex",
        data=(
            0x7F,
            0x7F,
            0x04,
            0x05,
            0x01,
            0x01,
            0x01,
            0x01,
            0x01,
            parameter_pp,
            value_0_127,
        ),
    )
