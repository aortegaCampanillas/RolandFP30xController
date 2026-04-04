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
        "btn_refresh": "Refresh",
        "btn_connect": "Connect",
        "btn_disconnect": "Disconnect",
        "label_master_volume": "Master Volume (RT)",
        "tooltip_master_volume": (
            "SysEx “Master Volume” (universal MIDI). If the piano does not respond, "
            "use part volume (CC 7) in Mix."
        ),
        "group_mix": "Mix (part Control Change)",
        "mix_volume": "Volume (CC 7)",
        "mix_expression": "Expression (CC 11)",
        "mix_pan": "Pan (CC 10)",
        "mix_modulation": "Modulation (CC 1)",
        "mix_reverb": "Reverb send (CC 91)",
        "mix_chorus": "Chorus send (CC 93)",
        "tooltip_reverb": (
            "Part send to the reverb bus (CC 91). Also sends GM2 tail time (SysEx) "
            "so the change is easier to hear on the FP-30X."
        ),
        "group_pedal": "Pedal",
        "pedal_sustain": "Hold 1 / sustain pedal (CC 64)",
        "btn_reset_defaults": "Reset to defaults",
        "status_no_midi": "No MIDI connection.",
        "status_midi_ports": "MIDI outputs: {no} · inputs: {ni}",
        "status_disconnected": "Disconnected.",
        "status_connected": "Connected to: {name}",
        "status_connected_sync": "Connected — output: {out} · piano input: {inn}.",
        "err_no_port": "No MIDI output device is available.",
        "err_open_port": "Could not open device:\n{error}",
        "status_defaults_offline": "Defaults restored (no MIDI sent).",
        "status_defaults_sent": "Defaults applied and sent to the piano.",
        "status_full_reapply": "Tone, mix, pedal and master sent again to the piano.",
        "status_preset_offline": (
            'Preset “{name}” selected; connect MIDI to send it to the piano.'
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
    },
    "es": {
        "window_title": "Controlador Roland FP-30X",
        "group_configuration": "Configuración",
        "group_main": "Principal",
        "label_language": "Idioma",
        "label_device": "Dispositivo:",
        "btn_refresh": "Actualizar",
        "btn_connect": "Conectar",
        "btn_disconnect": "Desconectar",
        "label_master_volume": "Master Volume (RT)",
        "tooltip_master_volume": (
            "SysEx «Master Volume» (MIDI universal). Si el piano no reacciona, "
            "usa el volumen de la parte (CC 7) en Mezcla."
        ),
        "group_mix": "Mezcla (Control Change por parte)",
        "mix_volume": "Volumen (CC 7)",
        "mix_expression": "Expresión (CC 11)",
        "mix_pan": "Pan (CC 10)",
        "mix_modulation": "Modulación (CC 1)",
        "mix_reverb": "Reverb send (CC 91)",
        "mix_chorus": "Chorus send (CC 93)",
        "tooltip_reverb": (
            "Envío de la parte al bus de reverb (CC 91). Además se envía tiempo de cola "
            "GM2 (SysEx) para que el cambio se note mejor en el FP-30X."
        ),
        "group_pedal": "Pedal",
        "pedal_sustain": "Hold 1 / sostenuto pedal (CC 64)",
        "btn_reset_defaults": "Restablecer valores por defecto",
        "status_no_midi": "Sin conexión MIDI.",
        "status_midi_ports": "MIDI salidas: {no} · entradas: {ni}",
        "status_disconnected": "Desconectado.",
        "status_connected": "Conectado a: {name}",
        "status_connected_sync": "Conectado — salida: {out} · entrada piano: {inn}.",
        "err_no_port": "No hay ningún dispositivo de salida disponible.",
        "err_open_port": "No se pudo abrir el dispositivo:\n{error}",
        "status_defaults_offline": "Valores restablecidos por defecto (sin enviar MIDI).",
        "status_defaults_sent": "Valores por defecto aplicados y enviados al piano.",
        "status_full_reapply": "Tono, mezcla, pedal y master reenviados al piano.",
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
    },
}


def tr(lang: Lang, key: str, **kwargs: object) -> str:
    s = STRINGS[lang][key]
    return s.format(**kwargs) if kwargs else s
