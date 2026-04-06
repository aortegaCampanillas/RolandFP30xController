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
        "btn_connect_help": "Help",
        "btn_read_piano_values": "Read piano values",
        "btn_read_piano_values_tip": (
            "Send RQ1 reads and print DT1 replies as traces on stderr (terminal / debug console)."
        ),
        "err_read_piano_needs_sync": (
            "Connect with a MIDI input port (same device) so the piano can answer. "
            "Read piano values needs incoming SysEx."
        ),
        "dlg_connect_help_title": "How to connect the FP-30X",
        "help_connect_skip_startup": "Don't show this dialog when the application starts",
        "help_connect_close": "Close",
        "help_connect_language": "Language",
        "help_connect_view_english": "English",
        "help_connect_view_spanish": "Español",
        "help_connect_body": (
            "This app controls your piano over MIDI. The FP-30X must appear as one or more MIDI "
            "ports in the operating system (use Refresh in this app if you do not see it).\n\n"
            "USB CABLE (WIRED)\n"
            "• Turn the FP-30X on.\n"
            "• Connect the supplied USB cable from the piano’s USB port (often labeled Computer "
            "or USB) to your Mac or PC.\n"
            "• Wait a few seconds for the system to recognise the device. On many Macs no extra "
            "driver is needed; on Windows, install Roland’s USB driver if the piano does not "
            "show up as a MIDI device (see Roland’s support pages for your model and OS).\n"
            "• In this app: Refresh, pick the MIDI output that matches your FP-30X (names vary, "
            "e.g. FP-30X or Roland Digital Piano), then Connect.\n\n"
            "BLUETOOTH (WIRELESS) — IMPORTANT\n"
            "Audio Bluetooth and MIDI Bluetooth are not the same. This application needs MIDI. "
            "On macOS you normally do a system Bluetooth pairing first, then enable the MIDI "
            "device in Audio MIDI Setup.\n\n"
            "1) Put the piano in pairing mode\n"
            "• On the FP-30X, press and hold the Function button for about 5 seconds until the "
            "Bluetooth indicator blinks (check the owner’s manual for the exact LED pattern).\n\n"
            "2) Pair “FP-30X Audio” in system Bluetooth\n"
            "• Open System Settings → Bluetooth (or System Preferences → Bluetooth on older macOS).\n"
            "• Select FP-30X Audio (wording may differ slightly) and complete pairing.\n"
            "• This step often enables the audio profile; MIDI may still require step 3.\n\n"
            "3) Connect “FP-30X MIDI” in Audio MIDI Setup (macOS)\n"
            "• Open Audio MIDI Setup (Spotlight, or Applications → Utilities).\n"
            "• Menu Window → Show MIDI Studio.\n"
            "• Click the Bluetooth control in the MIDI Studio toolbar.\n"
            "• After a short scan, FP-30X MIDI should appear in the lower area. Select it and "
            "click Connect.\n"
            "• Return here, press Refresh, choose the FP-30X MIDI output, then Connect.\n\n"
            "WINDOWS (BLUETOOTH)\n"
            "• Pair the piano under Settings → Bluetooth & devices following Roland’s guide.\n"
            "• If no MIDI port appears, install or use Roland’s Bluetooth MIDI software/driver so "
            "Windows exposes a MIDI port; then Refresh and Connect in this app.\n\n"
            "IN THIS APPLICATION\n"
            "• Connect uses MIDI output. For two-way sync (reading the piano), the same "
            "instrument should also be available as MIDI input when possible.\n"
            "• If you unplug the cable or turn the piano off, press Refresh and connect again.\n"
            "• For the official procedure and troubleshooting, refer to Roland’s FP-30X "
            "documentation and Bluetooth/MIDI guides."
        ),
        "label_master_volume": "Master Volume (RT)",
        "label_transpose": "Transpose",
        "tooltip_transpose": (
            "Sends Universal MIDI Master Coarse Tuning. 0 means no transpose."
        ),
        "tooltip_master_volume": "SysEx Master Volume - updates the piano panel LEDs.",
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
        "status_transpose_sent": "Transpose sent to the piano: {value:+d} semitones.",
        "status_transpose_offline": (
            "Transpose set to {value:+d} semitones; connect MIDI to send it."
        ),
        "status_transpose_unknown": "Transpose from piano not read yet.",
        "status_transpose_from_piano": "Transpose from piano: {value:+d} semitones.",
        "status_master_volume_sent": "Master volume sent: {value}.",
        "status_metronome_probe_sent": "Metronome toggled.",
        "status_piano_state_read": (
            "Piano state read: volume {vol}, transpose {tr:+d}, metronome {metro}."
        ),
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
        "tab_piano_designer": "Piano Designer (Beta)",
        "inv_label_note": "Key",
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
        "pd_section_note_voicing": "Per-note voicing",
        "pd_label_lid": "Lid",
        "pd_label_string_resonance": "String Resonance",
        "pd_label_damper_resonance": "Damper Resonance",
        "pd_label_key_off_resonance": "Key Off Resonance",
        "pd_label_temperament": "Temperament",
        "pd_label_temperament_key": "Temperament Key",
        "pd_btn_save": "Save to Piano",
        "status_pd_saved": "Piano Designer settings saved to the piano.",
        "pd_label_single_note_tuning": "Single Note Tuning",
        "pd_label_single_note_character": "Single Note Character",
        "pd_label_lock": "Lock",
        "pd_label_key": "Key",
        "tab_piano_settings": "Piano Settings",
        "tab_tones": "Tones",
        "tab_metronome": "Metronome",
        "label_key_touch": "Key Touch",
        "key_touch_fix": "Fix",
        "key_touch_super_light": "Super Light",
        "key_touch_light": "Light",
        "key_touch_medium": "Medium",
        "key_touch_heavy": "Heavy",
        "key_touch_super_heavy": "Super Heavy",
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
        "label_metro_pattern": "Pattern",
        "metro_pattern_0": "Off",
        "metro_pattern_1": "8th",
        "metro_pattern_2": "Triplet",
        "metro_pattern_3": "Trip·2",
        "metro_pattern_4": "16th",
        "metro_pattern_5": "Trip·3",
        "metro_pattern_6": "Quarter",
        "metro_pattern_7": "8th·2",
        "btn_start": "Start",
        "btn_stop": "Stop",
        "metro_tone_click": "Click",
        "metro_tone_electronic": "Electronic",
        "metro_tone_japanese": "Japanese",
        "metro_tone_english": "English",
        "label_off": "Off",
        "dlg_yes": "Yes",
        "dlg_no": "No",
        "tone_cat_piano": "Piano",
        "tone_cat_epiano": "E.Piano",
        "tone_cat_organ": "Organ",
        "tone_cat_strings": "Strings",
        "tone_cat_pad": "Pad",
        "tone_cat_synth": "Synth",
        "tone_cat_other": "Other",
        "tone_cat_drums": "Drums",
        "tone_cat_gm2": "GM2",
        "pd_temp_equal": "Equal",
        "pd_temp_just_major": "Just Major",
        "pd_temp_just_minor": "Just Minor",
        "pd_temp_pythagorean": "Pythagorean",
        "pd_temp_kirnberger_1": "Kirnberger 1",
        "pd_temp_kirnberger_2": "Kirnberger 2",
        "pd_temp_kirnberger_3": "Kirnberger 3",
        "pd_temp_meantone": "Meantone",
        "pd_temp_werckmeister": "Werckmeister",
        "pd_temp_arabic": "Arabic",
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
        "btn_connect_help": "Ayuda",
        "btn_read_piano_values": "Leer valores del piano",
        "btn_read_piano_values_tip": (
            "Envía lecturas RQ1 y escribe las respuestas DT1 como trazas en stderr (terminal o consola de depuración)."
        ),
        "err_read_piano_needs_sync": (
            "Conecta usando un puerto MIDI de entrada (el mismo dispositivo) para que el piano pueda responder. "
            "Leer valores requiere recibir SysEx entrantes."
        ),
        "dlg_connect_help_title": "Cómo conectar la FP-30X",
        "help_connect_skip_startup": "No volver a mostrar este mensaje al iniciar la aplicación",
        "help_connect_close": "Cerrar",
        "help_connect_language": "Idioma",
        "help_connect_view_english": "English",
        "help_connect_view_spanish": "Español",
        "help_connect_body": (
            "Esta aplicación controla el piano por MIDI. La FP-30X debe aparecer en el sistema "
            "como uno o varios puertos MIDI (usa Actualizar en esta app si no los ves).\n\n"
            "CABLE USB (CONEXIÓN POR CABLE)\n"
            "• Enciende la FP-30X.\n"
            "• Conecta el cable USB suministrado desde el puerto USB del piano (a menudo "
            "etiquetado como Computer o USB) al Mac o PC.\n"
            "• Espera unos segundos a que el sistema reconozca el dispositivo. En muchos Mac no "
            "hace falta driver adicional; en Windows, instala el driver USB de Roland si el "
            "piano no aparece como MIDI (consulta el soporte de Roland para tu modelo y sistema).\n"
            "• En esta app: Actualizar, elige la salida MIDI que corresponda a tu FP-30X (el "
            "nombre varía, p. ej. FP-30X o Roland Digital Piano) y pulsa Conectar.\n\n"
            "BLUETOOTH (INALÁMBRICO) — IMPORTANTE\n"
            "El audio por Bluetooth y el MIDI por Bluetooth no son lo mismo. Esta aplicación "
            "necesita MIDI. En macOS sueles emparejar antes en Ajustes del sistema y luego "
            "activar el MIDI en Configuración de audio y MIDI.\n\n"
            "1) Modo emparejamiento en el piano\n"
            "• En la FP-30X, mantén pulsado el botón de función (Function) unos 5 segundos hasta "
            "que el indicador Bluetooth parpadee (consulta el manual para el patrón exacto del "
            "LED).\n\n"
            "2) Emparejar «FP-30X Audio» en Bluetooth del sistema\n"
            "• Abre Ajustes del sistema → Bluetooth (o Preferencias del sistema → Bluetooth en "
            "macOS antiguos).\n"
            "• En la lista, selecciona FP-30X Audio (el nombre puede variar ligeramente) y "
            "completa el emparejamiento.\n"
            "• Este paso suele cubrir el perfil de audio; el MIDI puede requerir el paso 3.\n\n"
            "3) Conectar «FP-30X MIDI» en Configuración de audio y MIDI (macOS)\n"
            "• Abre Configuración de audio y MIDI (Spotlight, o Aplicaciones → Utilidades).\n"
            "• Menú Ventana → Mostrar estudio MIDI.\n"
            "• Pulsa el botón o icono de Bluetooth en la barra del Estudio MIDI.\n"
            "• Tras un breve escaneo debería aparecer abajo FP-30X MIDI. Selecciónalo y pulsa "
            "Conectar.\n"
            "• Vuelve aquí, pulsa Actualizar, elige la salida MIDI de la FP-30X y Conectar.\n\n"
            "WINDOWS (BLUETOOTH)\n"
            "• Empareja el piano en Configuración → Bluetooth y dispositivos siguiendo la guía "
            "de Roland.\n"
            "• Si no aparece ningún puerto MIDI, instala o usa el software/driver Bluetooth MIDI "
            "de Roland para que Windows exponga un puerto MIDI; luego Actualizar y Conectar en "
            "esta app.\n\n"
            "EN ESTA APLICACIÓN\n"
            "• Conectar usa la salida MIDI. Para sincronización en dos sentidos (leer el piano), "
            "conviene que el mismo instrumento esté también como entrada MIDI cuando sea posible.\n"
            "• Si desenchufas o apagas el piano, pulsa Actualizar y vuelve a conectar.\n"
            "• Para el procedimiento oficial y resolución de problemas, consulta la documentación "
            "de Roland para la FP-30X y las guías de Bluetooth/MIDI."
        ),
        "label_master_volume": "Volumen maestro (RT)",
        "label_transpose": "Transposición",
        "tooltip_transpose": (
            "Envía Master Coarse Tuning del MIDI universal. 0 significa sin "
            "transposición."
        ),
        "tooltip_master_volume": "SysEx Master Volume - actualiza las luces del panel del piano.",
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
        "status_transpose_sent": "Transposición enviada al piano: {value:+d} semitonos.",
        "status_transpose_offline": (
            "Transposición ajustada a {value:+d} semitonos; conecta MIDI para enviarla."
        ),
        "status_transpose_unknown": "La transposición del piano aún no se ha leído.",
        "status_transpose_from_piano": (
            "Transposición desde el piano: {value:+d} semitonos."
        ),
        "status_master_volume_sent": "Volumen maestro enviado: {value}.",
        "status_metronome_probe_sent": "Metrónomo conmutado.",
        "status_piano_state_read": (
            "Estado del piano leído: volumen {vol}, transposición {tr:+d}, "
            "metrónomo {metro}."
        ),
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
        "tab_piano_settings": "Ajustes del piano",
        "tab_tones": "Tonos",
        "tab_metronome": "Metrónomo",
        "label_key_touch": "Tacto de teclas",
        "key_touch_fix": "Fijo",
        "key_touch_super_light": "Super suave",
        "key_touch_light": "Suave",
        "key_touch_medium": "Medio",
        "key_touch_heavy": "Fuerte",
        "key_touch_super_heavy": "Super fuerte",
        "label_brilliance": "Brillo",
        "label_ambience": "Profundidad del ambiente",
        "label_master_tuning": "Afinación maestra",
        "tab_piano_designer": "Piano Designer (Beta)",
        "inv_label_note": "Tecla",
        "pd_warning_title": "Piano Designer",
        "pd_warning_text": (
            "Piano Designer solo está disponible en modo Simple y con tonos de piano específicos.\n"
            "¿Deseas cambiar tu configuración para continuar?"
        ),
        "pd_warning_dont_show": "No volver a mostrar",
        "pd_section_cabinet": "Tapa",
        "pd_section_strings": "Cuerdas",
        "pd_section_damper": "Apagador",
        "pd_section_keyboard": "Teclado",
        "pd_section_tuning": "Afinación",
        "pd_section_note_voicing": "Voicing por nota",
        "pd_label_lid": "Apertura de tapa",
        "pd_label_string_resonance": "Resonancia de cuerdas",
        "pd_label_damper_resonance": "Resonancia del apagador",
        "pd_label_key_off_resonance": "Resonancia al soltar",
        "pd_label_temperament": "Temperamento",
        "pd_label_temperament_key": "Tónica del temperamento",
        "pd_btn_save": "Guardar en el piano",
        "status_pd_saved": "Ajustes de Piano Designer guardados en el piano.",
        "pd_label_single_note_tuning": "Afinación de nota",
        "pd_label_single_note_character": "Carácter de nota",
        "pd_label_lock": "Bloquear",
        "pd_label_key": "Nota",
        "label_connection": "Conexión",
        # Tones tab
        "tone_mode_single": "Simple",
        "tone_mode_split": "Split",
        "tone_mode_dual": "Dual",
        "tone_mode_twin": "Twin",
        "label_tone": "Tono",
        "label_right_tone": "Tono derecha",
        "label_left_tone": "Tono izquierda",
        "label_tone_1": "Tono 1",
        "label_tone_2": "Tono 2",
        "label_balance": "Equilibrio",
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
        "label_metro_pattern": "Patrón",
        "metro_pattern_0": "Apagado",
        "metro_pattern_1": "1/8",
        "metro_pattern_2": "Trío",
        "metro_pattern_3": "Trío·2",
        "metro_pattern_4": "1/16",
        "metro_pattern_5": "Trío·3",
        "metro_pattern_6": "1/4",
        "metro_pattern_7": "1/8·2",
        "btn_start": "Iniciar",
        "btn_stop": "Detener",
        "metro_tone_click": "Clic",
        "metro_tone_electronic": "Electrónico",
        "metro_tone_japanese": "Japonés",
        "metro_tone_english": "Inglés",
        "label_off": "Apagado",
        "dlg_yes": "Sí",
        "dlg_no": "No",
        "tone_cat_piano": "Piano",
        "tone_cat_epiano": "Piano eléctrico",
        "tone_cat_organ": "Órgano",
        "tone_cat_strings": "Cuerdas",
        "tone_cat_pad": "Pad",
        "tone_cat_synth": "Sintetizador",
        "tone_cat_other": "Otros",
        "tone_cat_drums": "Batería",
        "tone_cat_gm2": "GM2",
        "pd_temp_equal": "Igual",
        "pd_temp_just_major": "Justa mayor",
        "pd_temp_just_minor": "Justa menor",
        "pd_temp_pythagorean": "Pitagórica",
        "pd_temp_kirnberger_1": "Kirnberger 1",
        "pd_temp_kirnberger_2": "Kirnberger 2",
        "pd_temp_kirnberger_3": "Kirnberger 3",
        "pd_temp_meantone": "Mesotonal",
        "pd_temp_werckmeister": "Werckmeister",
        "pd_temp_arabic": "Árabe",
    },
}


def tr(lang: Lang, key: str, **kwargs: object) -> str:
    s = STRINGS[lang][key]
    return s.format(**kwargs) if kwargs else s
