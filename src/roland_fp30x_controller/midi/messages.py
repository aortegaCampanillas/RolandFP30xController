from __future__ import annotations

import math

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

# Dual: el manual indica que CC7 ajusta el volumen por «Part». El teclado principal
# usa el canal 4 (véase soporte Roland / DAW). La segunda capa en Dual suele seguir
# otra parte MIDI en pianos Roland compactos; el SysEx 01 00 02 05 a veces espera
# valor centrado en 64, no 0..18 crudo.
MIDI_DUAL_MAIN_VOLUME_CH = 4
MIDI_DUAL_LAYER_VOLUME_CH = 2
# Split: mano derecha como parte principal (mismo canal que tono vía CC0/32/PC); mano izquierda
# como segunda parte (mismo canal que la capa Dual en este proyecto).
MIDI_SPLIT_RIGHT_VOLUME_CH = MIDI_DUAL_MAIN_VOLUME_CH
MIDI_SPLIT_LEFT_VOLUME_CH = MIDI_DUAL_LAYER_VOLUME_CH
# Tiempo extra tras Program Change antes del Note On de enganche (procesamiento interno).
POST_PROGRAM_CHANGE_LATCH_DELAY_S = 0.08

# Balance Dual (escala de panel con 9=centro): el FP-30X no aplica 0..18 completo;
# fuera de ~6..11 satura. La etiqueta L:R en UI usa split_balance_display_lr / dual_balance_display_lr.
DUAL_BALANCE_PANEL_MIN = 6
DUAL_BALANCE_PANEL_MAX = 11


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


# DT1 `masterVolume` en FP-30X: rango útil del panel 0..100 (no 0..127).
MASTER_VOLUME_DT1_MAX = 100


def master_volume_set(value: int) -> mido.Message:
    """Establece el master volume vía DT1 (01 00 02 13). Actualiza las luces del panel del FP-30X."""
    if not 0 <= value <= MASTER_VOLUME_DT1_MAX:
        msg = f"Master Volume debe estar entre 0 y {MASTER_VOLUME_DT1_MAX}"
        raise ValueError(msg)
    return roland_data_set_1((0x01, 0x00, 0x02, 0x13), (value,))


def master_volume_read() -> mido.Message:
    """Solicita el master volume del piano (RQ1). Respuesta en 01 00 02 13, 1 byte (panel 0..100)."""
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


def tone_for_single_read() -> mido.Message:
    return roland_data_request_1((0x01, 0x00, 0x02, 0x07), (0x00, 0x00, 0x00, 0x03))


def tone_for_split_read() -> mido.Message:
    return roland_data_request_1((0x01, 0x00, 0x02, 0x0A), (0x00, 0x00, 0x00, 0x03))


def tone_for_dual_read() -> mido.Message:
    return roland_data_request_1((0x01, 0x00, 0x02, 0x0D), (0x00, 0x00, 0x00, 0x03))


def split_point_set(note_midi: int) -> mido.Message:
    """Establece el punto de split (01 00 02 01). note_midi: 0-127."""
    if not 0 <= note_midi <= 127:
        msg = "Split point debe estar entre 0 y 127"
        raise ValueError(msg)
    return roland_data_set_1((0x01, 0x00, 0x02, 0x01), (note_midi,))


def split_point_read() -> mido.Message:
    return roland_data_request_1((0x01, 0x00, 0x02, 0x01), (0x00, 0x00, 0x00, 0x01))


def split_balance_display_lr(panel_value_0_18: int) -> tuple[int, int]:
    """Pareja izquierda:derecha (1..9 cada una) para la etiqueta de balance Split.

    Valor SysEx/panel 0..18 con 9=centro: extremo 0 → 9:1, centro 9 → 9:9, extremo 18 → 1:9.
    """
    v = max(0, min(18, int(panel_value_0_18)))
    if v <= 9:
        return 9, 1 + (8 * v) // 9
    return 1 + (8 * (18 - v)) // 9, 9


def split_balance_sysex_byte(value: int) -> int:
    """Índice de panel 0..18 (9=centro) al byte DT1 del FP-30X: `64 + (v−9)×3`."""
    v = max(0, min(18, int(value)))
    return max(0, min(127, 64 + (v - 9) * 3))


def split_balance_panel_from_sysex_byte(raw: int) -> int:
    """Invierte el byte RQ1/DT1 al índice de panel 0..18."""
    if 0 <= raw <= 18:
        return max(0, min(18, raw))
    v = int(round((raw - 64) / 3 + 9))
    return max(0, min(18, v))


def dual_balance_display_lr(panel_value_6_11: int) -> tuple[int, int]:
    """Misma convención visual que Split; panel Dual del FP-30X solo usa 6..11."""
    v = max(DUAL_BALANCE_PANEL_MIN, min(DUAL_BALANCE_PANEL_MAX, int(panel_value_6_11)))
    if v <= 9:
        full = (v - DUAL_BALANCE_PANEL_MIN) * 3
    else:
        full = int(round(9 + (v - 9) * 4.5))
    return split_balance_display_lr(full)


def split_balance_set(value: int) -> mido.Message:
    """Balance Split (01 00 02 03). Panel 0..18 (9=centro); byte DT1 centrado en 64."""
    return roland_data_set_1((0x01, 0x00, 0x02, 0x03), (split_balance_sysex_byte(value),))


def split_balance_control_changes(value: int) -> list[mido.Message]:
    """CC7 en mano izquierda y derecha (canales 2 y 4): refuerzo audible en todo el rango, como en Dual."""
    b = split_balance_sysex_byte(value)
    d = b - 64
    left = max(1, min(127, 100 - d))
    right = max(1, min(127, 100 + d))
    return [
        control_change(MIDI_SPLIT_LEFT_VOLUME_CH, 7, left),
        control_change(MIDI_SPLIT_RIGHT_VOLUME_CH, 7, right),
    ]


def split_balance_read() -> mido.Message:
    return roland_data_request_1((0x01, 0x00, 0x02, 0x03), (0x00, 0x00, 0x00, 0x01))


def dual_balance_sysex_byte(value: int) -> int:
    """Codifica la posición de panel (9=centro) al byte DT1 centrado en 64.

    El hardware solo acepta un subconjunto; se recorta a DUAL_BALANCE_PANEL_MIN/MAX.
    """
    v = max(DUAL_BALANCE_PANEL_MIN, min(DUAL_BALANCE_PANEL_MAX, int(value)))
    return max(0, min(127, 64 + (v - 9) * 3))


def dual_balance_panel_from_sysex_byte(raw: int) -> int:
    """Invierte el byte devuelto por RQ1/DT1 al índice de panel, acotado al rango real."""
    if raw <= 18:
        v = raw
    else:
        v = int(round((raw - 64) / 3 + 9))
    return max(DUAL_BALANCE_PANEL_MIN, min(DUAL_BALANCE_PANEL_MAX, v))


def dual_balance_set(value: int) -> mido.Message:
    """Balance Dual en 01 00 02 05 (byte centrado en 64). FP-30X: panel útil ~6..11 (9=centro)."""
    return roland_data_set_1((0x01, 0x00, 0x02, 0x05), (dual_balance_sysex_byte(value),))


def dual_balance_read() -> mido.Message:
    return roland_data_request_1((0x01, 0x00, 0x02, 0x05), (0x00, 0x00, 0x00, 0x01))


def dual_balance_control_changes(value: int) -> list[mido.Message]:
    """CC7 en dos partes: refuerzo audible (MIDI Implementation §Volume)."""
    b = dual_balance_sysex_byte(value)
    # Derivar dos niveles a partir del mismo eje que el SysEx (simétricos respecto a 64).
    d = b - 64
    main = max(1, min(127, 100 - d))
    layer = max(1, min(127, 100 + d))
    return [
        control_change(MIDI_DUAL_MAIN_VOLUME_CH, 7, main),
        control_change(MIDI_DUAL_LAYER_VOLUME_CH, 7, layer),
    ]


def split_octave_shift_set(value: int) -> mido.Message:
    """Transposición de octava en Split (01 00 02 02). Encoding: value+64."""
    return roland_data_set_1((0x01, 0x00, 0x02, 0x02), (value + 64,))


def dual_octave_shift_set(value: int) -> mido.Message:
    """Transposición de octava en Dual (01 00 02 04). Encoding: value+64."""
    return roland_data_set_1((0x01, 0x00, 0x02, 0x04), (value + 64,))


def twin_piano_mode_set(mode: int) -> mido.Message:
    """Establece el modo Twin Piano (01 00 02 06). 0=Pair 1=Individual."""
    return roland_data_set_1((0x01, 0x00, 0x02, 0x06), (mode,))


def twin_piano_mode_read() -> mido.Message:
    return roland_data_request_1((0x01, 0x00, 0x02, 0x06), (0x00, 0x00, 0x00, 0x01))


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
    """Establece el compás del metrónomo (01 00 02 1F).

    Tabla completa en PDF/midi_reference (incl. 2/2, 3/2, compases /8). Los seis presets
    de la app móvil (0/4 … 6/4) usan valores SysEx consecutivos 0..5, no el subconjunto 0,2..6.
    """
    return roland_data_set_1((0x01, 0x00, 0x02, 0x1F), (value,))


def metronome_beat_read() -> mido.Message:
    return roland_data_request_1((0x01, 0x00, 0x02, 0x1F), (0x00, 0x00, 0x00, 0x01))


def metronome_pattern_set(value: int) -> mido.Message:
    """Establece el patrón de metrónomo (01 00 02 20). 0-7 (0 = off en la app Roland)."""
    if not 0 <= value <= 7:
        msg = "Metronome pattern debe estar entre 0 y 7"
        raise ValueError(msg)
    return roland_data_set_1((0x01, 0x00, 0x02, 0x20), (value,))


def metronome_pattern_read() -> mido.Message:
    return roland_data_request_1((0x01, 0x00, 0x02, 0x20), (0x00, 0x00, 0x00, 0x01))


# Master tuning FP-30X: rango de referencia A4 según panel (~415.3 Hz … 466.2 Hz).
MASTER_TUNING_REF_HZ = 440.0
MASTER_TUNING_MIN_HZ = 415.3
MASTER_TUNING_MAX_HZ = 466.2
MASTER_TUNING_MIN_CENTS = 1200.0 * math.log2(MASTER_TUNING_MIN_HZ / MASTER_TUNING_REF_HZ)
MASTER_TUNING_MAX_CENTS = 1200.0 * math.log2(MASTER_TUNING_MAX_HZ / MASTER_TUNING_REF_HZ)
# Slider en décimas de cent (entero) para paso fino en la UI.
MASTER_TUNING_SLIDER_MIN = math.ceil(MASTER_TUNING_MIN_CENTS * 10)
MASTER_TUNING_SLIDER_MAX = math.ceil(MASTER_TUNING_MAX_CENTS * 10)


def master_tuning_raw_from_hz(hz: float) -> int:
    """Convierte Hz del panel (415.3…466.2) al valor 14-bit del SysEx (0…16383).

    El FP-30X interpola en escala logarítmica entre los extremos del panel (comportamiento
    observado frente a un mapeo lineal en cents alrededor de 8192, que desincronizaba
    envío, eco DT1 y la etiqueta en Hz).
    """
    h = max(MASTER_TUNING_MIN_HZ, min(MASTER_TUNING_MAX_HZ, float(hz)))
    ratio_top = math.log2(h / MASTER_TUNING_MIN_HZ)
    ratio_full = math.log2(MASTER_TUNING_MAX_HZ / MASTER_TUNING_MIN_HZ)
    t = ratio_top / ratio_full
    return int(round(t * 16383))


def master_tuning_hz_from_raw(raw: int) -> float:
    """Decodifica el valor 14-bit entrante a Hz (misma escala log que `master_tuning_raw_from_hz`)."""
    r = max(0, min(16383, int(raw)))
    if r <= 0:
        return MASTER_TUNING_MIN_HZ
    if r >= 16383:
        return MASTER_TUNING_MAX_HZ
    t = r / 16383
    return float(MASTER_TUNING_MIN_HZ * ((MASTER_TUNING_MAX_HZ / MASTER_TUNING_MIN_HZ) ** t))


def master_tuning_cents_from_raw(raw: int) -> float:
    """Cents relativos a La 440 a partir del raw 14-bit (coherente con Hz geométrico)."""
    hz = master_tuning_hz_from_raw(raw)
    return 1200.0 * math.log2(hz / MASTER_TUNING_REF_HZ)


def master_tuning_set(cents_offset: float) -> mido.Message:
    """Establece el master tuning (01 00 02 18).

    Rango útil ~415.3 Hz … 466.2 Hz respecto a La4=440 Hz (cents fuera se recortan).

    El raw 0…16383 sigue la escala log en Hz entre ``MASTER_TUNING_MIN_HZ`` y
    ``MASTER_TUNING_MAX_HZ`` (2 bytes 7-bit, MSB primero).
    """
    c = max(
        MASTER_TUNING_MIN_CENTS,
        min(MASTER_TUNING_MAX_CENTS, float(cents_offset)),
    )
    hz = MASTER_TUNING_REF_HZ * (2 ** (c / 1200))
    hz = max(MASTER_TUNING_MIN_HZ, min(MASTER_TUNING_MAX_HZ, hz))
    raw = master_tuning_raw_from_hz(hz)
    return roland_data_set_1((0x01, 0x00, 0x02, 0x18), (raw // 128, raw % 128))


def master_tuning_read() -> mido.Message:
    """Solicita el master tuning (RQ1). Respuesta en 01 00 02 18, 2 bytes."""
    return roland_data_request_1((0x01, 0x00, 0x02, 0x18), (0x00, 0x00, 0x00, 0x02))


def key_touch_set(value_0_5: int) -> mido.Message:
    """Establece la sensibilidad del teclado (01 00 02 1D).

    Orden como en Roland Piano App (captura Key Touch): 0 Fix, 1 Super Light, 2 Light,
    3 Medium, 4 Heavy, 5 Super Heavy.
    """
    if not 0 <= value_0_5 <= 5:
        msg = "Key Touch debe estar entre 0 y 5"
        raise ValueError(msg)
    return roland_data_set_1((0x01, 0x00, 0x02, 0x1D), (value_0_5,))


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
