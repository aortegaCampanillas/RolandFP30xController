"""Cadenas de interfaz (inglés por defecto, español)."""

from __future__ import annotations

from typing import Literal

Lang = Literal["en", "es"]

STRINGS: dict[Lang, dict[str, str]] = {
    "en": {
        "window_title": "Roland FP-30X Controller",
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
        "group_tone": "Tone (Roland MIDI list)",
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
        "status_output_ports": "Output devices: {n}",
        "status_disconnected": "Disconnected.",
        "status_connected": "Connected to: {name}",
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
    },
    "es": {
        "window_title": "Controlador Roland FP-30X",
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
        "group_tone": "Tono (lista MIDI Roland)",
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
        "status_output_ports": "Dispositivos de salida: {n}",
        "status_disconnected": "Desconectado.",
        "status_connected": "Conectado a: {name}",
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
    },
}


def tr(lang: Lang, key: str, **kwargs: object) -> str:
    s = STRINGS[lang][key]
    return s.format(**kwargs) if kwargs else s
