"""Cadenas de interfaz (inglés por defecto, español)."""

from __future__ import annotations

from typing import Literal

Lang = Literal["en", "es"]

STRINGS: dict[Lang, dict[str, str]] = {
    "en": {
        "window_title": "Roland FP-30X Controller",
        "group_configuration": "Configuration",
        "group_main": "Main",
        "label_language": "Language",
        "label_device": "Device:",
        "label_instrument": "Instrument",
        "btn_metronome_off": "▶ Metronome",
        "btn_metronome_on": "■ Metronome",
        "label_tempo": "Tempo (BPM)",
        "btn_refresh": "Refresh",
        "btn_connect": "Connect",
        "btn_disconnect": "Disconnect",
        "label_master_volume": "Master Volume (RT)",
        "label_transpose": "Transpose",
        "tooltip_transpose": (
            "Sends Universal MIDI Master Coarse Tuning. 0 means no transpose."
        ),
        "tooltip_master_volume": "SysEx Master Volume - updates the piano panel LEDs.",
        "group_pedal": "Pedal",
        "pedal_sustain": "Hold 1 / sustain pedal (CC 64)",
        "btn_reset_defaults": "Reset to defaults",
        "status_no_midi": "No MIDI connection.",
        "status_midi_ports": "MIDI outputs: {no} · inputs: {ni}",
        "status_disconnected": "Disconnected.",
        "status_device_lost": "Device disconnected: {name}",
        "status_connected": "Connected to: {name}",
        "status_connected_sync": "Connected — output: {out} · piano input: {inn}.",
        "err_no_port": "No MIDI output device is available.",
        "err_open_port": "Could not open device:\n{error}",
        "status_defaults_offline": "Defaults restored (no MIDI sent).",
        "status_defaults_sent": "Defaults applied and sent to the piano.",
        "status_full_reapply": "Tone, pedal and master sent again to the piano.",
        "status_transpose_sent": "Transpose sent to the piano: {value:+d} semitones.",
        "status_transpose_offline": (
            "Transpose set to {value:+d} semitones; connect MIDI to send it."
        ),
        "status_transpose_unknown": "Transpose from piano not read yet.",
        "status_transpose_from_piano": "Transpose from piano: {value:+d} semitones.",
        "status_master_volume_sent": "Master volume sent: {value}.",
        "status_metronome_probe_sent": "Metronome toggled.",
        "status_piano_state_read": "Piano state read: volume {vol}, transpose {tr:+d}, metronome {metro}.",
        "status_preset_offline": (
            'Preset "{name}" selected; connect MIDI to send it to the piano.'
        ),
        "msg_connect_before_send": "Connect a MIDI output device before sending.",
        "status_bank_line": (
            "{prefix}bank {msb}/{lsb}, program doc={pdoc} → MIDI PC={pmidi}{latch}"
        ),
        "latch_suffix": " (latch Note On/Off)",
        "dlg_midi": "MIDI",
        "warn_input_open": (
            "Could not open MIDI input; tone sync from the piano is disabled.\n{error}"
        ),
        "status_tone_from_piano": "Tone from piano: {name}",
        "status_piano_tone_unknown": (
            "Piano tone not in the list (MSB {msb} LSB {lsb} program {pdoc})."
        ),
        "label_master_tuning": "Master Tuning",
        "tab_piano_designer": "Piano Designer",
        "pd_warning_title": "Piano Designer",
        "pd_warning_text": (
            "Piano Designer is only available for Single mode and specified piano tones.\n"
            "Would you like to change your settings to proceed?"
        ),
        "pd_warning_dont_show": "Don't show again",
        "pd_section_cabinet": "Cabinet",
        "pd_section_strings": "Strings",
        "pd_section_damper": "Damper",
        "pd_section_keyboard": "Keyboard",
        "pd_section_tuning": "Tuning",
        "pd_label_lid": "Lid",
        "pd_label_string_resonance": "String Resonance",
        "pd_label_damper_resonance": "Damper Resonance",
        "pd_label_key_off_resonance": "Key Off Resonance",
        "pd_label_temperament": "Temperament",
        "pd_label_temperament_key": "Temperament Key",
        "pd_label_individual_voicing": "Individual Note Voicing",
        "pd_btn_save": "Save to Piano",
        "pd_label_single_note_tuning": "Single Note Tuning",
        "pd_label_single_note_character": "Single Note Character",
        "pd_label_lock": "Lock",
        "pd_label_key": "Key",
        "tab_piano_settings": "Piano Settings",
        "tab_tones": "Tones",
        "tab_metronome": "Metronome",
        "tab_extra": "Extra",
        "label_key_touch": "Key Touch",
        "key_touch_fix": "Fix",
        "key_touch_light": "Light",
        "key_touch_medium": "Medium",
        "key_touch_heavy": "Heavy",
        "label_brilliance": "Brilliance",
        "label_ambience": "Ambience Depth",
        "label_connection": "Connection",
        # Tones tab
        "tone_mode_single": "Single",
        "tone_mode_split": "Split",
        "tone_mode_dual": "Dual",
        "tone_mode_twin": "Twin",
        "label_tone": "Tone",
        "label_right_tone": "Right Tone",
        "label_left_tone": "Left Tone",
        "label_tone_1": "Tone 1",
        "label_tone_2": "Tone 2",
        "label_balance": "Balance",
        "label_split_point": "Split Point",
        "label_right_shift": "Right Shift",
        "label_left_shift": "Left Shift",
        "label_tone1_shift": "Tone 1 Shift",
        "label_tone2_shift": "Tone 2 Shift",
        "label_twin_mode": "Mode",
        "twin_mode_pair": "Pair",
        "twin_mode_individual": "Individual",
        "label_category": "Category",
        # Metronome tab
        "label_bpm": "BPM",
        "label_metro_volume": "Volume",
        "label_metro_tone": "Tone",
        "label_metro_beat": "Beat",
        "btn_start": "Start",
        "btn_stop": "Stop",
        "metro_tone_click": "Click",
        "metro_tone_electronic": "Electronic",
        "metro_tone_japanese": "Japanese",
        "metro_tone_english": "English",
        # Extra tab
        "pedal_sustain": "Hold 1 / sustain pedal (CC 64)",
    },
    "es": {
        "window_title": "Controlador Roland FP-30X",
        "group_configuration": "Configuración",
        "group_main": "Principal",
        "label_language": "Idioma",
        "label_device": "Dispositivo:",
        "label_instrument": "Instrumento",
        "btn_metronome_off": "▶ Metrónomo",
        "btn_metronome_on": "■ Metrónomo",
        "label_tempo": "Tempo (BPM)",
        "btn_refresh": "Actualizar",
        "btn_connect": "Conectar",
        "btn_disconnect": "Desconectar",
        "label_master_volume": "Master Volume (RT)",
        "label_transpose": "Transposición",
        "tooltip_transpose": (
            "Envía Master Coarse Tuning del MIDI universal. 0 significa sin "
            "transposición."
        ),
        "tooltip_master_volume": "SysEx Master Volume - actualiza las luces del panel del piano.",
        "group_pedal": "Pedal",
        "pedal_sustain": "Hold 1 / sostenuto pedal (CC 64)",
        "btn_reset_defaults": "Restablecer valores por defecto",
        "status_no_midi": "Sin conexión MIDI.",
        "status_midi_ports": "MIDI salidas: {no} · entradas: {ni}",
        "status_disconnected": "Desconectado.",
        "status_device_lost": "Dispositivo desconectado: {name}",
        "status_connected": "Conectado a: {name}",
        "status_connected_sync": "Conectado — salida: {out} · entrada piano: {inn}.",
        "err_no_port": "No hay ningún dispositivo de salida disponible.",
        "err_open_port": "No se pudo abrir el dispositivo:\n{error}",
        "status_defaults_offline": "Valores restablecidos por defecto (sin enviar MIDI).",
        "status_defaults_sent": "Valores por defecto aplicados y enviados al piano.",
        "status_full_reapply": "Tono, pedal y master reenviados al piano.",
        "status_transpose_sent": "Transposición enviada al piano: {value:+d} semitonos.",
        "status_transpose_offline": (
            "Transposición ajustada a {value:+d} semitonos; conecta MIDI para enviarla."
        ),
        "status_transpose_unknown": "La transposición del piano aún no se ha leído.",
        "status_transpose_from_piano": (
            "Transposición desde el piano: {value:+d} semitonos."
        ),
        "status_master_volume_sent": "Master volume enviado: {value}.",
        "status_metronome_probe_sent": "Metrónomo conmutado.",
        "status_piano_state_read": "Estado del piano leído: volumen {vol}, transposición {tr:+d}, metrónomo {metro}.",
        "status_preset_offline": (
            "Preset «{name}» seleccionado; conecta MIDI para enviarlo al piano."
        ),
        "msg_connect_before_send": "Conecta un dispositivo de salida antes de enviar.",
        "status_bank_line": (
            "{prefix}banco {msb}/{lsb}, programa doc={pdoc} → MIDI PC={pmidi}{latch}"
        ),
        "latch_suffix": " (enganche Note On/Off)",
        "dlg_midi": "MIDI",
        "warn_input_open": (
            "No se pudo abrir la entrada MIDI; la sincronización de tono desde el "
            "piano está desactivada.\n{error}"
        ),
        "status_tone_from_piano": "Tono desde el piano: {name}",
        "status_piano_tone_unknown": (
            "Tono del piano no está en la lista (MSB {msb} LSB {lsb} programa {pdoc})."
        ),
        "tab_piano_settings": "Piano Settings",
        "tab_tones": "Tonos",
        "tab_metronome": "Metrónomo",
        "tab_extra": "Extra",
        "label_key_touch": "Key Touch",
        "key_touch_fix": "Fix",
        "key_touch_light": "Light",
        "key_touch_medium": "Medium",
        "key_touch_heavy": "Heavy",
        "label_brilliance": "Brilliance",
        "label_ambience": "Ambience Depth",
        "label_master_tuning": "Master Tuning",
        "tab_piano_designer": "Piano Designer",
        "pd_warning_title": "Piano Designer",
        "pd_warning_text": (
            "Piano Designer solo está disponible en modo Single y con tonos de piano específicos.\n"
            "¿Deseas cambiar tu configuración para continuar?"
        ),
        "pd_warning_dont_show": "No volver a mostrar",
        "pd_section_cabinet": "Tapa",
        "pd_section_strings": "Cuerdas",
        "pd_section_damper": "Apagador",
        "pd_section_keyboard": "Teclado",
        "pd_section_tuning": "Afinación",
        "pd_label_lid": "Apertura de tapa",
        "pd_label_string_resonance": "Resonancia de cuerdas",
        "pd_label_damper_resonance": "Resonancia del apagador",
        "pd_label_key_off_resonance": "Resonancia al soltar",
        "pd_label_temperament": "Temperamento",
        "pd_label_temperament_key": "Tónica del temperamento",
        "pd_label_individual_voicing": "Voicing individual de nota",
        "pd_btn_save": "Guardar en el piano",
        "pd_label_single_note_tuning": "Afinación de nota",
        "pd_label_single_note_character": "Carácter de nota",
        "pd_label_lock": "Bloquear",
        "pd_label_key": "Nota",
        "label_connection": "Conexión",
        # Tones tab
        "tone_mode_single": "Single",
        "tone_mode_split": "Split",
        "tone_mode_dual": "Dual",
        "tone_mode_twin": "Twin",
        "label_tone": "Tono",
        "label_right_tone": "Tono derecha",
        "label_left_tone": "Tono izquierda",
        "label_tone_1": "Tono 1",
        "label_tone_2": "Tono 2",
        "label_balance": "Balance",
        "label_split_point": "Punto de split",
        "label_right_shift": "Desplazamiento derecha",
        "label_left_shift": "Desplazamiento izquierda",
        "label_tone1_shift": "Desplazamiento tono 1",
        "label_tone2_shift": "Desplazamiento tono 2",
        "label_twin_mode": "Modo",
        "twin_mode_pair": "Par",
        "twin_mode_individual": "Individual",
        "label_category": "Categoría",
        # Metronome tab
        "label_bpm": "BPM",
        "label_metro_volume": "Volumen",
        "label_metro_tone": "Sonido",
        "label_metro_beat": "Compás",
        "btn_start": "Iniciar",
        "btn_stop": "Detener",
        "metro_tone_click": "Click",
        "metro_tone_electronic": "Electronic",
        "metro_tone_japanese": "Japanese",
        "metro_tone_english": "English",
        # Extra tab
        "pedal_sustain": "Hold 1 / pedal sustain (CC 64)",
    },
}


def tr(lang: Lang, key: str, **kwargs: object) -> str:
    s = STRINGS[lang][key]
    return s.format(**kwargs) if kwargs else s
