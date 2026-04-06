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


# --- Metrónomo del piano (direcciones extraídas por ingeniería inversa de Roland Piano App 1.5.9) ---
# metronomeSwToggle  01 00 05 09  First(0) / Repeat(1)
# metronomeSwitch    01 00 03 1A  Off(0) / On(1) / OnRequestNextStart(2)
# metronomeStatus    01 00 01 0F  (read) 0=off 1=on
# sequencerTempoWO   01 00 03 09  (write, 2 bytes) [bpm // 128, bpm % 128]
# sequencerTempoRO   01 00 01 08  (read,  2 bytes)
# metronomeBeat      01 00 02 1F
# metronomeVolume    01 00 02 21


def app_connect_handshake() -> mido.Message:
    """Notifica al FP-30X que una app está conectada (DT1 «connection» 01 00 03 06 = 1).

    El piano requiere este mensaje para aceptar DT1 de master volume, metrónomo, etc.
    Fuente: Roland Piano App 1.5.9 — midiConnector.js sendConnection(1), extraído
    por ingeniería inversa. La dirección 01 00 03 06 se llama 'connection' en el mapa
    de direcciones de la app y se envía justo tras establecer la conexión MIDI.
    """
    return roland_data_set_1((0x01, 0x00, 0x03, 0x06), (0x01,))


def metronome_toggle() -> mido.Message:
    """Activa/desactiva el metrónomo interno del FP-30X (primera pulsación)."""
    return roland_data_set_1((0x01, 0x00, 0x05, 0x09), (0x00,))


def metronome_set(*, on: bool) -> mido.Message:
    """Enciende o apaga el metrónomo directamente sin depender del estado actual."""
    return roland_data_set_1((0x01, 0x00, 0x03, 0x1A), (0x01 if on else 0x00,))


def metronome_set_tempo(bpm: int) -> mido.Message:
    """Establece el tempo del metrónomo (20–250 BPM). Codificación: [bpm // 128, bpm % 128]."""
    if not 20 <= bpm <= 250:
        msg = "El tempo debe estar entre 20 y 250 BPM"
        raise ValueError(msg)
    return roland_data_set_1((0x01, 0x00, 0x03, 0x09), (bpm // 128, bpm % 128))


def metronome_read_status() -> mido.Message:
    """Solicita el estado on/off del metrónomo (RQ1). Respuesta en 01 00 01 0F."""
    return roland_data_request_1((0x01, 0x00, 0x01, 0x0F), (0x00, 0x00, 0x00, 0x01))


def metronome_read_tempo() -> mido.Message:
    """Solicita el tempo actual del secuenciador (RQ1). Respuesta en 01 00 01 08, 2 bytes."""
    return roland_data_request_1((0x01, 0x00, 0x01, 0x08), (0x00, 0x00, 0x00, 0x02))


def master_volume_set(value_0_127: int) -> mido.Message:
    """Establece el master volume vía DT1 (01 00 02 13). Actualiza las luces del panel del FP-30X."""
    if not 0 <= value_0_127 <= 127:
        msg = "Master Volume debe estar entre 0 y 127"
        raise ValueError(msg)
    return roland_data_set_1((0x01, 0x00, 0x02, 0x13), (value_0_127,))


def master_volume_read() -> mido.Message:
    """Solicita el master volume del piano (RQ1). Respuesta en 01 00 02 13, 1 byte, 0–127."""
    return roland_data_request_1((0x01, 0x00, 0x02, 0x13), (0x00, 0x00, 0x00, 0x01))


def key_transpose_read() -> mido.Message:
    """Solicita la transposición de teclado (RQ1). Respuesta en 01 00 01 01, 1 byte.

    Decodificación: semitones = value - 64  (64 = sin transposición).
    Rango FP-30X: -6..+5 (valores 58..69).
    """
    return roland_data_request_1((0x01, 0x00, 0x01, 0x01), (0x00, 0x00, 0x00, 0x01))


def master_volume_realtime(value_0_127: int) -> mido.Message:
    if not 0 <= value_0_127 <= 127:
        msg = "Master Volume debe estar entre 0 y 127"
        raise ValueError(msg)
    return mido.Message("sysex", data=(0x7F, 0x7F, 0x04, 0x01, 0x00, value_0_127))


def keyboard_mode_set(mode: int) -> mido.Message:
    """Establece el modo de teclado (01 00 02 00). 0=Single 1=Split 2=Dual 3=Twin."""
    if not 0 <= mode <= 3:
        msg = "keyboard mode debe estar entre 0 y 3"
        raise ValueError(msg)
    return roland_data_set_1((0x01, 0x00, 0x02, 0x00), (mode,))


def keyboard_mode_read() -> mido.Message:
    """Solicita el modo de teclado (RQ1). Respuesta en 01 00 02 00."""
    return roland_data_request_1((0x01, 0x00, 0x02, 0x00), (0x00, 0x00, 0x00, 0x01))


def tone_for_single_set(category_idx: int, num: int) -> mido.Message:
    """Establece el tono del modo Single (01 00 02 07). 3 bytes: [cat, num//128, num%128]."""
    return roland_data_set_1((0x01, 0x00, 0x02, 0x07), (category_idx, num // 128, num % 128))


def tone_for_split_set(category_idx: int, num: int) -> mido.Message:
    """Establece el tono izquierdo del modo Split (01 00 02 0A)."""
    return roland_data_set_1((0x01, 0x00, 0x02, 0x0A), (category_idx, num // 128, num % 128))


def tone_for_dual_set(category_idx: int, num: int) -> mido.Message:
    """Establece el segundo tono del modo Dual (01 00 02 0D)."""
    return roland_data_set_1((0x01, 0x00, 0x02, 0x0D), (category_idx, num // 128, num % 128))


def split_point_set(note_midi: int) -> mido.Message:
    """Establece el punto de split (01 00 02 01). note_midi: 0-127."""
    if not 0 <= note_midi <= 127:
        msg = "Split point debe estar entre 0 y 127"
        raise ValueError(msg)
    return roland_data_set_1((0x01, 0x00, 0x02, 0x01), (note_midi,))


def split_point_read() -> mido.Message:
    return roland_data_request_1((0x01, 0x00, 0x02, 0x01), (0x00, 0x00, 0x00, 0x01))


def split_balance_set(value: int) -> mido.Message:
    """Establece el balance del modo Split (01 00 02 03). 0-18 donde 9=centro."""
    return roland_data_set_1((0x01, 0x00, 0x02, 0x03), (value,))


def split_balance_read() -> mido.Message:
    return roland_data_request_1((0x01, 0x00, 0x02, 0x03), (0x00, 0x00, 0x00, 0x01))


def dual_balance_set(value: int) -> mido.Message:
    """Establece el balance del modo Dual (01 00 02 05). 0-18 donde 9=centro."""
    return roland_data_set_1((0x01, 0x00, 0x02, 0x05), (value,))


def dual_balance_read() -> mido.Message:
    return roland_data_request_1((0x01, 0x00, 0x02, 0x05), (0x00, 0x00, 0x00, 0x01))


def split_octave_shift_set(value: int) -> mido.Message:
    """Transposición de octava en Split (01 00 02 02). Encoding: value+64."""
    return roland_data_set_1((0x01, 0x00, 0x02, 0x02), (value + 64,))


def dual_octave_shift_set(value: int) -> mido.Message:
    """Transposición de octava en Dual (01 00 02 04). Encoding: value+64."""
    return roland_data_set_1((0x01, 0x00, 0x02, 0x04), (value + 64,))


def twin_piano_mode_set(mode: int) -> mido.Message:
    """Establece el modo Twin Piano (01 00 02 06). 0=Pair 1=Individual."""
    return roland_data_set_1((0x01, 0x00, 0x02, 0x06), (mode,))


def metronome_volume_set(value_0_10: int) -> mido.Message:
    """Establece el volumen del metrónomo (01 00 02 21). 0=silenciado, 1–10."""
    if not 0 <= value_0_10 <= 10:
        msg = "Metronome volume debe estar entre 0 y 10"
        raise ValueError(msg)
    return roland_data_set_1((0x01, 0x00, 0x02, 0x21), (value_0_10,))


def metronome_volume_read() -> mido.Message:
    return roland_data_request_1((0x01, 0x00, 0x02, 0x21), (0x00, 0x00, 0x00, 0x01))


def metronome_tone_set(value_0_3: int) -> mido.Message:
    """Establece el sonido del metrónomo (01 00 02 22). 0=Click 1=Electronic 2=Voice-JP 3=Voice-EN."""
    if not 0 <= value_0_3 <= 3:
        msg = "Metronome tone debe estar entre 0 y 3"
        raise ValueError(msg)
    return roland_data_set_1((0x01, 0x00, 0x02, 0x22), (value_0_3,))


def metronome_tone_read() -> mido.Message:
    return roland_data_request_1((0x01, 0x00, 0x02, 0x22), (0x00, 0x00, 0x00, 0x01))


def metronome_beat_set(value: int) -> mido.Message:
    """Establece el compás del metrónomo (01 00 02 1F). Ver tabla §4.3."""
    return roland_data_set_1((0x01, 0x00, 0x02, 0x1F), (value,))


def metronome_beat_read() -> mido.Message:
    return roland_data_request_1((0x01, 0x00, 0x02, 0x1F), (0x00, 0x00, 0x00, 0x01))


def metronome_pattern_set(value: int) -> mido.Message:
    """Establece el patrón de metrónomo (01 00 02 20). 0-7."""
    return roland_data_set_1((0x01, 0x00, 0x02, 0x20), (value,))


def metronome_pattern_read() -> mido.Message:
    return roland_data_request_1((0x01, 0x00, 0x02, 0x20), (0x00, 0x00, 0x00, 0x01))


def master_tuning_set(cents_offset: float) -> mido.Message:
    """Establece el master tuning (01 00 02 18). cents_offset: -50.0..+50.0.

    Encoding: 14-bit centrado en 8192 (= 440 Hz).
    value = 8192 + round(cents_offset * 8191 / 50)
    Dividido en 2 bytes de 7 bits: [value // 128, value % 128].
    """
    if not -50.0 <= cents_offset <= 50.0:
        msg = "Master tuning offset debe estar entre -50 y +50 cents"
        raise ValueError(msg)
    raw = 8192 + round(cents_offset * 8191 / 50)
    raw = max(0, min(16383, raw))
    return roland_data_set_1((0x01, 0x00, 0x02, 0x18), (raw // 128, raw % 128))


def master_tuning_read() -> mido.Message:
    """Solicita el master tuning (RQ1). Respuesta en 01 00 02 18, 2 bytes."""
    return roland_data_request_1((0x01, 0x00, 0x02, 0x18), (0x00, 0x00, 0x00, 0x02))


def key_touch_set(value_0_3: int) -> mido.Message:
    """Establece la sensibilidad del teclado (01 00 02 1D). 0=Fix 1=Light 2=Medium 3=Heavy."""
    if not 0 <= value_0_3 <= 3:
        msg = "Key Touch debe estar entre 0 y 3"
        raise ValueError(msg)
    return roland_data_set_1((0x01, 0x00, 0x02, 0x1D), (value_0_3,))


def key_touch_read() -> mido.Message:
    """Solicita la sensibilidad del teclado (RQ1). Respuesta en 01 00 02 1D, 1 byte."""
    return roland_data_request_1((0x01, 0x00, 0x02, 0x1D), (0x00, 0x00, 0x00, 0x01))


def brilliance_set(value_neg1_to_pos1: int) -> mido.Message:
    """Establece el brillo del sonido (01 00 02 1C). Rango -1..+1, centrado en 64."""
    if not -1 <= value_neg1_to_pos1 <= 1:
        msg = "Brilliance debe estar entre -1 y +1"
        raise ValueError(msg)
    return roland_data_set_1((0x01, 0x00, 0x02, 0x1C), (64 + value_neg1_to_pos1,))


def brilliance_read() -> mido.Message:
    """Solicita el brillo del sonido (RQ1). Respuesta en 01 00 02 1C, 1 byte."""
    return roland_data_request_1((0x01, 0x00, 0x02, 0x1C), (0x00, 0x00, 0x00, 0x01))


def ambience_set(value_0_10: int) -> mido.Message:
    """Establece el nivel de ambience (01 00 02 1A). Rango 0–10."""
    if not 0 <= value_0_10 <= 10:
        msg = "Ambience debe estar entre 0 y 10"
        raise ValueError(msg)
    return roland_data_set_1((0x01, 0x00, 0x02, 0x1A), (value_0_10,))


def ambience_read() -> mido.Message:
    """Solicita el nivel de ambience (RQ1). Respuesta en 01 00 02 1A, 1 byte."""
    return roland_data_request_1((0x01, 0x00, 0x02, 0x1A), (0x00, 0x00, 0x00, 0x01))


# ── Piano Designer ───────────────────────────────────────────────────────────
# Direcciones extraídas por ingeniería inversa de Roland Piano App 1.5.9.
# addressMapModelId: 00000019 — parámetros temporales del Piano Designer.
# Los parámetros "temporales" (02 xxxxxx) se aplican en tiempo real pero
# se guardan en el piano solo con el comando writePianoDesigner.

_PD_PREFIX = (0x02, 0x00, 0x00)  # prefijo parámetros Piano Designer

def _pd_addr(offset: int) -> tuple[int, int, int, int]:
    return (0x02, 0x00, 0x00, offset)


def piano_designer_lid_set(value_0_6: int) -> mido.Message:
    """Establece la apertura de la tapa (Lid). 0–6."""
    return roland_data_set_1(_pd_addr(0x01), (max(0, min(6, value_0_6)),))


def piano_designer_string_resonance_set(value: int) -> mido.Message:
    """Establece String Resonance. 0=Off, 1–10."""
    return roland_data_set_1(_pd_addr(0x02), (max(0, min(10, value)),))


def piano_designer_damper_resonance_set(value: int) -> mido.Message:
    """Establece Damper Resonance. 0=Off, 1–10."""
    return roland_data_set_1(_pd_addr(0x03), (max(0, min(10, value)),))


def piano_designer_key_off_resonance_set(value: int) -> mido.Message:
    """Establece Key Off Resonance. 0=Off, 1–10."""
    return roland_data_set_1(_pd_addr(0x06), (max(0, min(10, value)),))


def piano_designer_temperament_set(value_0_8: int) -> mido.Message:
    """Establece el temperamento. 0=Equal 1=JustMajor 2=JustMinor 3=Pythagorean
    4=Kirnberger1 5=Kirnberger2 6=Kirnberger3 7=Meantone 8=Werckmeister 9=Arabic."""
    return roland_data_set_1((0x01, 0x00, 0x00, 0x04), (max(0, min(9, value_0_8)),))


def piano_designer_temperament_key_set(value_0_11: int) -> mido.Message:
    """Establece la tónica del temperamento. 0=C, 1=C#, …, 11=B."""
    return roland_data_set_1((0x01, 0x00, 0x00, 0x05), (max(0, min(11, value_0_11)),))


def piano_designer_write() -> mido.Message:
    """Guarda los parámetros del Piano Designer en el piano (writePianoDesigner)."""
    return roland_data_set_1((0x01, 0x02, 0x00, 0x01), (0x01,))


def piano_designer_enter() -> mido.Message:
    """Notifica al piano que se entra en modo Piano Designer."""
    return roland_data_set_1((0x01, 0x02, 0x00, 0x00), (0x01,))


def piano_designer_individual_note_tuning_set(note_0_87: int, cents_x10: int) -> mido.Message:
    """Ajusta el fine tuning de una nota individual. cents_x10: -500..+500 (= -50.0..+50.0 cents).
    Dirección: 02 10 04 00 + note (offset por nota). Encoding: value + 500 centrado."""
    raw = max(0, min(1000, cents_x10 + 500))
    addr = (0x02, 0x10, 0x04, note_0_87)
    return roland_data_set_1(addr, (raw // 128, raw % 128))


def piano_designer_individual_note_character_set(note_0_87: int, value: int) -> mido.Message:
    """Ajusta el carácter tonal de una nota individual. value: -5..+5 → offset 5."""
    raw = max(0, min(10, value + 5))
    addr = (0x02, 0x10, 0x05, note_0_87)
    return roland_data_set_1(addr, (raw,))


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
