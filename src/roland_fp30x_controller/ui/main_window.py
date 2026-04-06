from __future__ import annotations

import sys
import time
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import ClassVar

import mido
from PySide6.QtCore import QLocale, QSettings, Qt, QTimer
from PySide6.QtGui import QCloseEvent, QFont, QGuiApplication, QIcon
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from roland_fp30x_controller.midi import messages as midix
from roland_fp30x_controller.midi.bank_program_parser import BankProgramParser
from roland_fp30x_controller.midi.client import MidiOutClient
from roland_fp30x_controller.midi.ports import list_input_names, list_output_names
from roland_fp30x_controller.midi.rpn_parser import RpnParser, parse_master_coarse_tuning_sysex
from roland_fp30x_controller.midi.sysex_parser import parse_roland_dt1
from roland_fp30x_controller.midi.tone_catalog import (
    CATEGORIES,
    TONE_CATEGORIES,
    TONE_PRESETS,
    Tone,
    category_of,
    tone_dt1_encoding,
    tone_from_dt1_bytes,
)
from roland_fp30x_controller.ui.i18n import Lang, tr
from roland_fp30x_controller.ui.midi_in_worker import MidiInWorker


def _lang_from_settings_or_system_locale(settings: QSettings) -> Lang:
    """Idioma guardado, o en el primer arranque según el locale del sistema (p. ej. es_* → español)."""
    saved = settings.value("ui/lang")
    if saved in ("en", "es"):
        return saved  # type: ignore[return-value]
    primary = QLocale.system().name().replace("-", "_").split("_", 1)[0].lower()
    if primary == "es":
        return "es"
    return "en"


TONE_CATEGORY_I18N_KEYS: dict[str, str] = {
    "Piano": "tone_cat_piano",
    "E.Piano": "tone_cat_epiano",
    "Organ": "tone_cat_organ",
    "Strings": "tone_cat_strings",
    "Pad": "tone_cat_pad",
    "Synth": "tone_cat_synth",
    "Other": "tone_cat_other",
    "Drums": "tone_cat_drums",
    "GM2": "tone_cat_gm2",
}

DEFAULT_PRESET_INDEX = 0
MIDI_PART_CHANNEL = 4
DEFAULT_MASTER_VOLUME = midix.MASTER_VOLUME_DT1_MAX
DEFAULT_MASTER_TUNING_RAW = midix.master_tuning_raw_from_hz(midix.MASTER_TUNING_REF_HZ)
DEFAULT_TRANSPOSE = 0
DEFAULT_TEMPO = 120
DEFAULT_BRILLIANCE = 0
DEFAULT_AMBIENCE = 1
DEFAULT_KEY_TOUCH = 3  # Medium (orden 0..5 como app Roland, captura 31)
DEFAULT_KEYBOARD_MODE = 0   # Single
DEFAULT_BALANCE = 9  # centro (9:9); Dual acota slider a DUAL_BALANCE_PANEL_*; Split usa rango 0..18
DEFAULT_TWIN_MODE = 0       # Pair
DEFAULT_METRO_VOLUME = 5
DEFAULT_METRO_TONE = 0      # Click
DEFAULT_METRO_BEAT = 3      # 4/4 (valor SysEx del preset central)
DEFAULT_METRO_PATTERN = 0   # Off (01 00 02 20)
OCTAVE_SHIFT_MIN = -3
OCTAVE_SHIFT_MAX = 3

# Columnas en rejilla para compás y patrón (misma disposición que la app Roland).
METRO_GRID_COLS = 5

# Key Touch: mismos 6 valores y orden que Roland Piano App (docs/.../31 key tuch.png).
_KEY_TOUCH_I18N_KEYS = (
    "key_touch_fix",
    "key_touch_super_light",
    "key_touch_light",
    "key_touch_medium",
    "key_touch_heavy",
    "key_touch_super_heavy",
)

TEMPO_MIN = 20
TEMPO_MAX = 250
MASTER_VOL_DEBOUNCE_MS = 55
TEMPO_DEBOUNCE_MS = 120
PIANO_PATCH_IGNORE_S = 0.55
MASTER_VOL_IGNORE_DT1_S = 1.5
PORT_WATCHDOG_MS = 1000
# Sondeo RQ1 → DT1 para reflejar en la UI los cambios hechos en el panel del piano.
PIANO_STATE_POLL_INTERVAL_MS = 2500
# Tras un cambio desde la UI, no enviar RQ1 de estado completo durante este intervalo
# (evita que los DT1 devueltos pisen controles mientras el FP-30X aplica el valor).
PIANO_POLL_SUPPRESS_AFTER_USER_CHANGE_S = 2.0
# Espacio entre RQ1 consecutivos (evita saturar Bluetooth; más corto que DEFAULT_MESSAGE_GAP_S).
PIANO_POLL_MESSAGE_GAP_S = 0.004
# Tras cambiar Single/Split/Dual/Twin el piano necesita un instante; luego RQ1 de tonos.
TONE_REFRESH_AFTER_MODE_MS = 120
TONE_REFRESH_RETRY_WHEN_POPUP_OPEN_MS = 250
# Individual note voicing: índice 0..87 = 88 teclas desde La0 (MIDI 21).
INV_NOTE_MIDI_BASE = 21
INV_NOTE_COUNT = 88
INV_TUNING_DEBOUNCE_MS = 85

# Ventana inicial: más alta si hay pantalla (menos scroll en pestañas).
WINDOW_MIN_WIDTH = 560
WINDOW_DEFAULT_SIZE = (640, 740)
WINDOW_MAX_INITIAL_HEIGHT = 1000
WINDOW_SCREEN_MARGIN = 64

# Compás del metrónomo: (valor SysEx, numerador n en n/4) para los 6 botones de la app Roland.
#
# El PDF lista entradas 0=2/2, 1=3/2, 2=2/4, 3=3/4… pero los presets del panel no saltan el 1:
# son valores consecutivos 0..5 para 0/4, 2/4, 3/4, 4/4, 5/4, 6/4. Usar 2 para «2/4» hacía sonar 3/4.
BEAT_TABLE = [
    (0, 0),
    (1, 2),
    (2, 3),
    (3, 4),
    (4, 5),
    (5, 6),
]

_SUPERSCRIPT_DIGITS = "⁰¹²³⁴⁵⁶⁷⁸⁹"
_SUBSCRIPT_DIGITS = "₀₁₂₃₄₅₆₇₈₉"


def _beat_sig_unicode(numerator: int) -> str:
    """Notación tipo app Roland: numerador en superíndice, denominador 4 en subíndice."""
    return f"{_SUPERSCRIPT_DIGITS[numerator]}\u2044{_SUBSCRIPT_DIGITS[4]}"


# Patrón 0 = Off (texto vía i18n). Resto: glifos musicales como en la app Roland.
_METRO_PATTERN_GLYPHS: tuple[str | None, ...] = (
    None,
    "\u266b",  # corcheas enlazadas
    "\u266a\u266a\u266a\u2083",  # tríolo de corcheas
    "\u266b\u2082",  # variante tríolo (Trip·2)
    "\u266c",  # semicorcheas enlazadas
    "\u266c\u2083",  # variante tríolo 16 (Trip·3)
    "\u2669",  # negra
    "\u266a",  # corchea
)

# Note names for split point display
NOTE_NAMES_EN = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
NOTE_NAMES_ES = ["Do", "Do#", "Re", "Re#", "Mi", "Fa", "Fa#", "Sol", "Sol#", "La", "La#", "Si"]

DEFAULT_SPLIT_POINT = 54  # F#3 like Roland app

# Listas desplegables: mismo número de filas visibles salvo listas muy largas (tonos).
COMBO_MAX_VISIBLE = 24
COMBO_MAX_VISIBLE_TONE_LIST = 30


def _configure_combo(cb: QComboBox, *, max_visible: int = COMBO_MAX_VISIBLE) -> None:
    cb.setMaxVisibleItems(max_visible)


def midi_note_name(note: int, lang: Lang) -> str:
    names = NOTE_NAMES_ES if lang == "es" else NOTE_NAMES_EN
    return f"{names[note % 12]}{note // 12 - 1}"


class SegmentedBar(QWidget):
    """Barra de botones segmentada estilo Roland App (Single/Split/Dual/Twin)."""

    def __init__(self, labels: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        self.setStyleSheet(
            "SegmentedBar { background-color: #2c2c2e; border-radius: 8px; }"
        )
        self._buttons: list[QPushButton] = []
        for i, label in enumerate(labels):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setChecked(i == 0)
            btn.setStyleSheet(self._btn_style(i == 0))
            btn.toggled.connect(lambda checked, b=btn: b.setStyleSheet(self._btn_style(checked)))
            self._group.addButton(btn, i)
            layout.addWidget(btn)
            self._buttons.append(btn)

    @staticmethod
    def _btn_style(active: bool) -> str:
        if active:
            return (
                "QPushButton { background-color: #E07828; color: #ffffff; "
                "border: none; border-radius: 6px; padding: 3px 8px; font-size: 12px; }"
            )
        return (
            "QPushButton { background-color: transparent; color: #888888; "
            "border: none; border-radius: 6px; padding: 3px 8px; font-size: 12px; }"
            "QPushButton:hover { color: #e0e0e0; }"
        )

    def current_index(self) -> int:
        return self._group.checkedId()

    def set_index(self, idx: int) -> None:
        btn = self._group.button(idx)
        if btn:
            btn.setChecked(True)

    def connect_changed(self, slot) -> None:  # type: ignore[override]
        self._group.idToggled.connect(lambda bid, checked: slot(bid) if checked else None)

    def set_labels(self, labels: list[str]) -> None:
        for i, text in enumerate(labels):
            if i < len(self._buttons):
                self._buttons[i].setText(text)


class TonePicker(QWidget):
    """Widget de selección de tono: combo de categoría + combo de tono."""

    def __init__(
        self,
        label: str,
        parent: QWidget | None = None,
        *,
        category_label: Callable[[str], str] | None = None,
    ) -> None:
        super().__init__(parent)
        self._populating = False
        self._category_label = category_label or (lambda c: c)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)

        # Header row: label
        self._label = QLabel(label)
        v.addWidget(self._label)

        # Category + tone combos in a row
        row = QHBoxLayout()
        self._cat_combo = QComboBox()
        _configure_combo(self._cat_combo)
        for cat in CATEGORIES:
            self._cat_combo.addItem(self._category_label(cat), cat)
        self._tone_combo = QComboBox()
        _configure_combo(self._tone_combo, max_visible=COMBO_MAX_VISIBLE_TONE_LIST)
        self._cat_combo.currentIndexChanged.connect(self._on_cat_changed)
        row.addWidget(self._cat_combo)
        row.addWidget(self._tone_combo, stretch=1)
        v.addLayout(row)

        self._populate_tones(CATEGORIES[0])
        self._tone_callback = None

    def _on_cat_changed(self, _idx: int) -> None:
        cat = self._cat_combo.currentData()
        if not isinstance(cat, str):
            cat = CATEGORIES[0]
        self._populate_tones(cat)
        if self._tone_callback and not self._populating:
            self._tone_callback(self.current_tone())

    def _populate_tones(self, category: str) -> None:
        self._populating = True
        self._tone_combo.blockSignals(True)
        self._tone_combo.clear()
        for t in TONE_CATEGORIES.get(category, []):
            self._tone_combo.addItem(t.name, t)
        self._tone_combo.blockSignals(False)
        self._populating = False

    def set_tone_changed_callback(self, cb) -> None:  # type: ignore[override]
        self._tone_callback = cb
        self._tone_combo.currentIndexChanged.connect(
            lambda _: cb(self.current_tone()) if not self._populating else None
        )

    def current_tone(self) -> Tone | None:
        idx = self._tone_combo.currentIndex()
        if idx < 0:
            return None
        data = self._tone_combo.itemData(idx)
        return data if isinstance(data, Tone) else None

    def set_tone(self, tone: Tone) -> None:
        from roland_fp30x_controller.midi.tone_catalog import category_of
        cat = category_of(tone)
        self._populating = True
        self._cat_combo.blockSignals(True)
        self._tone_combo.blockSignals(True)
        found = False
        for i in range(self._cat_combo.count()):
            if self._cat_combo.itemData(i) == cat:
                self._cat_combo.setCurrentIndex(i)
                found = True
                break
        if not found:
            self._cat_combo.setCurrentIndex(0)
            cat = self._cat_combo.currentData()
            if not isinstance(cat, str):
                cat = CATEGORIES[0]
        self._cat_combo.blockSignals(False)
        self._populate_tones(cat)
        for i in range(self._tone_combo.count()):
            if self._tone_combo.itemData(i) == tone:
                self._tone_combo.setCurrentIndex(i)
                break
        self._tone_combo.blockSignals(False)
        self._populating = False

    def set_label(self, text: str) -> None:
        self._label.setText(text)

    def has_open_popup(self) -> bool:
        return self._cat_combo.view().isVisible() or self._tone_combo.view().isVisible()

    def retranslate_categories(self, label_fn: Callable[[str], str]) -> None:
        self._category_label = label_fn
        cur = self._cat_combo.currentData()
        self._cat_combo.blockSignals(True)
        self._cat_combo.clear()
        for cat in CATEGORIES:
            self._cat_combo.addItem(self._category_label(cat), cat)
        if isinstance(cur, str):
            for i in range(self._cat_combo.count()):
                if self._cat_combo.itemData(i) == cur:
                    self._cat_combo.setCurrentIndex(i)
                    break
        self._cat_combo.blockSignals(False)


class MainWindow(QMainWindow):
    _TEMPERAMENT_I18N_KEYS: tuple[str, ...] = (
        "pd_temp_equal",
        "pd_temp_just_major",
        "pd_temp_just_minor",
        "pd_temp_pythagorean",
        "pd_temp_kirnberger_1",
        "pd_temp_kirnberger_2",
        "pd_temp_kirnberger_3",
        "pd_temp_meantone",
        "pd_temp_werckmeister",
        "pd_temp_arabic",
    )

    # RQ1 → DT1 para «Read piano values» (nombre log, dirección de respuesta, fábrica del RQ1).
    _READ_PIANO_VALUE_SPECS: ClassVar[
        list[tuple[str, tuple[int, int, int, int], Callable[[], mido.Message]]]
    ] = [
        ("master_volume", (0x01, 0x00, 0x02, 0x13), midix.master_volume_read),
        ("sequencer_tempo", (0x01, 0x00, 0x01, 0x08), midix.metronome_read_tempo),
        ("metronome_status", (0x01, 0x00, 0x01, 0x0F), midix.metronome_read_status),
        ("key_transpose", (0x01, 0x00, 0x01, 0x01), midix.key_transpose_read),
        ("brilliance", (0x01, 0x00, 0x02, 0x1C), midix.brilliance_read),
        ("ambience", (0x01, 0x00, 0x02, 0x1A), midix.ambience_read),
        ("key_touch", (0x01, 0x00, 0x02, 0x1D), midix.key_touch_read),
        ("keyboard_mode", (0x01, 0x00, 0x02, 0x00), midix.keyboard_mode_read),
        ("master_tuning", (0x01, 0x00, 0x02, 0x18), midix.master_tuning_read),
        ("metronome_volume", (0x01, 0x00, 0x02, 0x21), midix.metronome_volume_read),
        ("metronome_tone", (0x01, 0x00, 0x02, 0x22), midix.metronome_tone_read),
        ("metronome_beat", (0x01, 0x00, 0x02, 0x1F), midix.metronome_beat_read),
        ("metronome_pattern", (0x01, 0x00, 0x02, 0x20), midix.metronome_pattern_read),
        ("split_point", (0x01, 0x00, 0x02, 0x01), midix.split_point_read),
        ("split_right_octave_shift", (0x01, 0x00, 0x02, 0x16), midix.split_right_octave_shift_read),
        ("split_left_octave_shift", (0x01, 0x00, 0x02, 0x02), midix.split_octave_shift_read),
        ("split_balance", (0x01, 0x00, 0x02, 0x03), midix.split_balance_read),
        ("dual_tone1_octave_shift", (0x01, 0x00, 0x02, 0x17), midix.dual_tone1_octave_shift_read),
        ("dual_tone2_octave_shift", (0x01, 0x00, 0x02, 0x04), midix.dual_octave_shift_read),
        ("dual_balance", (0x01, 0x00, 0x02, 0x05), midix.dual_balance_read),
        ("twin_piano_mode", (0x01, 0x00, 0x02, 0x06), midix.twin_piano_mode_read),
        ("tone_single", (0x01, 0x00, 0x02, 0x07), midix.tone_for_single_read),
        ("tone_split_left", (0x01, 0x00, 0x02, 0x0A), midix.tone_for_split_read),
        ("tone_dual_layer", (0x01, 0x00, 0x02, 0x0D), midix.tone_for_dual_read),
    ]

    def __init__(self, *, verbose: bool = False, debug: bool = False) -> None:
        super().__init__()
        _icon_path = Path(__file__).resolve().parent.parent / "resources" / "app_icon.svg"
        if _icon_path.is_file():
            self.setWindowIcon(QIcon(str(_icon_path)))
        self._verbose = verbose
        self._debug = debug
        self._settings = QSettings("RolandFP30xController", "RolandFP30xController")
        self._lang: Lang = _lang_from_settings_or_system_locale(self._settings)
        self._last_output_port: str | None = None
        self._last_input_port: str | None = None
        self._midi = MidiOutClient(
            trace_send=self._trace_midi_out if verbose else None,
        )
        self._midi_in_worker: MidiInWorker | None = None
        self._bank_parser = BankProgramParser((1, MIDI_PART_CHANNEL))
        self._rpn_parser = RpnParser((1, MIDI_PART_CHANNEL))
        self._ignore_piano_patch_until = 0.0
        self._master_vol_sent_at = 0.0
        self._transpose_known = False
        self._metronome_on: bool | None = None
        self._suppress_slider_midi = False
        self._midi_sync_updating = False
        self._keyboard_mode = DEFAULT_KEYBOARD_MODE

        self._master_vol_debounce_timer = QTimer(self)
        self._master_vol_debounce_timer.setSingleShot(True)
        self._master_vol_debounce_timer.timeout.connect(self._send_master_volume)

        self._piano_poll_suppress_until = 0.0
        self._piano_poll_timer = QTimer(self)
        self._piano_poll_timer.setInterval(PIANO_STATE_POLL_INTERVAL_MS)
        self._piano_poll_timer.timeout.connect(self._request_piano_state)

        self._tone_refresh_after_mode_timer = QTimer(self)
        self._tone_refresh_after_mode_timer.setSingleShot(True)
        self._tone_refresh_after_mode_timer.setInterval(TONE_REFRESH_AFTER_MODE_MS)
        self._tone_refresh_after_mode_timer.timeout.connect(self._request_tones_from_piano)

        self._tempo_debounce_timer = QTimer(self)
        self._tempo_debounce_timer.setSingleShot(True)
        self._tempo_debounce_timer.timeout.connect(self._flush_tempo)

        self._inv_tuning_debounce_timer = QTimer(self)
        self._inv_tuning_debounce_timer.setSingleShot(True)
        self._inv_tuning_debounce_timer.timeout.connect(self._flush_inv_tuning)

        self._port_watchdog_timer = QTimer(self)
        self._port_watchdog_timer.setInterval(PORT_WATCHDOG_MS)
        self._port_watchdog_timer.timeout.connect(self._check_connected_ports)
        self._port_watchdog_timer.start()

        self._piano_values_read_active = False
        self._piano_values_read_pending: dict[tuple[int, int, int, int], str] = {}
        self._piano_values_read_timer = QTimer(self)
        self._piano_values_read_timer.setSingleShot(True)
        self._piano_values_read_timer.timeout.connect(self._piano_values_read_timeout)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_connection_panel())

        # Todo lo que depende del piano (pestañas + reset): se deshabilita junto al desconectar.
        self._piano_controls_wrap = QWidget()
        piano_outer = QVBoxLayout(self._piano_controls_wrap)
        piano_outer.setContentsMargins(0, 0, 0, 0)
        piano_outer.setSpacing(0)

        self._tab_widget = QTabWidget()
        self._tab_widget.addTab(self._build_piano_settings_tab(), "")
        self._tab_widget.addTab(self._build_tones_tab(), "")
        self._tab_widget.addTab(self._build_metronome_tab(), "")
        self._tab_widget.addTab(self._build_piano_designer_tab(), "")
        self._pd_warning_shown = self._settings.value("pd_warning_shown", False, type=bool)
        piano_outer.addWidget(self._tab_widget, stretch=1)

        self._piano_footer_wrap = QWidget()
        reset_bar = QHBoxLayout(self._piano_footer_wrap)
        reset_bar.setContentsMargins(16, 8, 16, 8)
        self._reset_btn = QPushButton()
        self._reset_btn.clicked.connect(self._reset_defaults)
        reset_bar.addWidget(self._reset_btn)
        reset_bar.addStretch(1)
        piano_outer.addWidget(self._piano_footer_wrap)

        root.addWidget(self._piano_controls_wrap, stretch=1)

        self._status = QLabel()
        self._status.setObjectName("statusLabel")
        self._status.setWordWrap(True)
        self._status.setContentsMargins(16, 0, 16, 8)
        root.addWidget(self._status)

        self._retranslate_ui()
        self._refresh_ports()
        self._apply_initial_window_size()
        self._sync_connection_dependent_controls()
        QTimer.singleShot(150, self._maybe_show_connect_help_on_startup)

    def _sync_connection_dependent_controls(self) -> None:
        connected = self._midi.is_open
        self._piano_controls_wrap.setEnabled(connected)
        if connected:
            self._tab_widget.setGraphicsEffect(None)
            self._piano_footer_wrap.setGraphicsEffect(None)
        else:
            # setGraphicsEffect(None) destruye el efecto anterior; no reutilizar punteros guardados.
            tab_fx = QGraphicsOpacityEffect(self._tab_widget)
            tab_fx.setOpacity(0.42)
            foot_fx = QGraphicsOpacityEffect(self._piano_footer_wrap)
            foot_fx.setOpacity(0.42)
            self._tab_widget.setGraphicsEffect(tab_fx)
            self._piano_footer_wrap.setGraphicsEffect(foot_fx)
        self._repaint_piano_controls_area()
        if not connected:

            def _deferred_repaint() -> None:
                if not self._midi.is_open:
                    self._repaint_piano_controls_area()

            QTimer.singleShot(0, _deferred_repaint)
        if hasattr(self, "_read_piano_values_btn"):
            self._read_piano_values_btn.setVisible(self._debug)
            self._read_piano_values_btn.setEnabled(
                self._debug and connected and bool(self._last_input_port)
            )

    def _repaint_piano_controls_area(self) -> None:
        """Fuerza repintado del bloque de pestañas (incl. viewports) y del pie."""
        w = self._piano_controls_wrap
        w.update()
        w.repaint()
        tw = self._tab_widget
        tw.update()
        tw.repaint()
        for i in range(tw.count()):
            page = tw.widget(i)
            if page is None:
                continue
            page.update()
            page.repaint()
            if isinstance(page, QScrollArea):
                vp = page.viewport()
                if vp is not None:
                    vp.update()
                    vp.repaint()
        self._piano_footer_wrap.update()
        self._piano_footer_wrap.repaint()

    def _apply_initial_window_size(self) -> None:
        self.setMinimumWidth(WINDOW_MIN_WIDTH)
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            w, h = WINDOW_DEFAULT_SIZE
            self.resize(w, h)
            return
        ag = screen.availableGeometry()
        usable_w = max(400, ag.width() - WINDOW_SCREEN_MARGIN)
        usable_h = max(480, ag.height() - WINDOW_SCREEN_MARGIN)
        # Altura: ~90 % del área útil, entre default y tope (evita ventana ridícula en 4K).
        target_h = int(min(WINDOW_MAX_INITIAL_HEIGHT, max(WINDOW_DEFAULT_SIZE[1], usable_h * 0.90)))
        target_h = min(target_h, usable_h)
        # Anchura: un poco más ancha si cabe (combos y pestañas).
        target_w = int(min(880, max(WINDOW_DEFAULT_SIZE[0], usable_w * 0.52)))
        target_w = min(target_w, usable_w)
        target_w = max(WINDOW_MIN_WIDTH, target_w)
        self.resize(target_w, target_h)

    # ── Translation helpers ──────────────────────────────────────────────────

    def _tr(self, key: str, **kwargs: object) -> str:
        return tr(self._lang, key, **kwargs)

    def _tone_category_label(self, cat: str) -> str:
        ikey = TONE_CATEGORY_I18N_KEYS.get(cat)
        return self._tr(ikey) if ikey else cat

    def _trace_midi_out(self, msg: mido.Message) -> None:
        self._print_midi_trace("OUT", msg)

    def _print_midi_trace(self, direction: str, msg: mido.Message) -> None:
        try:
            raw = " ".join(f"{b:02X}" for b in msg.bytes())
        except (AttributeError, ValueError, TypeError):
            raw = "?"
        print(f"MIDI [{direction}] {msg!s}  |  {raw}", file=sys.stderr, flush=True)

    def _piano_value_summary(self, pid: str, data: tuple[int, ...]) -> str:
        if not data:
            return "(sin datos)"
        try:
            if pid == "master_volume":
                return f"master_volume={data[0]}"
            if pid == "sequencer_tempo" and len(data) >= 2:
                return f"tempo_bpm={data[0] * 128 + data[1]}"
            if pid == "metronome_status":
                return f"metronome_on={bool(data[0])}"
            if pid == "key_transpose":
                return f"transpose_semitones={int(data[0]) - 64}"
            if pid == "brilliance":
                return f"brilliance={max(-1, min(1, data[0] - 64))}"
            if pid == "ambience":
                return f"ambience={max(0, min(10, data[0]))}"
            if pid == "key_touch":
                k = max(0, min(5, data[0]))
                names = (
                    "Fix",
                    "Super Light",
                    "Light",
                    "Medium",
                    "Heavy",
                    "Super Heavy",
                )
                return f"key_touch={names[k]} ({k})"
            if pid == "keyboard_mode":
                m = max(0, min(3, data[0]))
                modes = ("Single", "Split", "Dual", "TwinPiano")
                return f"keyboard_mode={modes[m]} ({m})"
            if pid == "master_tuning" and len(data) >= 2:
                raw_t = data[0] * 128 + data[1]
                hz = midix.master_tuning_hz_from_raw(raw_t)
                cents = midix.master_tuning_cents_from_raw(raw_t)
                cents = max(
                    midix.MASTER_TUNING_MIN_CENTS,
                    min(midix.MASTER_TUNING_MAX_CENTS, cents),
                )
                return f"master_tuning_cents={cents:.2f} ref_hz={hz:.1f}"
            if pid == "metronome_volume":
                return f"metronome_volume={data[0]}"
            if pid == "metronome_tone":
                t = max(0, min(3, data[0]))
                tones = ("Click", "Electronic", "Voice-JP", "Voice-EN")
                return f"metronome_tone={tones[t]} ({t})"
            if pid == "metronome_beat":
                return f"metronome_beat_index={data[0]}"
            if pid == "metronome_pattern":
                return f"metronome_pattern={data[0]}"
            if pid == "split_point":
                return f"split_point_midi={data[0]}"
            if pid == "split_right_octave_shift":
                return f"split_right_octave_shift={max(-4, min(4, int(data[0]) - 64))}"
            if pid == "split_left_octave_shift":
                return f"split_left_octave_shift={max(-4, min(4, int(data[0]) - 64))}"
            if pid == "split_balance":
                panel = midix.split_balance_panel_from_sysex_byte(data[0])
                left, right = midix.split_balance_display_lr(panel)
                return f"split_balance panel={panel} display={left}:{right} raw=0x{data[0]:02X}"
            if pid == "dual_tone1_octave_shift":
                return f"dual_tone1_octave_shift={max(-4, min(4, int(data[0]) - 64))}"
            if pid == "dual_tone2_octave_shift":
                return f"dual_tone2_octave_shift={max(-4, min(4, int(data[0]) - 64))}"
            if pid == "dual_balance":
                panel = midix.dual_balance_panel_from_sysex_byte(data[0])
                left, right = midix.dual_balance_display_lr(panel)
                return f"dual_balance panel={panel} display={left}:{right} raw=0x{data[0]:02X}"
            if pid == "twin_piano_mode":
                return f"twin_mode={data[0]} (0=Pair 1=Individual)"
            if pid in ("tone_single", "tone_split_left", "tone_dual_layer") and len(data) >= 3:
                tone = tone_from_dt1_bytes(data[0], data[1], data[2])
                num = data[1] * 128 + data[2]
                name = tone.name if tone else "?"
                return f"category={data[0]} num={num} name={name}"
        except (IndexError, ValueError, TypeError):
            pass
        return "raw=" + " ".join(f"{b:02X}" for b in data)

    def _print_piano_value_trace(self, pid: str, data: tuple[int, ...]) -> None:
        summary = self._piano_value_summary(pid, data)
        print(f"MIDI [VALUES] {pid}: {summary}", file=sys.stderr, flush=True)

    def _piano_values_read_finish_ok(self) -> None:
        self._piano_values_read_timer.stop()
        self._piano_values_read_active = False
        self._piano_values_read_pending.clear()
        print("=== Fin Read Piano Values ===\n", file=sys.stderr, flush=True)

    def _piano_values_read_timeout(self) -> None:
        if not self._piano_values_read_active:
            return
        for _addr, pid in self._piano_values_read_pending.items():
            print(f"MIDI [VALUES] {pid}: (sin respuesta a tiempo)", file=sys.stderr, flush=True)
        self._piano_values_read_pending.clear()
        self._piano_values_read_active = False
        print("=== Fin Read Piano Values (timeout) ===\n", file=sys.stderr, flush=True)

    def _on_read_piano_values_clicked(self) -> None:
        if not self._midi.is_open or not self._last_input_port:
            QMessageBox.information(
                self,
                self._tr("dlg_midi"),
                self._tr("err_read_piano_needs_sync"),
            )
            return
        if self._piano_values_read_active:
            return
        specs = self._READ_PIANO_VALUE_SPECS
        self._piano_values_read_pending = {addr: pid for pid, addr, _ in specs}
        self._piano_values_read_active = True
        self._piano_values_read_timer.stop()
        self._piano_values_read_timer.start(4500)
        print("\n=== Read Piano Values ===", file=sys.stderr, flush=True)
        msgs = [factory() for _pid, _addr, factory in self._READ_PIANO_VALUE_SPECS]
        try:
            for m in msgs:
                if not self._verbose:
                    self._print_midi_trace("OUT", m)
            self._midi.send_all_spaced(msgs, gap_s=0.05)
        except OSError:
            self._piano_values_read_timer.stop()
            self._piano_values_read_active = False
            self._piano_values_read_pending.clear()
            self._disconnect_device(
                status_key="status_device_lost",
                name=self._last_output_port or "?",
            )

    def _on_language_changed(self, index: int) -> None:
        if index < 0:
            return
        code = self._lang_combo.itemData(index)
        if code in ("en", "es"):
            self._lang = code
            self._settings.setValue("ui/lang", code)
            self._retranslate_ui()

    def _retranslate_ui(self) -> None:
        self.setWindowTitle(self._tr("window_title"))
        self._lang_lbl.setText(self._tr("label_language"))
        self._label_device.setText(self._tr("label_device"))
        self._refresh_btn.setText(self._tr("btn_refresh"))
        self._update_connect_button_text()
        self._connect_help_btn.setText(self._tr("btn_connect_help"))
        self._connect_help_btn.setToolTip(self._tr("dlg_connect_help_title"))
        self._read_piano_values_btn.setText(self._tr("btn_read_piano_values"))
        self._read_piano_values_btn.setToolTip(self._tr("btn_read_piano_values_tip"))
        # Tab labels
        self._tab_widget.setTabText(0, self._tr("tab_piano_settings"))
        self._tab_widget.setTabText(1, self._tr("tab_tones"))
        self._tab_widget.setTabText(2, self._tr("tab_metronome"))
        self._tab_widget.setTabText(3, self._tr("tab_piano_designer"))
        # Piano Designer labels
        self._pd_label_lid.setText(self._tr("pd_label_lid"))
        self._pd_label_string_res.setText(self._tr("pd_label_string_resonance"))
        self._pd_label_damper_res.setText(self._tr("pd_label_damper_resonance"))
        self._pd_label_key_off.setText(self._tr("pd_label_key_off_resonance"))
        self._pd_label_temperament.setText(self._tr("pd_label_temperament"))
        self._pd_label_temp_key.setText(self._tr("pd_label_temperament_key"))
        self._pd_save_btn.setText(self._tr("pd_btn_save"))
        if hasattr(self, "_inv_note_combo"):
            self._inv_section_title.setText(self._tr("pd_section_note_voicing"))
            self._inv_label_note.setText(self._tr("inv_label_note"))
            self._inv_label_tuning.setText(self._tr("pd_label_single_note_tuning"))
            self._inv_label_character.setText(self._tr("pd_label_single_note_character"))
            self._repopulate_inv_note_combo()
        # Piano Settings
        self._label_master_vol.setText(self._tr("label_master_volume"))
        self._label_master_tuning.setText(self._tr("label_master_tuning"))
        self._label_key_touch.setText(self._tr("label_key_touch"))
        self._label_brilliance.setText(self._tr("label_brilliance"))
        self._label_transpose.setText(self._tr("label_transpose"))
        self._label_ambience.setText(self._tr("label_ambience"))
        # Key Touch combo
        self._key_touch_combo.blockSignals(True)
        current_kt = self._key_touch_combo.currentIndex()
        self._key_touch_combo.clear()
        for key in _KEY_TOUCH_I18N_KEYS:
            self._key_touch_combo.addItem(self._tr(key))
        self._key_touch_combo.setCurrentIndex(max(0, current_kt))
        self._key_touch_combo.blockSignals(False)
        # Metronome
        self._label_tempo.setText(self._tr("label_bpm"))
        self._label_metro_vol.setText(self._tr("label_metro_volume"))
        if hasattr(self, "_label_metro_pattern"):
            self._label_metro_pattern.setText(self._tr("label_metro_pattern"))
            for i, btn in enumerate(self._pattern_btns):
                g = _METRO_PATTERN_GLYPHS[i]
                if g is None:
                    btn.setText(self._tr("metro_pattern_0"))
                btn.setToolTip(self._tr(f"metro_pattern_{i}"))
        self._update_metronome_btn()
        self._reset_btn.setText(self._tr("btn_reset_defaults"))
        # Tone pickers labels
        self._single_picker.set_label(self._tr("label_tone"))
        self._split_right_picker.set_label(self._tr("label_right_tone"))
        self._split_left_picker.set_label(self._tr("label_left_tone"))
        self._dual_picker1.set_label(self._tr("label_tone_1"))
        self._dual_picker2.set_label(self._tr("label_tone_2"))
        self._twin_picker.set_label(self._tr("label_tone"))
        self._label_split_balance.setText(self._tr("label_balance"))
        self._label_dual_balance.setText(self._tr("label_balance"))
        self._label_split_point.setText(self._tr("label_split_point"))
        self._label_split_right_shift.setText(self._tr("label_right_shift"))
        self._label_split_left_shift.setText(self._tr("label_left_shift"))
        self._label_dual_shift1.setText(self._tr("label_tone1_shift"))
        self._label_dual_shift2.setText(self._tr("label_tone2_shift"))
        self._label_twin_mode.setText(self._tr("label_twin_mode"))
        self._tones_seg.set_labels(
            [
                self._tr("tone_mode_single"),
                self._tr("tone_mode_split"),
                self._tr("tone_mode_dual"),
                self._tr("tone_mode_twin"),
            ]
        )
        self._twin_mode_seg.set_labels(
            [self._tr("twin_mode_pair"), self._tr("twin_mode_individual")]
        )
        self._update_split_point_label()
        # Metronome tone labels
        self._retranslate_metro_tone()
        for picker in (
            self._single_picker,
            self._split_right_picker,
            self._split_left_picker,
            self._dual_picker1,
            self._dual_picker2,
            self._twin_picker,
        ):
            picker.retranslate_categories(self._tone_category_label)
        if hasattr(self, "_pd_temp_combo"):
            for i, key in enumerate(self._TEMPERAMENT_I18N_KEYS):
                self._pd_temp_combo.setItemText(i, self._tr(key))
        if hasattr(self, "_pd_off_scale_labels"):
            for lbl in self._pd_off_scale_labels:
                lbl.setText(self._tr("label_off"))
        self._refresh_pd_resonance_value_labels()
        # Status
        if not self._midi.is_open:
            self._status.setText(self._tr("status_no_midi"))
        elif self._last_output_port:
            if self._midi_in_worker is not None and self._last_input_port:
                self._status.setText(
                    self._tr("status_connected_sync", out=self._last_output_port, inn=self._last_input_port)
                )
            else:
                self._status.setText(self._tr("status_connected", name=self._last_output_port))

    def _retranslate_metro_tone(self) -> None:
        if hasattr(self, "_metro_tone_seg"):
            self._metro_tone_seg.set_labels(
                [
                    self._tr("metro_tone_click"),
                    self._tr("metro_tone_electronic"),
                    self._tr("metro_tone_japanese"),
                    self._tr("metro_tone_english"),
                ]
            )

    def _update_connect_button_text(self) -> None:
        if self._midi.is_open:
            self._connect_btn.setText(self._tr("btn_disconnect"))
            self._connect_btn.setStyleSheet(
                "QPushButton { background-color: #E07828; color: #ffffff; "
                "border: 1px solid #E07828; border-radius: 6px; "
                "padding: 3px 12px; font-size: 13px; min-height: 22px; }"
                "QPushButton:hover { background-color: #f09040; border-color: #f09040; }"
                "QPushButton:pressed { background-color: #b05818; }"
            )
        else:
            self._connect_btn.setText(self._tr("btn_connect"))
            self._connect_btn.setStyleSheet("")

    def _maybe_show_connect_help_on_startup(self) -> None:
        if self._settings.value("connect_help_skip_startup", False, type=bool):
            return
        self._open_connect_help_dialog(show_skip_startup_checkbox=True)

    def _on_connect_help_clicked(self) -> None:
        self._open_connect_help_dialog()

    def _open_connect_help_dialog(self, *, show_skip_startup_checkbox: bool = False) -> None:
        dlg = QDialog(self)
        dlg.setModal(True)
        dlg.setMinimumWidth(540)
        dv = QVBoxLayout(dlg)
        dv.setContentsMargins(14, 14, 14, 14)
        dv.setSpacing(12)

        lang_row = QHBoxLayout()
        lang_lbl = QLabel()
        lang_row.addWidget(lang_lbl)
        btn_en = QPushButton()
        btn_es = QPushButton()
        btn_en.setCheckable(True)
        btn_es.setCheckable(True)
        lang_grp = QButtonGroup(dlg)
        lang_grp.setExclusive(True)
        lang_grp.addButton(btn_en)
        lang_grp.addButton(btn_es)
        lang_row.addWidget(btn_en)
        lang_row.addWidget(btn_es)
        lang_row.addStretch(1)
        dv.addLayout(lang_row)

        text = QPlainTextEdit()
        text.setReadOnly(True)
        text.setMinimumHeight(340)
        tf = QFont(text.font())
        tf.setPointSize(12)
        text.setFont(tf)
        text.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        dv.addWidget(text)
        dont_show: QCheckBox | None = None
        if show_skip_startup_checkbox:
            dont_show = QCheckBox()
            dont_show.setChecked(
                self._settings.value("connect_help_skip_startup", False, type=bool)
            )
            dv.addWidget(dont_show)
        row = QHBoxLayout()
        row.addStretch(1)
        btn_close = QPushButton()
        btn_close.setDefault(True)
        btn_close.clicked.connect(dlg.accept)
        row.addWidget(btn_close)
        dv.addLayout(row)

        help_lang_choice: list[Lang] = [self._lang]

        def apply_help_lang(code: Lang) -> None:
            help_lang_choice[0] = code
            dlg.setWindowTitle(tr(code, "dlg_connect_help_title"))
            lang_lbl.setText(tr(code, "help_connect_language"))
            text.setPlainText(tr(code, "help_connect_body"))
            if dont_show is not None:
                dont_show.setText(tr(code, "help_connect_skip_startup"))
            btn_close.setText(tr(code, "help_connect_close"))
            btn_en.setText(tr(code, "help_connect_view_english"))
            btn_es.setText(tr(code, "help_connect_view_spanish"))

        btn_en.toggled.connect(lambda c: c and apply_help_lang("en"))
        btn_es.toggled.connect(lambda c: c and apply_help_lang("es"))
        if self._lang == "en":
            btn_en.setChecked(True)
        else:
            btn_es.setChecked(True)

        dlg.exec()
        if dont_show is not None:
            self._settings.setValue("connect_help_skip_startup", dont_show.isChecked())
        chosen = help_lang_choice[0]
        if chosen != self._lang:
            self._lang = chosen
            self._settings.setValue("ui/lang", chosen)
            self._lang_combo.blockSignals(True)
            self._lang_combo.setCurrentIndex(0 if chosen == "en" else 1)
            self._lang_combo.blockSignals(False)
            self._retranslate_ui()

    # ── UI helpers ───────────────────────────────────────────────────────────

    def _make_separator(self) -> QFrame:
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #2c2c2e; border: none;")
        return sep

    def _make_scale_row(self, left: str, center: str | None, right: str) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        lbl_l = QLabel(left)
        lbl_l.setObjectName("scaleLabel")
        row.addWidget(lbl_l)
        if center is not None:
            lbl_c = QLabel(center)
            lbl_c.setObjectName("scaleLabel")
            lbl_c.setAlignment(Qt.AlignmentFlag.AlignCenter)
            row.addWidget(lbl_c, 1)
        else:
            row.addStretch(1)
        lbl_r = QLabel(right)
        lbl_r.setObjectName("scaleLabel")
        lbl_r.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(lbl_r)
        return row

    def _make_pd_off_scale_row(self, right: str) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        lbl_l = QLabel(self._tr("label_off"))
        lbl_l.setObjectName("scaleLabel")
        self._pd_off_scale_labels.append(lbl_l)
        row.addWidget(lbl_l)
        row.addStretch(1)
        lbl_r = QLabel(right)
        lbl_r.setObjectName("scaleLabel")
        lbl_r.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(lbl_r)
        return row

    def _pd_resonance_display(self, val: int) -> str:
        return self._tr("label_off") if val == 0 else str(val)

    def _refresh_pd_resonance_value_labels(self) -> None:
        if not hasattr(self, "_pd_string_sld"):
            return
        self._pd_string_lbl.setText(self._pd_resonance_display(self._pd_string_sld.value()))
        self._pd_damper_lbl.setText(self._pd_resonance_display(self._pd_damper_sld.value()))
        self._pd_key_off_lbl.setText(self._pd_resonance_display(self._pd_key_off_sld.value()))

    def _make_scroll_tab(self, inner: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(inner)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        return scroll

    def _make_shift_stepper(
        self,
        default: int = 0,
        *,
        on_change: Callable[[int], None] | None = None,
    ) -> tuple[QWidget, QLabel]:
        """Devuelve (widget, value_label) para un control de octava -3..+3."""
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(4)
        btn_minus = QPushButton("-")
        btn_minus.setObjectName("stepperButton")
        btn_minus.setFixedWidth(36)
        val_lbl = QLabel(str(default))
        val_lbl.setObjectName("valueLabel")
        val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        val_lbl.setFixedWidth(32)
        btn_plus = QPushButton("+")
        btn_plus.setObjectName("stepperButton")
        btn_plus.setFixedWidth(36)

        def dec() -> None:
            v = int(val_lbl.text())
            if v > OCTAVE_SHIFT_MIN:
                v -= 1
                val_lbl.setText(str(v))
                if on_change is not None:
                    on_change(v)

        def inc() -> None:
            v = int(val_lbl.text())
            if v < OCTAVE_SHIFT_MAX:
                v += 1
                val_lbl.setText(str(v))
                if on_change is not None:
                    on_change(v)

        btn_minus.clicked.connect(dec)
        btn_plus.clicked.connect(inc)
        h.addWidget(btn_minus)
        h.addWidget(val_lbl)
        h.addWidget(btn_plus)
        return w, val_lbl

    # ── Connection panel ─────────────────────────────────────────────────────

    def _build_connection_panel(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet("QWidget { background-color: #111113; }")
        v = QVBoxLayout(panel)
        v.setContentsMargins(12, 10, 12, 10)
        v.setSpacing(6)

        port_row = QHBoxLayout()
        self._label_device = QLabel()
        self._port_combo = QComboBox()
        _configure_combo(self._port_combo)
        self._port_combo.setMinimumWidth(200)
        self._refresh_btn = QPushButton()
        self._refresh_btn.clicked.connect(self._refresh_ports)
        self._connect_btn = QPushButton()
        self._connect_btn.clicked.connect(self._toggle_connect)
        port_row.addWidget(self._label_device)
        port_row.addWidget(self._port_combo, stretch=1)
        port_row.addWidget(self._refresh_btn)
        port_row.addWidget(self._connect_btn)
        help_stack = QWidget()
        help_stack_l = QVBoxLayout(help_stack)
        help_stack_l.setContentsMargins(0, 0, 0, 0)
        help_stack_l.setSpacing(4)
        self._connect_help_btn = QPushButton()
        self._connect_help_btn.setMinimumWidth(140)
        self._connect_help_btn.clicked.connect(self._on_connect_help_clicked)
        help_stack_l.addWidget(self._connect_help_btn)
        self._read_piano_values_btn = QPushButton()
        self._read_piano_values_btn.setMinimumWidth(140)
        self._read_piano_values_btn.clicked.connect(self._on_read_piano_values_clicked)
        help_stack_l.addWidget(self._read_piano_values_btn)
        port_row.addWidget(help_stack)
        v.addLayout(port_row)

        lang_row = QHBoxLayout()
        self._lang_lbl = QLabel()
        self._lang_combo = QComboBox()
        _configure_combo(self._lang_combo)
        self._lang_combo.setMinimumWidth(120)
        self._lang_combo.addItem("English", "en")
        self._lang_combo.addItem("Español", "es")
        self._lang_combo.blockSignals(True)
        self._lang_combo.setCurrentIndex(0 if self._lang == "en" else 1)
        self._lang_combo.blockSignals(False)
        self._lang_combo.currentIndexChanged.connect(self._on_language_changed)
        lang_row.addWidget(self._lang_lbl)
        lang_row.addWidget(self._lang_combo)
        lang_row.addStretch(1)
        v.addLayout(lang_row)

        v.addWidget(self._make_separator())
        return panel

    # ── Piano Settings tab ───────────────────────────────────────────────────

    def _build_piano_settings_tab(self) -> QScrollArea:
        inner = QWidget()
        v = QVBoxLayout(inner)
        v.setContentsMargins(12, 8, 12, 12)
        v.setSpacing(0)

        v.addWidget(self._build_master_vol_section())
        v.addWidget(self._build_key_touch_section())
        v.addWidget(self._build_master_tuning_section())
        v.addWidget(self._build_brilliance_section())
        v.addWidget(self._build_transpose_section())
        v.addWidget(self._build_ambience_section())
        v.addStretch(1)
        return self._make_scroll_tab(inner)

    def _build_master_vol_section(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 10, 0, 3)
        v.setSpacing(6)

        header = QHBoxLayout()
        self._label_master_vol = QLabel()
        self._master_lbl = QLabel(str(DEFAULT_MASTER_VOLUME))
        self._master_lbl.setObjectName("valueLabel")
        self._master_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        header.addWidget(self._label_master_vol)
        header.addWidget(self._master_lbl)
        v.addLayout(header)

        self._master_sld = QSlider(Qt.Orientation.Horizontal)
        self._master_sld.setRange(0, midix.MASTER_VOLUME_DT1_MAX)
        self._master_sld.setValue(DEFAULT_MASTER_VOLUME)
        self._master_sld.setTracking(True)
        self._master_sld.valueChanged.connect(lambda val: self._master_lbl.setText(str(val)))
        self._master_sld.valueChanged.connect(self._schedule_master_volume_debounced)
        self._master_sld.sliderReleased.connect(self._on_master_volume_slider_released)
        v.addWidget(self._master_sld)
        v.addLayout(self._make_scale_row("0", None, str(midix.MASTER_VOLUME_DT1_MAX)))
        v.addSpacing(8)
        v.addWidget(self._make_separator())
        return w

    def _build_key_touch_section(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 10, 0, 3)
        v.setSpacing(6)

        row = QHBoxLayout()
        self._label_key_touch = QLabel()
        self._key_touch_combo = QComboBox()
        _configure_combo(self._key_touch_combo)
        self._key_touch_combo.setMinimumWidth(120)
        for _ in range(4):
            self._key_touch_combo.addItem("")
        self._key_touch_combo.setCurrentIndex(DEFAULT_KEY_TOUCH)
        self._key_touch_combo.currentIndexChanged.connect(self._on_key_touch_changed)
        row.addWidget(self._label_key_touch)
        row.addSpacing(8)
        row.addWidget(self._key_touch_combo)
        row.addStretch(1)
        v.addLayout(row)
        v.addSpacing(8)
        v.addWidget(self._make_separator())
        return w

    def _build_master_tuning_section(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 10, 0, 3)
        v.setSpacing(6)

        header = QHBoxLayout()
        self._label_master_tuning = QLabel()
        self._master_tuning_hz_lbl = QLabel("440.0 Hz")
        self._master_tuning_hz_lbl.setObjectName("valueLabel")
        self._master_tuning_hz_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        header.addWidget(self._label_master_tuning)
        header.addWidget(self._master_tuning_hz_lbl)
        v.addLayout(header)

        self._master_tuning_sld = QSlider(Qt.Orientation.Horizontal)
        self._master_tuning_sld.setRange(midix.MASTER_TUNING_MIN_RAW, midix.MASTER_TUNING_MAX_RAW)
        self._master_tuning_sld.setValue(DEFAULT_MASTER_TUNING_RAW)
        self._master_tuning_sld.setTracking(True)
        self._master_tuning_sld.valueChanged.connect(self._on_master_tuning_changed)
        self._master_tuning_sld.sliderReleased.connect(self._send_master_tuning)
        v.addWidget(self._master_tuning_sld)
        v.addLayout(
            self._make_scale_row(
                f"{midix.MASTER_TUNING_MIN_HZ:.1f} Hz",
                "440 Hz",
                f"{midix.MASTER_TUNING_MAX_HZ:.1f} Hz",
            )
        )
        v.addSpacing(8)
        v.addWidget(self._make_separator())
        return w

    def _build_brilliance_section(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 10, 0, 3)
        v.setSpacing(6)

        header = QHBoxLayout()
        self._label_brilliance = QLabel()
        self._brilliance_lbl = QLabel("0")
        self._brilliance_lbl.setObjectName("valueLabel")
        self._brilliance_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        header.addWidget(self._label_brilliance)
        header.addWidget(self._brilliance_lbl)
        v.addLayout(header)

        self._brilliance_sld = QSlider(Qt.Orientation.Horizontal)
        self._brilliance_sld.setRange(-1, 1)
        self._brilliance_sld.setValue(DEFAULT_BRILLIANCE)
        self._brilliance_sld.setTracking(True)
        self._brilliance_sld.valueChanged.connect(self._on_brilliance_changed)
        v.addWidget(self._brilliance_sld)
        v.addLayout(self._make_scale_row("-1", "0", "+1"))
        v.addSpacing(8)
        v.addWidget(self._make_separator())
        return w

    def _build_transpose_section(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 10, 0, 3)
        v.setSpacing(6)

        saved = int(self._settings.value("transpose/value", DEFAULT_TRANSPOSE))
        header = QHBoxLayout()
        self._label_transpose = QLabel()
        self._transpose_lbl = QLabel(f"{saved:+d}" if saved != 0 else "0")
        self._transpose_lbl.setObjectName("valueLabel")
        self._transpose_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        header.addWidget(self._label_transpose)
        header.addWidget(self._transpose_lbl)
        v.addLayout(header)

        self._transpose_sld = QSlider(Qt.Orientation.Horizontal)
        self._transpose_sld.setRange(-24, 24)
        self._transpose_sld.setValue(saved)
        self._transpose_known = True
        self._transpose_sld.setTracking(True)
        self._transpose_sld.valueChanged.connect(
            lambda val: self._sync_transpose_label(val if self._transpose_known else None)
        )
        self._transpose_sld.valueChanged.connect(self._on_transpose_changed)
        v.addWidget(self._transpose_sld)
        v.addLayout(self._make_scale_row("-24", "0", "+24"))
        v.addSpacing(8)
        v.addWidget(self._make_separator())
        return w

    def _build_ambience_section(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 10, 0, 3)
        v.setSpacing(6)

        header = QHBoxLayout()
        self._label_ambience = QLabel()
        self._ambience_lbl = QLabel(str(DEFAULT_AMBIENCE))
        self._ambience_lbl.setObjectName("valueLabel")
        self._ambience_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        header.addWidget(self._label_ambience)
        header.addWidget(self._ambience_lbl)
        v.addLayout(header)

        self._ambience_sld = QSlider(Qt.Orientation.Horizontal)
        self._ambience_sld.setRange(0, 10)
        self._ambience_sld.setValue(DEFAULT_AMBIENCE)
        self._ambience_sld.setTracking(True)
        self._ambience_sld.valueChanged.connect(self._on_ambience_changed)
        v.addWidget(self._ambience_sld)
        v.addLayout(self._make_scale_row("0", "5", "10"))
        v.addSpacing(8)
        v.addWidget(self._make_separator())
        return w

    # ── Tones tab ────────────────────────────────────────────────────────────

    def _build_tones_tab(self) -> QScrollArea:
        inner = QWidget()
        v = QVBoxLayout(inner)
        v.setContentsMargins(12, 10, 12, 12)
        v.setSpacing(8)

        self._tones_seg = SegmentedBar(
            [
                self._tr("tone_mode_single"),
                self._tr("tone_mode_split"),
                self._tr("tone_mode_dual"),
                self._tr("tone_mode_twin"),
            ]
        )
        v.addWidget(self._tones_seg)

        self._tones_stack = QStackedWidget()
        self._tones_stack.addWidget(self._build_single_panel())
        self._tones_stack.addWidget(self._build_split_panel())
        self._tones_stack.addWidget(self._build_dual_panel())
        self._tones_stack.addWidget(self._build_twin_panel())
        self._tones_seg.connect_changed(self._on_keyboard_mode_changed)
        v.addWidget(self._tones_stack, stretch=1)

        return self._make_scroll_tab(inner)

    def _build_single_panel(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 8, 0, 0)
        v.setSpacing(8)

        self._single_picker = TonePicker(
            "", category_label=lambda c: self._tone_category_label(c)
        )
        self._single_picker.set_tone_changed_callback(self._on_single_tone_changed)
        v.addWidget(self._single_picker)
        v.addWidget(self._make_separator())
        v.addStretch(1)
        return w

    def _build_split_panel(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 8, 0, 0)
        v.setSpacing(8)

        self._split_left_picker = TonePicker(
            "", category_label=lambda c: self._tone_category_label(c)
        )
        self._split_left_picker.set_tone_changed_callback(self._on_split_left_tone_changed)
        v.addWidget(self._split_left_picker)
        v.addWidget(self._make_separator())

        self._split_right_picker = TonePicker(
            "", category_label=lambda c: self._tone_category_label(c)
        )
        self._split_right_picker.set_tone_changed_callback(self._on_split_right_tone_changed)
        v.addWidget(self._split_right_picker)
        v.addWidget(self._make_separator())

        # Balance
        bal_row = QHBoxLayout()
        self._label_split_balance = QLabel()
        self._split_balance_lbl = QLabel("9:9")
        self._split_balance_lbl.setObjectName("valueLabel")
        bal_row.addWidget(self._label_split_balance)
        bal_row.addWidget(self._split_balance_lbl)
        v.addLayout(bal_row)
        self._split_balance_sld = QSlider(Qt.Orientation.Horizontal)
        self._split_balance_sld.setRange(0, 18)
        self._split_balance_sld.setValue(DEFAULT_BALANCE)
        self._split_balance_sld.valueChanged.connect(self._on_split_balance_changed)
        v.addWidget(self._split_balance_sld)
        v.addWidget(self._make_separator())

        # Split Point
        sp_row = QHBoxLayout()
        self._label_split_point = QLabel()
        self._split_point_lbl = QLabel()
        self._split_point_lbl.setObjectName("valueLabel")
        self._split_point_val = DEFAULT_SPLIT_POINT
        sp_row.addWidget(self._label_split_point)
        sp_row.addStretch(1)
        sp_btn_m = QPushButton("-")
        sp_btn_m.setObjectName("stepperButton")
        sp_btn_m.setFixedWidth(36)
        sp_btn_m.clicked.connect(self._dec_split_point)
        sp_btn_p = QPushButton("+")
        sp_btn_p.setObjectName("stepperButton")
        sp_btn_p.setFixedWidth(36)
        sp_btn_p.clicked.connect(self._inc_split_point)
        sp_row.addWidget(sp_btn_m)
        sp_row.addWidget(self._split_point_lbl)
        sp_row.addWidget(sp_btn_p)
        v.addLayout(sp_row)
        v.addWidget(self._make_separator())

        # Right / Left shift
        rsh_row = QHBoxLayout()
        self._label_split_right_shift = QLabel()
        self._split_right_shift_w, self._split_right_shift_lbl = self._make_shift_stepper(
            on_change=self._send_split_right_octave_shift
        )
        rsh_row.addWidget(self._label_split_right_shift)
        rsh_row.addStretch(1)
        rsh_row.addWidget(self._split_right_shift_w)
        v.addLayout(rsh_row)
        v.addWidget(self._make_separator())

        lsh_row = QHBoxLayout()
        self._label_split_left_shift = QLabel()
        self._split_left_shift_w, self._split_left_shift_lbl = self._make_shift_stepper(
            on_change=self._send_split_left_octave_shift
        )
        lsh_row.addWidget(self._label_split_left_shift)
        lsh_row.addStretch(1)
        lsh_row.addWidget(self._split_left_shift_w)
        v.addLayout(lsh_row)
        v.addWidget(self._make_separator())

        v.addStretch(1)
        return w

    def _build_dual_panel(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 8, 0, 0)
        v.setSpacing(8)

        self._dual_picker1 = TonePicker(
            "", category_label=lambda c: self._tone_category_label(c)
        )
        self._dual_picker1.set_tone_changed_callback(self._on_dual_tone1_changed)
        v.addWidget(self._dual_picker1)
        v.addWidget(self._make_separator())

        self._dual_picker2 = TonePicker(
            "", category_label=lambda c: self._tone_category_label(c)
        )
        self._dual_picker2.set_tone_changed_callback(self._on_dual_tone2_changed)
        v.addWidget(self._dual_picker2)
        v.addWidget(self._make_separator())

        # Balance
        bal_row = QHBoxLayout()
        self._label_dual_balance = QLabel()
        self._dual_balance_lbl = QLabel("9:9")
        self._dual_balance_lbl.setObjectName("valueLabel")
        bal_row.addWidget(self._label_dual_balance)
        bal_row.addWidget(self._dual_balance_lbl)
        v.addLayout(bal_row)
        self._dual_balance_sld = QSlider(Qt.Orientation.Horizontal)
        self._dual_balance_sld.setRange(midix.DUAL_BALANCE_PANEL_MIN, midix.DUAL_BALANCE_PANEL_MAX)
        self._dual_balance_sld.setValue(DEFAULT_BALANCE)
        self._dual_balance_sld.valueChanged.connect(self._on_dual_balance_changed)
        v.addWidget(self._dual_balance_sld)
        v.addWidget(self._make_separator())

        # Tone 1 shift
        sh1_row = QHBoxLayout()
        self._label_dual_shift1 = QLabel()
        self._dual_shift1_w, self._dual_shift1_lbl = self._make_shift_stepper(
            on_change=self._send_dual_tone1_octave_shift
        )
        sh1_row.addWidget(self._label_dual_shift1)
        sh1_row.addStretch(1)
        sh1_row.addWidget(self._dual_shift1_w)
        v.addLayout(sh1_row)
        v.addWidget(self._make_separator())

        # Tone 2 shift
        sh2_row = QHBoxLayout()
        self._label_dual_shift2 = QLabel()
        self._dual_shift2_w, self._dual_shift2_lbl = self._make_shift_stepper(
            on_change=self._send_dual_tone2_octave_shift
        )
        sh2_row.addWidget(self._label_dual_shift2)
        sh2_row.addStretch(1)
        sh2_row.addWidget(self._dual_shift2_w)
        v.addLayout(sh2_row)
        v.addWidget(self._make_separator())

        v.addStretch(1)
        return w

    def _build_twin_panel(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 8, 0, 0)
        v.setSpacing(8)

        self._twin_picker = TonePicker(
            "", category_label=lambda c: self._tone_category_label(c)
        )
        self._twin_picker.set_tone_changed_callback(self._on_twin_tone_changed)
        v.addWidget(self._twin_picker)
        v.addWidget(self._make_separator())

        # Twin mode Pair / Individual
        mode_row = QHBoxLayout()
        self._label_twin_mode = QLabel()
        self._twin_mode_seg = SegmentedBar(
            [self._tr("twin_mode_pair"), self._tr("twin_mode_individual")]
        )
        self._twin_mode_seg.connect_changed(self._on_twin_mode_changed)
        mode_row.addWidget(self._label_twin_mode)
        mode_row.addStretch(1)
        mode_row.addWidget(self._twin_mode_seg)
        v.addLayout(mode_row)
        v.addWidget(self._make_separator())

        v.addStretch(1)
        return w

    # ── Metronome tab ────────────────────────────────────────────────────────

    def _build_metronome_tab(self) -> QScrollArea:
        inner = QWidget()
        v = QVBoxLayout(inner)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(10)

        # Start/Stop button
        self._metronome_btn = QPushButton()
        self._metronome_btn.setMinimumHeight(38)
        font = QFont()
        font.setPointSize(13)
        font.setBold(True)
        self._metronome_btn.setFont(font)
        self._metronome_btn.clicked.connect(self._send_metronome_probe)
        v.addWidget(self._metronome_btn)

        # BPM display
        bpm_header = QHBoxLayout()
        self._label_tempo = QLabel()
        self._tempo_val = QLabel(str(DEFAULT_TEMPO))
        self._tempo_val.setObjectName("valueLabel")
        self._tempo_val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        bpm_header.addWidget(self._label_tempo)
        bpm_header.addWidget(self._tempo_val)
        v.addLayout(bpm_header)

        self._tempo_sld = QSlider(Qt.Orientation.Horizontal)
        self._tempo_sld.setRange(TEMPO_MIN, TEMPO_MAX)
        self._tempo_sld.setValue(DEFAULT_TEMPO)
        self._tempo_sld.setTracking(True)
        self._tempo_sld.valueChanged.connect(lambda val: self._tempo_val.setText(str(val)))
        self._tempo_sld.valueChanged.connect(self._on_tempo_changed)
        self._tempo_sld.sliderReleased.connect(self._flush_tempo)
        v.addWidget(self._tempo_sld)
        v.addLayout(self._make_scale_row(str(TEMPO_MIN), "120", str(TEMPO_MAX)))
        v.addWidget(self._make_separator())

        # Volume
        vol_header = QHBoxLayout()
        self._label_metro_vol = QLabel()
        self._metro_vol_lbl = QLabel(str(DEFAULT_METRO_VOLUME))
        self._metro_vol_lbl.setObjectName("valueLabel")
        self._metro_vol_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        vol_header.addWidget(self._label_metro_vol)
        vol_header.addWidget(self._metro_vol_lbl)
        v.addLayout(vol_header)

        self._metro_vol_sld = QSlider(Qt.Orientation.Horizontal)
        self._metro_vol_sld.setRange(0, 10)
        self._metro_vol_sld.setValue(DEFAULT_METRO_VOLUME)
        self._metro_vol_sld.setTracking(True)
        self._metro_vol_sld.valueChanged.connect(lambda val: self._metro_vol_lbl.setText(str(val)))
        self._metro_vol_sld.valueChanged.connect(self._on_metro_volume_changed)
        v.addWidget(self._metro_vol_sld)
        v.addLayout(self._make_scale_row("0", None, "10"))
        v.addWidget(self._make_separator())

        # Tone (Click / Electronic / Japanese / English)
        tone_lbl = QLabel(self._tr("label_metro_tone"))
        v.addWidget(tone_lbl)
        self._metro_tone_seg = SegmentedBar(
            [
                self._tr("metro_tone_click"),
                self._tr("metro_tone_electronic"),
                self._tr("metro_tone_japanese"),
                self._tr("metro_tone_english"),
            ]
        )
        self._metro_tone_seg.connect_changed(self._on_metro_tone_changed)
        v.addWidget(self._metro_tone_seg)
        v.addWidget(self._make_separator())

        # Pattern (01 00 02 20, valores 0–7; 0 = Off en la app Roland)
        self._label_metro_pattern = QLabel(self._tr("label_metro_pattern"))
        v.addWidget(self._label_metro_pattern)
        pattern_widget = QWidget()
        pattern_grid = QGridLayout(pattern_widget)
        pattern_grid.setContentsMargins(0, 0, 0, 0)
        pattern_grid.setHorizontalSpacing(8)
        pattern_grid.setVerticalSpacing(8)
        self._pattern_btn_group = QButtonGroup(self)
        self._pattern_btn_group.setExclusive(True)
        self._pattern_btns: list[QPushButton] = []
        for pat in range(8):
            glyph = _METRO_PATTERN_GLYPHS[pat]
            btn = QPushButton(
                self._tr("metro_pattern_0") if glyph is None else glyph,
            )
            btn.setToolTip(self._tr(f"metro_pattern_{pat}"))
            btn.setCheckable(True)
            btn.setChecked(pat == DEFAULT_METRO_PATTERN)
            btn.setMinimumHeight(34)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setStyleSheet(self._beat_btn_style(pat == DEFAULT_METRO_PATTERN, glyph=True))
            btn.toggled.connect(
                lambda checked, b=btn, p=pat: (
                    b.setStyleSheet(self._beat_btn_style(checked, glyph=True)),
                    self._on_metro_pattern_changed(p) if checked else None,
                ),
            )
            self._pattern_btn_group.addButton(btn, pat)
            self._pattern_btns.append(btn)
            row, col = divmod(pat, METRO_GRID_COLS)
            pattern_grid.addWidget(btn, row, col)
        for c in range(METRO_GRID_COLS):
            pattern_grid.setColumnStretch(c, 1)
        v.addWidget(pattern_widget)
        v.addWidget(self._make_separator())

        # Beat / time signature (todos los compases del FP-30X, rejilla para no cortar)
        beat_lbl = QLabel(self._tr("label_metro_beat"))
        v.addWidget(beat_lbl)
        beat_widget = QWidget()
        beat_grid = QGridLayout(beat_widget)
        beat_grid.setContentsMargins(0, 0, 0, 0)
        beat_grid.setHorizontalSpacing(8)
        beat_grid.setVerticalSpacing(8)
        self._beat_btn_group = QButtonGroup(self)
        self._beat_btn_group.setExclusive(True)
        self._beat_midi_values: list[int] = []
        for idx, (midi_val, beat_num) in enumerate(BEAT_TABLE):
            btn = QPushButton(_beat_sig_unicode(beat_num))
            btn.setToolTip(f"{beat_num}/4")
            btn.setCheckable(True)
            btn.setChecked(midi_val == DEFAULT_METRO_BEAT)
            btn.setMinimumHeight(34)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setStyleSheet(self._beat_btn_style(midi_val == DEFAULT_METRO_BEAT, glyph=True))
            btn.toggled.connect(
                lambda checked, b=btn, mv=midi_val: (
                    b.setStyleSheet(self._beat_btn_style(checked, glyph=True)),
                    self._on_metro_beat_changed(mv) if checked else None,
                ),
            )
            self._beat_btn_group.addButton(btn, len(self._beat_midi_values))
            self._beat_midi_values.append(midi_val)
            row, col = divmod(idx, METRO_GRID_COLS)
            beat_grid.addWidget(btn, row, col)
        for c in range(METRO_GRID_COLS):
            beat_grid.setColumnStretch(c, 1)
        v.addWidget(beat_widget)
        v.addWidget(self._make_separator())

        v.addStretch(1)
        return self._make_scroll_tab(inner)

    @staticmethod
    def _beat_btn_style(active: bool, *, glyph: bool = False) -> str:
        fs = "14px" if glyph else "11px"
        if active:
            return (
                "QPushButton { background-color: #E07828; color: #ffffff; "
                f"border: none; border-radius: 14px; font-size: {fs}; }}"
            )
        return (
            "QPushButton { background-color: #2c2c2e; color: #c8c8c8; "
            f"border: none; border-radius: 14px; font-size: {fs}; }}"
            "QPushButton:hover { color: #ffffff; }"
        )

    # ── Piano Designer tab ───────────────────────────────────────────────────

    _TEMPERAMENT_KEYS_EN = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
    _TEMPERAMENT_KEYS_ES = ["Do", "Do#", "Re", "Mib", "Mi", "Fa", "Fa#", "Sol", "Lab", "La", "Sib", "Si"]

    def _build_piano_designer_tab(self) -> QScrollArea:
        inner = QWidget()
        v = QVBoxLayout(inner)
        v.setContentsMargins(12, 8, 12, 12)
        v.setSpacing(0)
        self._pd_off_scale_labels = []
        self._tab_widget.tabBarClicked.connect(self._on_tab_clicked)

        def _section_header(text: str) -> QLabel:
            lbl = QLabel(text)
            lbl.setStyleSheet("color: #E07828; font-size: 12px; font-weight: bold;")
            lbl.setContentsMargins(0, 10, 0, 2)
            return lbl

        # ── Cabinet ──
        v.addWidget(_section_header(self._tr("pd_section_cabinet")))
        v.addWidget(self._make_separator())

        lid_hdr = QHBoxLayout()
        self._pd_label_lid = QLabel()
        self._pd_lid_lbl = QLabel("4")
        self._pd_lid_lbl.setObjectName("valueLabel")
        self._pd_lid_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lid_hdr.addWidget(self._pd_label_lid)
        lid_hdr.addWidget(self._pd_lid_lbl)
        v.addLayout(lid_hdr)
        self._pd_lid_sld = QSlider(Qt.Orientation.Horizontal)
        self._pd_lid_sld.setRange(0, 6)
        self._pd_lid_sld.setValue(4)
        self._pd_lid_sld.valueChanged.connect(
            lambda val: (self._pd_lid_lbl.setText(str(val)), self._pd_send_lid(val))
        )
        v.addWidget(self._pd_lid_sld)
        v.addLayout(self._make_scale_row("0", None, "6"))
        v.addSpacing(8)

        # ── Strings ──
        v.addWidget(_section_header(self._tr("pd_section_strings")))
        v.addWidget(self._make_separator())

        str_hdr = QHBoxLayout()
        self._pd_label_string_res = QLabel()
        self._pd_string_lbl = QLabel("5")
        self._pd_string_lbl.setObjectName("valueLabel")
        self._pd_string_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        str_hdr.addWidget(self._pd_label_string_res)
        str_hdr.addWidget(self._pd_string_lbl)
        v.addLayout(str_hdr)
        self._pd_string_sld = QSlider(Qt.Orientation.Horizontal)
        self._pd_string_sld.setRange(0, 10)
        self._pd_string_sld.setValue(5)
        self._pd_string_sld.valueChanged.connect(
            lambda val: (
                self._pd_string_lbl.setText(self._pd_resonance_display(val)),
                self._pd_send_string_res(val),
            )
        )
        v.addWidget(self._pd_string_sld)
        v.addLayout(self._make_pd_off_scale_row("10"))
        v.addSpacing(8)

        # ── Damper ──
        v.addWidget(_section_header(self._tr("pd_section_damper")))
        v.addWidget(self._make_separator())

        dmp_hdr = QHBoxLayout()
        self._pd_label_damper_res = QLabel()
        self._pd_damper_lbl = QLabel("5")
        self._pd_damper_lbl.setObjectName("valueLabel")
        self._pd_damper_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        dmp_hdr.addWidget(self._pd_label_damper_res)
        dmp_hdr.addWidget(self._pd_damper_lbl)
        v.addLayout(dmp_hdr)
        self._pd_damper_sld = QSlider(Qt.Orientation.Horizontal)
        self._pd_damper_sld.setRange(0, 10)
        self._pd_damper_sld.setValue(5)
        self._pd_damper_sld.valueChanged.connect(
            lambda val: (
                self._pd_damper_lbl.setText(self._pd_resonance_display(val)),
                self._pd_send_damper_res(val),
            )
        )
        v.addWidget(self._pd_damper_sld)
        v.addLayout(self._make_pd_off_scale_row("10"))
        v.addSpacing(8)

        # ── Keyboard ──
        v.addWidget(_section_header(self._tr("pd_section_keyboard")))
        v.addWidget(self._make_separator())

        koff_hdr = QHBoxLayout()
        self._pd_label_key_off = QLabel()
        self._pd_key_off_lbl = QLabel("5")
        self._pd_key_off_lbl.setObjectName("valueLabel")
        self._pd_key_off_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        koff_hdr.addWidget(self._pd_label_key_off)
        koff_hdr.addWidget(self._pd_key_off_lbl)
        v.addLayout(koff_hdr)
        self._pd_key_off_sld = QSlider(Qt.Orientation.Horizontal)
        self._pd_key_off_sld.setRange(0, 10)
        self._pd_key_off_sld.setValue(5)
        self._pd_key_off_sld.valueChanged.connect(
            lambda val: (
                self._pd_key_off_lbl.setText(self._pd_resonance_display(val)),
                self._pd_send_key_off(val),
            )
        )
        v.addWidget(self._pd_key_off_sld)
        v.addLayout(self._make_pd_off_scale_row("10"))
        v.addSpacing(8)

        # ── Tuning ──
        v.addWidget(_section_header(self._tr("pd_section_tuning")))
        v.addWidget(self._make_separator())

        # Temperament
        temp_row = QHBoxLayout()
        self._pd_label_temperament = QLabel()
        self._pd_temp_combo = QComboBox()
        _configure_combo(self._pd_temp_combo)
        for key in self._TEMPERAMENT_I18N_KEYS:
            self._pd_temp_combo.addItem(self._tr(key))
        self._pd_temp_combo.currentIndexChanged.connect(self._pd_send_temperament)
        temp_row.addWidget(self._pd_label_temperament)
        temp_row.addSpacing(8)
        temp_row.addWidget(self._pd_temp_combo)
        temp_row.addStretch(1)
        v.addLayout(temp_row)
        v.addSpacing(8)
        v.addWidget(self._make_separator())

        # Temperament Key
        temp_key_row = QHBoxLayout()
        self._pd_label_temp_key = QLabel()
        self._pd_temp_key_combo = QComboBox()
        _configure_combo(self._pd_temp_key_combo)
        self._pd_temp_key_combo.currentIndexChanged.connect(self._pd_send_temperament_key)
        self._pd_populate_temp_key_combo()
        temp_key_row.addWidget(self._pd_label_temp_key)
        temp_key_row.addSpacing(8)
        temp_key_row.addWidget(self._pd_temp_key_combo)
        temp_key_row.addStretch(1)
        v.addLayout(temp_key_row)
        v.addSpacing(8)
        v.addWidget(self._make_separator())

        v.addSpacing(10)

        # Voicing por nota (antes de Guardar)
        self._inv_section_title = _section_header(self._tr("pd_section_note_voicing"))
        v.addWidget(self._inv_section_title)
        v.addWidget(self._make_separator())

        note_row = QHBoxLayout()
        self._inv_label_note = QLabel(self._tr("inv_label_note"))
        self._inv_note_combo = QComboBox()
        _configure_combo(self._inv_note_combo, max_visible=18)
        self._repopulate_inv_note_combo()
        self._inv_note_combo.currentIndexChanged.connect(self._on_inv_note_changed)
        note_row.addWidget(self._inv_label_note)
        note_row.addWidget(self._inv_note_combo, stretch=1)
        v.addLayout(note_row)

        tun_hdr = QHBoxLayout()
        self._inv_label_tuning = QLabel(self._tr("pd_label_single_note_tuning"))
        self._inv_tuning_val_lbl = QLabel("0.0")
        self._inv_tuning_val_lbl.setObjectName("valueLabel")
        self._inv_tuning_val_lbl.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        tun_hdr.addWidget(self._inv_label_tuning)
        tun_hdr.addWidget(self._inv_tuning_val_lbl)
        v.addLayout(tun_hdr)
        self._inv_tuning_sld = QSlider(Qt.Orientation.Horizontal)
        self._inv_tuning_sld.setRange(-500, 500)
        self._inv_tuning_sld.setValue(0)
        self._inv_tuning_sld.setTracking(True)
        self._inv_tuning_sld.valueChanged.connect(self._on_inv_tuning_slider_changed)
        self._inv_tuning_sld.sliderReleased.connect(self._flush_inv_tuning_immediate)
        v.addWidget(self._inv_tuning_sld)
        v.addLayout(self._make_scale_row("−50", "0", "+50"))

        v.addWidget(self._make_separator())

        ch_hdr = QHBoxLayout()
        self._inv_label_character = QLabel(self._tr("pd_label_single_note_character"))
        self._inv_char_val_lbl = QLabel("0")
        self._inv_char_val_lbl.setObjectName("valueLabel")
        self._inv_char_val_lbl.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        ch_hdr.addWidget(self._inv_label_character)
        ch_hdr.addWidget(self._inv_char_val_lbl)
        v.addLayout(ch_hdr)
        self._inv_char_sld = QSlider(Qt.Orientation.Horizontal)
        self._inv_char_sld.setRange(-5, 5)
        self._inv_char_sld.setValue(0)
        self._inv_char_sld.setTracking(True)
        self._inv_char_sld.valueChanged.connect(self._on_inv_character_changed)
        v.addWidget(self._inv_char_sld)
        v.addLayout(self._make_scale_row("−5", "0", "+5"))

        v.addSpacing(10)

        # Save to Piano button
        self._pd_save_btn = QPushButton()
        self._pd_save_btn.setMinimumHeight(34)
        self._pd_save_btn.setStyleSheet(
            "QPushButton { background-color: #E07828; color: #ffffff; "
            "border: none; border-radius: 8px; font-size: 13px; font-weight: bold; }"
            "QPushButton:hover { background-color: #f09040; }"
            "QPushButton:pressed { background-color: #b05818; }"
        )
        self._pd_save_btn.clicked.connect(self._pd_save_to_piano)
        v.addWidget(self._pd_save_btn)

        v.addStretch(1)
        return self._make_scroll_tab(inner)

    def _repopulate_inv_note_combo(self) -> None:
        if not hasattr(self, "_inv_note_combo"):
            return
        cur = max(0, self._inv_note_combo.currentIndex())
        self._inv_note_combo.blockSignals(True)
        self._inv_note_combo.clear()
        for i in range(INV_NOTE_COUNT):
            midi_n = INV_NOTE_MIDI_BASE + i
            self._inv_note_combo.addItem(midi_note_name(midi_n, self._lang))
        self._inv_note_combo.setCurrentIndex(min(cur, INV_NOTE_COUNT - 1))
        self._inv_note_combo.blockSignals(False)

    def _update_inv_tuning_value_label(self) -> None:
        v10 = self._inv_tuning_sld.value()
        self._inv_tuning_val_lbl.setText(f"{v10 / 10.0:+.1f}")

    def _on_inv_note_changed(self, _idx: int) -> None:
        if self._suppress_slider_midi:
            return
        self._inv_tuning_debounce_timer.stop()
        self._inv_tuning_sld.blockSignals(True)
        self._inv_tuning_sld.setValue(0)
        self._inv_tuning_sld.blockSignals(False)
        self._update_inv_tuning_value_label()
        self._inv_char_sld.blockSignals(True)
        self._inv_char_sld.setValue(0)
        self._inv_char_sld.blockSignals(False)
        self._inv_char_val_lbl.setText("0")

    def _on_inv_tuning_slider_changed(self, _value: int) -> None:
        if self._suppress_slider_midi:
            return
        self._update_inv_tuning_value_label()
        self._inv_tuning_debounce_timer.stop()
        self._inv_tuning_debounce_timer.start(INV_TUNING_DEBOUNCE_MS)

    def _flush_inv_tuning_immediate(self) -> None:
        if self._suppress_slider_midi:
            return
        self._inv_tuning_debounce_timer.stop()
        self._flush_inv_tuning()

    def _flush_inv_tuning(self) -> None:
        if not self._midi.is_open or self._suppress_slider_midi:
            return
        note_i = self._inv_note_combo.currentIndex()
        if note_i < 0 or note_i >= INV_NOTE_COUNT:
            return
        cents_x10 = self._inv_tuning_sld.value()
        try:
            self._midi_user_send(
                midix.piano_designer_individual_note_tuning_set(note_i, cents_x10),
            )
        except OSError:
            self._disconnect_device(
                status_key="status_device_lost", name=self._last_output_port or "?"
            )
        except (ValueError, RuntimeError) as e:
            self._set_status(str(e))

    def _on_inv_character_changed(self, value: int) -> None:
        if self._suppress_slider_midi:
            return
        self._inv_char_val_lbl.setText(f"{value:+d}" if value != 0 else "0")
        if not self._midi.is_open:
            return
        note_i = self._inv_note_combo.currentIndex()
        if note_i < 0 or note_i >= INV_NOTE_COUNT:
            return
        try:
            self._midi_user_send(
                midix.piano_designer_individual_note_character_set(note_i, value),
            )
        except OSError:
            self._disconnect_device(
                status_key="status_device_lost", name=self._last_output_port or "?"
            )
        except (ValueError, RuntimeError) as e:
            self._set_status(str(e))

    def _pd_populate_temp_key_combo(self) -> None:
        keys = self._TEMPERAMENT_KEYS_ES if self._lang == "es" else self._TEMPERAMENT_KEYS_EN
        current = self._pd_temp_key_combo.currentIndex()
        self._pd_temp_key_combo.blockSignals(True)
        self._pd_temp_key_combo.clear()
        for k in keys:
            self._pd_temp_key_combo.addItem(k)
        self._pd_temp_key_combo.setCurrentIndex(max(0, current))
        self._pd_temp_key_combo.blockSignals(False)

    def _on_tab_clicked(self, index: int) -> None:
        if index != 3:
            return
        if self._pd_warning_shown:
            return
        # Show warning dialog
        from PySide6.QtWidgets import (
            QCheckBox,
            QDialog,
            QHBoxLayout,
            QLabel,
            QPushButton,
            QVBoxLayout,
        )
        dlg = QDialog(self)
        dlg.setWindowTitle(self._tr("pd_warning_title"))
        dlg.setModal(True)
        dlg.setMinimumWidth(380)
        dv = QVBoxLayout(dlg)
        dv.setSpacing(16)
        dv.setContentsMargins(20, 20, 20, 20)
        msg = QLabel(self._tr("pd_warning_text"))
        msg.setWordWrap(True)
        dv.addWidget(msg)
        dont_show = QCheckBox(self._tr("pd_warning_dont_show"))
        dv.addWidget(dont_show)
        btns = QHBoxLayout()
        btn_yes = QPushButton(self._tr("dlg_yes"))
        btn_yes.clicked.connect(dlg.accept)
        btn_no = QPushButton(self._tr("dlg_no"))
        btn_no.clicked.connect(dlg.reject)
        btns.addStretch(1)
        btns.addWidget(btn_no)
        btns.addWidget(btn_yes)
        dv.addLayout(btns)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            if dont_show.isChecked():
                self._pd_warning_shown = True
                self._settings.setValue("pd_warning_shown", True)
            # Switch to Single mode if needed
            if self._keyboard_mode != 0:
                self._tones_seg.set_index(0)
                self._on_keyboard_mode_changed(0)
        else:
            # Switch back to previous tab
            self._tab_widget.setCurrentIndex(0)

    def _pd_send_lid(self, val: int) -> None:
        if not self._midi.is_open:
            return
        try:
            self._midi_user_send(midix.piano_designer_lid_set(val))
        except OSError:
            self._disconnect_device(status_key="status_device_lost", name=self._last_output_port or "?")

    def _pd_send_string_res(self, val: int) -> None:
        if not self._midi.is_open:
            return
        try:
            self._midi_user_send(midix.piano_designer_string_resonance_set(val))
        except OSError:
            self._disconnect_device(status_key="status_device_lost", name=self._last_output_port or "?")

    def _pd_send_damper_res(self, val: int) -> None:
        if not self._midi.is_open:
            return
        try:
            self._midi_user_send(midix.piano_designer_damper_resonance_set(val))
        except OSError:
            self._disconnect_device(status_key="status_device_lost", name=self._last_output_port or "?")

    def _pd_send_key_off(self, val: int) -> None:
        if not self._midi.is_open:
            return
        try:
            self._midi_user_send(midix.piano_designer_key_off_resonance_set(val))
        except OSError:
            self._disconnect_device(status_key="status_device_lost", name=self._last_output_port or "?")

    def _pd_send_temperament(self, idx: int) -> None:
        if not self._midi.is_open:
            return
        try:
            self._midi_user_send(midix.piano_designer_temperament_set(idx))
        except OSError:
            self._disconnect_device(status_key="status_device_lost", name=self._last_output_port or "?")

    def _pd_send_temperament_key(self, idx: int) -> None:
        if not self._midi.is_open:
            return
        try:
            self._midi_user_send(midix.piano_designer_temperament_key_set(idx))
        except OSError:
            self._disconnect_device(status_key="status_device_lost", name=self._last_output_port or "?")

    def _pd_save_to_piano(self) -> None:
        if not self._midi.is_open:
            self._set_status(self._tr("msg_connect_before_send"))
            return
        try:
            self._midi_user_send(midix.piano_designer_write())
            self._set_status(self._tr("status_pd_saved"))
        except OSError:
            self._disconnect_device(status_key="status_device_lost", name=self._last_output_port or "?")

    # ── App lifecycle ────────────────────────────────────────────────────────

    def closeEvent(self, event: QCloseEvent) -> None:
        self._port_watchdog_timer.stop()
        self._cancel_debounce_timers()
        self._stop_midi_in_worker()
        self._midi.close()
        super().closeEvent(event)

    def _stop_midi_in_worker(self) -> None:
        worker = self._midi_in_worker
        if worker is None:
            return
        try:
            worker.message_received.disconnect(self._on_midi_in_message)
        except (RuntimeError, TypeError):
            pass
        try:
            worker.port_lost.disconnect(self._on_midi_in_port_lost)
        except (RuntimeError, TypeError):
            pass
        worker.stop_safely()
        worker.wait(2000)
        self._midi_in_worker = None

    def _mark_app_bank_tx(self) -> None:
        self._ignore_piano_patch_until = time.monotonic() + PIANO_PATCH_IGNORE_S

    def _sync_transpose_label(self, value: int | None) -> None:
        if value is None:
            self._transpose_lbl.setText("--")
        elif value == 0:
            self._transpose_lbl.setText("0")
        else:
            self._transpose_lbl.setText(f"{value:+d}")

    def _set_transpose_ui(self, value: int, *, known: bool, emit_status: bool = False) -> None:
        self._transpose_known = known
        self._transpose_sld.blockSignals(True)
        self._transpose_sld.setValue(value)
        self._transpose_sld.blockSignals(False)
        self._sync_transpose_label(value if known else None)
        if known:
            self._settings.setValue("transpose/value", value)
        if emit_status:
            if known:
                self._set_status(self._tr("status_transpose_from_piano", value=value))
            else:
                self._set_status(self._tr("status_transpose_unknown"))

    def _disconnect_device(self, *, status_key: str, name: str | None = None) -> None:
        self._piano_poll_timer.stop()
        self._tone_refresh_after_mode_timer.stop()
        self._piano_values_read_timer.stop()
        self._piano_values_read_active = False
        self._piano_values_read_pending.clear()
        self._cancel_debounce_timers()
        self._stop_midi_in_worker()
        try:
            self._midi.close()
        except OSError:
            # close() ya deja el cliente en estado cerrado; seguimos para refrescar la UI.
            pass
        self._last_output_port = None
        self._last_input_port = None
        self._metronome_on = None
        self._update_metronome_btn()
        self._update_connect_button_text()
        self._sync_connection_dependent_controls()
        if name is None:
            self._set_status(self._tr(status_key))
        else:
            self._set_status(self._tr(status_key, name=name))

    def _check_connected_ports(self) -> None:
        if not self._midi.is_open or not self._last_output_port:
            return
        outs = list_output_names()
        if self._last_output_port not in outs:
            self._refresh_ports()
            self._disconnect_device(status_key="status_device_lost", name=self._last_output_port)
            return
        if self._last_input_port and self._last_input_port not in list_input_names():
            lost_name = self._last_input_port
            self._stop_midi_in_worker()
            self._last_input_port = None
            self._set_status(self._tr("status_device_lost", name=lost_name))
            self._refresh_ports()
            self._sync_connection_dependent_controls()

    def _on_midi_in_port_lost(self, _error: str) -> None:
        if not self._last_input_port:
            return
        lost_name = self._last_input_port
        self._stop_midi_in_worker()
        self._last_input_port = None
        if self._last_output_port and self._midi.is_open:
            self._set_status(self._tr("status_device_lost", name=lost_name))
        self._sync_connection_dependent_controls()

    def _refresh_ports(self) -> None:
        current = self._port_combo.currentText()
        self._port_combo.clear()
        outs = list_output_names()
        self._port_combo.addItems(outs)
        if current in outs:
            self._port_combo.setCurrentText(current)
        ni = len(list_input_names())
        self._set_status(self._tr("status_midi_ports", no=len(outs), ni=ni))

    def _on_midi_in_message(self, msg: object) -> None:
        if not isinstance(msg, mido.Message):
            return
        if self._verbose:
            self._print_midi_trace("IN", msg)
        dt1 = parse_roland_dt1(msg)
        if self._piano_values_read_active and dt1 is not None:
            addr, data = dt1
            pending = self._piano_values_read_pending
            if addr in pending:
                pid = pending.pop(addr)
                self._print_piano_value_trace(pid, data)
                if not pending:
                    self._piano_values_read_finish_ok()
        if time.monotonic() < self._ignore_piano_patch_until:
            return
        if dt1 is not None:
            self._handle_dt1(*dt1)
            return
        transpose_sysex = parse_master_coarse_tuning_sysex(msg)
        if transpose_sysex is not None:
            if self._transpose_sld.value() != transpose_sysex or not self._transpose_known:
                self._set_transpose_ui(transpose_sysex, known=True, emit_status=True)
            return
        transpose = self._rpn_parser.feed_coarse_tuning(msg)
        if transpose is not None:
            if self._transpose_sld.value() != transpose or not self._transpose_known:
                self._set_transpose_ui(transpose, known=True, emit_status=True)
            return
        parsed = self._bank_parser.feed(msg)
        if parsed is None:
            return
        if not self._tone_uses_bank_program(self._active_primary_tone()):
            return
        msb, lsb, pdoc = parsed
        for t in TONE_PRESETS:
            if t.bank_msb == msb and t.bank_lsb == lsb and t.program_doc == pdoc:
                if self._single_picker.current_tone() != t:
                    self._single_picker.set_tone(t)
                if self._split_right_picker.current_tone() != t:
                    self._split_right_picker.set_tone(t)
                if self._dual_picker1.current_tone() != t:
                    self._dual_picker1.set_tone(t)
                if self._twin_picker.current_tone() != t:
                    self._twin_picker.set_tone(t)
                self._set_status(self._tr("status_tone_from_piano", name=t.name))
                return
        self._set_status(self._tr("status_piano_tone_unknown", msb=msb, lsb=lsb, pdoc=pdoc))

    def _toggle_connect(self) -> None:
        if self._midi.is_open:
            self._disconnect_device(status_key="status_disconnected")
            return
        name = self._port_combo.currentText().strip()
        if not name:
            QMessageBox.warning(self, self._tr("dlg_midi"), self._tr("err_no_port"))
            return
        try:
            self._midi.open(name)
        except OSError as e:
            QMessageBox.critical(self, self._tr("dlg_midi"), self._tr("err_open_port", error=str(e)))
            return
        self._last_output_port = name
        self._last_input_port = None
        self._transpose_known = False
        self._metronome_on = None
        self._sync_transpose_label(None)
        self._update_metronome_btn()
        self._update_connect_button_text()
        self._sync_connection_dependent_controls()
        try:
            self._midi.send(midix.app_connect_handshake())
        except (OSError, RuntimeError):
            pass
        input_names = list_input_names()
        in_name = name if name in input_names else ""
        if in_name:
            try:
                worker = MidiInWorker(in_name)
                worker.message_received.connect(self._on_midi_in_message)
                worker.port_lost.connect(self._on_midi_in_port_lost)
                self._midi_in_worker = worker
                worker.start()
                self._last_input_port = in_name
            except OSError as e:
                self._midi_in_worker = None
                QMessageBox.warning(self, self._tr("dlg_midi"), self._tr("warn_input_open", error=str(e)))
        if self._midi_in_worker is not None and self._last_input_port:
            self._set_status(self._tr("status_connected_sync", out=name, inn=self._last_input_port))
            self._request_piano_state()
            self._piano_poll_timer.start()
        else:
            self._set_status(self._tr("status_connected", name=name))
        # Tras abrir (o fallar) la entrada MIDI: _last_input_port se rellena después del primer sync.
        self._sync_connection_dependent_controls()
        if self._transpose_sld.value() != 0:
            self._send_transpose(update_status=False)

    def _set_status(self, text: str) -> None:
        self._status.setText(text)

    def _reset_defaults(self) -> None:
        self._cancel_debounce_timers()
        self._suppress_slider_midi = True
        try:
            self._master_sld.setValue(DEFAULT_MASTER_VOLUME)
            self._set_transpose_ui(DEFAULT_TRANSPOSE, known=True)
            self._set_tempo_ui(DEFAULT_TEMPO)

            self._master_tuning_sld.blockSignals(True)
            self._master_tuning_sld.setValue(DEFAULT_MASTER_TUNING_RAW)
            self._master_tuning_sld.blockSignals(False)
            self._master_tuning_hz_lbl.setText(f"{midix.MASTER_TUNING_REF_HZ:.1f} Hz")

            self._brilliance_sld.blockSignals(True)
            self._brilliance_sld.setValue(DEFAULT_BRILLIANCE)
            self._brilliance_sld.blockSignals(False)
            self._brilliance_lbl.setText("0")

            self._ambience_sld.blockSignals(True)
            self._ambience_sld.setValue(DEFAULT_AMBIENCE)
            self._ambience_sld.blockSignals(False)
            self._ambience_lbl.setText(str(DEFAULT_AMBIENCE))

            self._key_touch_combo.blockSignals(True)
            self._key_touch_combo.setCurrentIndex(DEFAULT_KEY_TOUCH)
            self._key_touch_combo.blockSignals(False)

            # Metronome
            self._metro_vol_sld.blockSignals(True)
            self._metro_vol_sld.setValue(DEFAULT_METRO_VOLUME)
            self._metro_vol_sld.blockSignals(False)
            self._metro_vol_lbl.setText(str(DEFAULT_METRO_VOLUME))
            self._metro_tone_seg.set_index(DEFAULT_METRO_TONE)
            for p, pbtn in enumerate(self._pattern_btns):
                pbtn.blockSignals(True)
                pbtn.setChecked(p == DEFAULT_METRO_PATTERN)
                pbtn.setStyleSheet(self._beat_btn_style(p == DEFAULT_METRO_PATTERN, glyph=True))
                pbtn.blockSignals(False)
            for i, mv in enumerate(self._beat_midi_values):
                btn = self._beat_btn_group.button(i)
                if btn:
                    btn.blockSignals(True)
                    btn.setChecked(mv == DEFAULT_METRO_BEAT)
                    btn.setStyleSheet(self._beat_btn_style(mv == DEFAULT_METRO_BEAT, glyph=True))
                    btn.blockSignals(False)

            # Tones — balance and split point
            self._split_balance_sld.blockSignals(True)
            self._split_balance_sld.setValue(DEFAULT_BALANCE)
            self._split_balance_sld.blockSignals(False)
            sb_l, sb_r = midix.split_balance_display_lr(DEFAULT_BALANCE)
            self._split_balance_lbl.setText(f"{sb_l}:{sb_r}")
            self._dual_balance_sld.blockSignals(True)
            self._dual_balance_sld.setValue(DEFAULT_BALANCE)
            self._dual_balance_sld.blockSignals(False)
            db_l, db_r = midix.dual_balance_display_lr(DEFAULT_BALANCE)
            self._dual_balance_lbl.setText(f"{db_l}:{db_r}")
            self._split_point_val = DEFAULT_SPLIT_POINT
            self._update_split_point_label()
            self._split_right_shift_lbl.setText("0")
            self._split_left_shift_lbl.setText("0")
            self._dual_shift1_lbl.setText("0")
            self._dual_shift2_lbl.setText("0")
            self._twin_mode_seg.set_index(DEFAULT_TWIN_MODE)

            # Piano Designer
            self._pd_lid_sld.blockSignals(True)
            self._pd_lid_sld.setValue(4)
            self._pd_lid_sld.blockSignals(False)
            self._pd_lid_lbl.setText("4")
            self._pd_string_sld.blockSignals(True)
            self._pd_string_sld.setValue(5)
            self._pd_string_sld.blockSignals(False)
            self._pd_string_lbl.setText("5")
            self._pd_damper_sld.blockSignals(True)
            self._pd_damper_sld.setValue(5)
            self._pd_damper_sld.blockSignals(False)
            self._pd_damper_lbl.setText("5")
            self._pd_key_off_sld.blockSignals(True)
            self._pd_key_off_sld.setValue(5)
            self._pd_key_off_sld.blockSignals(False)
            self._pd_key_off_lbl.setText("5")
            self._pd_temp_combo.blockSignals(True)
            self._pd_temp_combo.setCurrentIndex(0)
            self._pd_temp_combo.blockSignals(False)
            self._pd_temp_key_combo.blockSignals(True)
            self._pd_temp_key_combo.setCurrentIndex(0)
            self._pd_temp_key_combo.blockSignals(False)

            self._inv_note_combo.blockSignals(True)
            self._inv_note_combo.setCurrentIndex(0)
            self._inv_note_combo.blockSignals(False)
            self._inv_tuning_sld.blockSignals(True)
            self._inv_tuning_sld.setValue(0)
            self._inv_tuning_sld.blockSignals(False)
            self._update_inv_tuning_value_label()
            self._inv_char_sld.blockSignals(True)
            self._inv_char_sld.setValue(0)
            self._inv_char_sld.blockSignals(False)
            self._inv_char_val_lbl.setText("0")
        finally:
            self._suppress_slider_midi = False

        if not self._midi.is_open:
            self._set_status(self._tr("status_defaults_offline"))
            return
        self._send_master_volume()
        self._send_master_tuning()
        self._send_transpose(update_status=False)
        self._send_brilliance()
        self._send_ambience()
        self._send_key_touch()
        self._midi_user_send(midix.metronome_volume_set(DEFAULT_METRO_VOLUME))
        self._midi_user_send(midix.metronome_tone_set(DEFAULT_METRO_TONE))
        self._midi_user_send(midix.metronome_beat_set(DEFAULT_METRO_BEAT))
        self._midi_user_send(midix.metronome_pattern_set(DEFAULT_METRO_PATTERN))
        self._midi_user_send(midix.split_balance_set(DEFAULT_BALANCE))
        self._midi.send_all_spaced(
            midix.split_balance_control_changes(DEFAULT_BALANCE),
            gap_s=midix.DEFAULT_MESSAGE_GAP_S,
        )
        self._midi_user_send(midix.split_right_octave_shift_set(0))
        self._midi_user_send(midix.split_octave_shift_set(0))
        self._midi_user_send(midix.dual_balance_set(DEFAULT_BALANCE))
        self._midi.send_all_spaced(
            midix.dual_balance_control_changes(DEFAULT_BALANCE),
            gap_s=midix.DEFAULT_MESSAGE_GAP_S,
        )
        self._midi_user_send(midix.dual_tone1_octave_shift_set(0))
        self._midi_user_send(midix.dual_octave_shift_set(0))
        self._midi_user_send(midix.piano_designer_lid_set(4))
        self._midi_user_send(midix.piano_designer_string_resonance_set(5))
        self._midi_user_send(midix.piano_designer_damper_resonance_set(5))
        self._midi_user_send(midix.piano_designer_key_off_resonance_set(5))
        self._midi_user_send(midix.piano_designer_temperament_set(0))
        self._midi_user_send(midix.piano_designer_temperament_key_set(0))
        self._set_status(self._tr("status_defaults_sent"))

    def _cancel_debounce_timers(self) -> None:
        self._master_vol_debounce_timer.stop()
        self._tempo_debounce_timer.stop()
        self._tone_refresh_after_mode_timer.stop()
        self._inv_tuning_debounce_timer.stop()

    def _schedule_master_volume_debounced(self, _value: int = 0) -> None:
        if self._suppress_slider_midi:
            return
        self._master_vol_debounce_timer.stop()
        self._master_vol_debounce_timer.start(MASTER_VOL_DEBOUNCE_MS)

    def _on_master_volume_slider_released(self) -> None:
        if self._suppress_slider_midi:
            return
        self._master_vol_debounce_timer.stop()
        self._send_master_volume()

    def _on_transpose_changed(self, value: int) -> None:
        if self._suppress_slider_midi:
            return
        self._transpose_known = True
        self._sync_transpose_label(value)
        if self._midi.is_open:
            self._send_transpose()
        else:
            self._set_status(self._tr("status_transpose_offline", value=value))

    def _send_transpose(self, *, update_status: bool = True) -> None:
        if not self._midi.is_open:
            return
        value = self._transpose_sld.value()
        self._settings.setValue("transpose/value", value)
        try:
            self._midi_user_send(midix.master_coarse_tuning_realtime(value))
        except OSError:
            self._disconnect_device(
                status_key="status_device_lost", name=self._last_output_port or "?"
            )
            return
        except (ValueError, RuntimeError) as e:
            self._set_status(str(e))
            return
        if update_status:
            self._set_status(self._tr("status_transpose_sent", value=value))

    def _update_metronome_btn(self) -> None:
        if self._metronome_on is True:
            self._metronome_btn.setText(self._tr("btn_stop"))
            self._metronome_btn.setStyleSheet(
                "QPushButton { background-color: #c0392b; color: white; font-size: 13px; "
                "font-weight: bold; border-radius: 8px; }"
                "QPushButton:hover { background-color: #e74c3c; }"
                "QPushButton:pressed { background-color: #922b21; }"
            )
        else:
            self._metronome_btn.setText(self._tr("btn_start"))
            self._metronome_btn.setStyleSheet(
                "QPushButton { background-color: #E07828; color: white; font-size: 13px; "
                "font-weight: bold; border-radius: 8px; }"
                "QPushButton:hover { background-color: #f09040; }"
                "QPushButton:pressed { background-color: #b05818; }"
            )

    def _suppress_piano_state_poll_after_user_change(self) -> None:
        until = time.monotonic() + PIANO_POLL_SUPPRESS_AFTER_USER_CHANGE_S
        if until > self._piano_poll_suppress_until:
            self._piano_poll_suppress_until = until

    def _tone_uses_bank_program(self, tone: Tone | None) -> bool:
        if tone is None:
            return False
        return category_of(tone) in {"GM2", "Drums"}

    def _active_primary_tone(self) -> Tone | None:
        if self._keyboard_mode == 1:
            return self._split_right_picker.current_tone()
        if self._keyboard_mode == 2:
            return self._dual_picker1.current_tone()
        if self._keyboard_mode == 3:
            return self._twin_picker.current_tone()
        return self._single_picker.current_tone()

    def _send_tone_bank_program(self, tone: Tone) -> None:
        if not self._midi.is_open:
            return
        self._mark_app_bank_tx()
        prog_midi = max(0, min(127, tone.program_doc - 1))
        try:
            core, latch = midix.bank_select_program_and_latch_parts(
                MIDI_PART_CHANNEL, tone.bank_msb, tone.bank_lsb, prog_midi,
                latch_after_program=True,
            )
            self._midi_user_send_all(core, gap_s=midix.DEFAULT_MESSAGE_GAP_S)
            if latch:
                time.sleep(midix.POST_PROGRAM_CHANGE_LATCH_DELAY_S)
                self._midi_user_send_all(latch, gap_s=0.0)
        except OSError:
            self._disconnect_device(
                status_key="status_device_lost", name=self._last_output_port or "?"
            )
        except (ValueError, RuntimeError) as e:
            self._set_status(str(e))

    def _any_tone_picker_popup_open(self) -> bool:
        pickers = (
            getattr(self, "_single_picker", None),
            getattr(self, "_split_left_picker", None),
            getattr(self, "_split_right_picker", None),
            getattr(self, "_dual_picker1", None),
            getattr(self, "_dual_picker2", None),
            getattr(self, "_twin_picker", None),
        )
        return any(
            isinstance(picker, TonePicker) and picker.has_open_popup()
            for picker in pickers
        )

    def _midi_user_send(self, msg: mido.Message) -> None:
        self._midi.send(msg)
        self._suppress_piano_state_poll_after_user_change()

    def _midi_user_send_all(self, messages: Iterable[mido.Message], *, gap_s: float) -> None:
        self._midi.send_all_spaced(messages, gap_s=gap_s)
        self._suppress_piano_state_poll_after_user_change()

    def _request_piano_state(self) -> None:
        if not self._midi.is_open or not self._last_input_port:
            return
        if self._any_tone_picker_popup_open():
            return
        if time.monotonic() < self._piano_poll_suppress_until:
            return
        poll_msgs = (
            midix.master_volume_read(),
            midix.metronome_read_tempo(),
            midix.metronome_read_status(),
            midix.brilliance_read(),
            midix.ambience_read(),
            midix.key_touch_read(),
            midix.keyboard_mode_read(),
            midix.master_tuning_read(),
            midix.metronome_volume_read(),
            midix.metronome_tone_read(),
            midix.metronome_beat_read(),
            midix.metronome_pattern_read(),
            midix.split_point_read(),
            midix.split_right_octave_shift_read(),
            midix.split_octave_shift_read(),
            midix.split_balance_read(),
            midix.dual_tone1_octave_shift_read(),
            midix.dual_octave_shift_read(),
            midix.dual_balance_read(),
            midix.twin_piano_mode_read(),
            midix.tone_for_single_read(),
            midix.tone_for_split_read(),
            midix.tone_for_dual_read(),
        )
        try:
            self._midi.send_all_spaced(poll_msgs, gap_s=PIANO_POLL_MESSAGE_GAP_S)
        except OSError:
            self._disconnect_device(
                status_key="status_device_lost", name=self._last_output_port or "?"
            )

    def _schedule_tone_refresh_from_piano(self) -> None:
        """Tras un cambio de modo de teclado, los combos deben reflejar los tonos reales del FP-30X."""
        if not self._midi.is_open or not self._last_input_port:
            return
        self._tone_refresh_after_mode_timer.stop()
        self._tone_refresh_after_mode_timer.start()

    def _request_tones_from_piano(self) -> None:
        if not self._midi.is_open or not self._last_input_port:
            return
        if self._any_tone_picker_popup_open():
            self._tone_refresh_after_mode_timer.start(TONE_REFRESH_RETRY_WHEN_POPUP_OPEN_MS)
            return
        tone_msgs = (
            midix.tone_for_single_read(),
            midix.tone_for_split_read(),
            midix.tone_for_dual_read(),
            midix.split_right_octave_shift_read(),
            midix.split_octave_shift_read(),
            midix.dual_tone1_octave_shift_read(),
            midix.dual_octave_shift_read(),
        )
        try:
            self._midi.send_all_spaced(tone_msgs, gap_s=PIANO_POLL_MESSAGE_GAP_S)
        except OSError:
            self._disconnect_device(
                status_key="status_device_lost", name=self._last_output_port or "?"
            )

    def _handle_dt1(self, addr: tuple[int, int, int, int], data: tuple[int, ...]) -> None:
        # Master Volume: 01 00 02 13
        if addr == (0x01, 0x00, 0x02, 0x13) and data:
            if time.monotonic() - self._master_vol_sent_at < MASTER_VOL_IGNORE_DT1_S:
                return
            mv = max(0, min(midix.MASTER_VOLUME_DT1_MAX, int(data[0])))
            self._suppress_slider_midi = True
            try:
                self._master_sld.blockSignals(True)
                self._master_sld.setValue(mv)
                self._master_sld.blockSignals(False)
                self._master_lbl.setText(str(mv))
            finally:
                self._suppress_slider_midi = False
            return
        # Sequencer Tempo RO: 01 00 01 08
        if addr == (0x01, 0x00, 0x01, 0x08) and len(data) >= 2:
            bpm = data[0] * 128 + data[1]
            if TEMPO_MIN <= bpm <= TEMPO_MAX:
                self._set_tempo_ui(bpm)
            return
        # Metronome Status: 01 00 01 0F
        if addr == (0x01, 0x00, 0x01, 0x0F) and data:
            self._metronome_on = bool(data[0])
            self._update_metronome_btn()
            return
        # Brilliance: 01 00 02 1C
        if addr == (0x01, 0x00, 0x02, 0x1C) and data:
            display = max(-1, min(1, data[0] - 64))
            self._suppress_slider_midi = True
            try:
                self._brilliance_sld.blockSignals(True)
                self._brilliance_sld.setValue(display)
                self._brilliance_sld.blockSignals(False)
                self._brilliance_lbl.setText(f"{display:+d}" if display != 0 else "0")
            finally:
                self._suppress_slider_midi = False
            return
        # Ambience: 01 00 02 1A
        if addr == (0x01, 0x00, 0x02, 0x1A) and data:
            val = max(0, min(10, data[0]))
            self._suppress_slider_midi = True
            try:
                self._ambience_sld.blockSignals(True)
                self._ambience_sld.setValue(val)
                self._ambience_sld.blockSignals(False)
                self._ambience_lbl.setText(str(val))
            finally:
                self._suppress_slider_midi = False
            return
        # Key Touch: 01 00 02 1D
        if addr == (0x01, 0x00, 0x02, 0x1D) and data:
            idx = max(0, min(5, data[0]))
            self._key_touch_combo.blockSignals(True)
            self._key_touch_combo.setCurrentIndex(idx)
            self._key_touch_combo.blockSignals(False)
            return
        # Master Tuning: 01 00 02 18 — 2 bytes 7-bit; raw útil 9..518 y Hz = (4144 + raw) / 10.
        if addr == (0x01, 0x00, 0x02, 0x18) and len(data) >= 2:
            raw = data[0] * 128 + data[1]
            hz = midix.master_tuning_hz_from_raw(raw)
            self._suppress_slider_midi = True
            try:
                self._master_tuning_sld.blockSignals(True)
                self._master_tuning_sld.setValue(
                    max(midix.MASTER_TUNING_MIN_RAW, min(midix.MASTER_TUNING_MAX_RAW, raw))
                )
                self._master_tuning_sld.blockSignals(False)
                self._master_tuning_hz_lbl.setText(f"{hz:.1f} Hz")
            finally:
                self._suppress_slider_midi = False
            return
        # Keyboard Mode: 01 00 02 00
        if addr == (0x01, 0x00, 0x02, 0x00) and data:
            mode = max(0, min(3, data[0]))
            if mode != self._keyboard_mode:
                self._midi_sync_updating = True
                try:
                    self._tones_seg.set_index(mode)
                finally:
                    self._midi_sync_updating = False
                self._schedule_tone_refresh_from_piano()
            return
        # Split point: 01 00 02 01
        if addr == (0x01, 0x00, 0x02, 0x01) and data:
            self._split_point_val = max(0, min(127, data[0]))
            self._update_split_point_label()
            return
        # Split right octave shift: 01 00 02 16
        if addr == (0x01, 0x00, 0x02, 0x16) and data:
            self._split_right_shift_lbl.setText(
                str(max(OCTAVE_SHIFT_MIN, min(OCTAVE_SHIFT_MAX, int(data[0]) - 64)))
            )
            return
        # Split left octave shift: 01 00 02 02
        if addr == (0x01, 0x00, 0x02, 0x02) and data:
            self._split_left_shift_lbl.setText(
                str(max(OCTAVE_SHIFT_MIN, min(OCTAVE_SHIFT_MAX, int(data[0]) - 64)))
            )
            return
        # Split balance: 01 00 02 03 (byte centrado en 64; pasos de 1 con 9=centro)
        if addr == (0x01, 0x00, 0x02, 0x03) and data:
            val = midix.split_balance_normalize_panel(
                midix.split_balance_panel_from_sysex_byte(data[0])
            )
            left, right = midix.split_balance_display_lr(val)
            self._suppress_slider_midi = True
            try:
                self._split_balance_sld.blockSignals(True)
                self._split_balance_sld.setValue(val)
                self._split_balance_sld.blockSignals(False)
                self._split_balance_lbl.setText(f"{left}:{right}")
            finally:
                self._suppress_slider_midi = False
            return
        # Dual tone 1 octave shift: 01 00 02 17
        if addr == (0x01, 0x00, 0x02, 0x17) and data:
            self._dual_shift1_lbl.setText(
                str(max(OCTAVE_SHIFT_MIN, min(OCTAVE_SHIFT_MAX, int(data[0]) - 64)))
            )
            return
        # Dual tone 2 octave shift: 01 00 02 04
        if addr == (0x01, 0x00, 0x02, 0x04) and data:
            self._dual_shift2_lbl.setText(
                str(max(OCTAVE_SHIFT_MIN, min(OCTAVE_SHIFT_MAX, int(data[0]) - 64)))
            )
            return
        # Dual balance: 01 00 02 05 (byte centrado en 64; panel útil ~6..11 en FP-30X)
        if addr == (0x01, 0x00, 0x02, 0x05) and data:
            val = midix.dual_balance_panel_from_sysex_byte(data[0])
            left, right = midix.dual_balance_display_lr(val)
            self._suppress_slider_midi = True
            try:
                self._dual_balance_sld.blockSignals(True)
                self._dual_balance_sld.setValue(val)
                self._dual_balance_sld.blockSignals(False)
                self._dual_balance_lbl.setText(f"{left}:{right}")
            finally:
                self._suppress_slider_midi = False
            return
        # Twin Piano mode: 01 00 02 06
        if addr == (0x01, 0x00, 0x02, 0x06) and data:
            twin_m = max(0, min(1, data[0]))
            self._midi_sync_updating = True
            try:
                self._twin_mode_seg.set_index(twin_m)
            finally:
                self._midi_sync_updating = False
            return
        # Tones (catálogo interno Roland): Single / Split (mano izq.) / Dual (2.º tono)
        if addr == (0x01, 0x00, 0x02, 0x07) and len(data) >= 3:
            if self._tone_uses_bank_program(self._active_primary_tone()):
                return
            tone = tone_from_dt1_bytes(data[0], data[1], data[2])
            if tone is not None:
                self._single_picker.set_tone(tone)
                self._split_right_picker.set_tone(tone)
                self._dual_picker1.set_tone(tone)
                self._twin_picker.set_tone(tone)
            return
        if addr == (0x01, 0x00, 0x02, 0x0A) and len(data) >= 3:
            if self._tone_uses_bank_program(self._split_left_picker.current_tone()):
                return
            tone = tone_from_dt1_bytes(data[0], data[1], data[2])
            if tone is not None:
                self._split_left_picker.set_tone(tone)
            return
        if addr == (0x01, 0x00, 0x02, 0x0D) and len(data) >= 3:
            if self._tone_uses_bank_program(self._dual_picker2.current_tone()):
                return
            tone = tone_from_dt1_bytes(data[0], data[1], data[2])
            if tone is not None:
                self._dual_picker2.set_tone(tone)
            return
        # Metronome Volume: 01 00 02 21
        if addr == (0x01, 0x00, 0x02, 0x21) and data:
            val = max(0, min(10, data[0]))
            self._suppress_slider_midi = True
            try:
                self._metro_vol_sld.blockSignals(True)
                self._metro_vol_sld.setValue(val)
                self._metro_vol_sld.blockSignals(False)
                self._metro_vol_lbl.setText(str(val))
            finally:
                self._suppress_slider_midi = False
            return
        # Metronome Tone: 01 00 02 22
        if addr == (0x01, 0x00, 0x02, 0x22) and data:
            self._midi_sync_updating = True
            try:
                self._metro_tone_seg.set_index(max(0, min(3, data[0])))
            finally:
                self._midi_sync_updating = False
            return
        # Metronome Pattern: 01 00 02 20
        if addr == (0x01, 0x00, 0x02, 0x20) and data:
            pat = max(0, min(7, data[0]))
            self._midi_sync_updating = True
            try:
                btn = self._pattern_btn_group.button(pat)
                if btn:
                    btn.setChecked(True)
            finally:
                self._midi_sync_updating = False
            return
        # Metronome Beat: 01 00 02 1F
        if addr == (0x01, 0x00, 0x02, 0x1F) and data:
            midi_beat = data[0]
            self._midi_sync_updating = True
            try:
                match = next(
                    (i for i, mv in enumerate(self._beat_midi_values) if mv == midi_beat),
                    None,
                )
                if match is not None:
                    btn = self._beat_btn_group.button(match)
                    if btn:
                        btn.setChecked(True)
                else:
                    for i in range(len(self._beat_midi_values)):
                        b = self._beat_btn_group.button(i)
                        if b is not None:
                            b.setChecked(False)
            finally:
                self._midi_sync_updating = False
            return

    def _on_tempo_changed(self, _value: int) -> None:
        if self._suppress_slider_midi:
            return
        self._tempo_debounce_timer.stop()
        self._tempo_debounce_timer.start(TEMPO_DEBOUNCE_MS)

    def _flush_tempo(self) -> None:
        if not self._midi.is_open or self._suppress_slider_midi:
            return
        try:
            self._midi_user_send(midix.metronome_set_tempo(self._tempo_sld.value()))
        except OSError:
            self._disconnect_device(
                status_key="status_device_lost", name=self._last_output_port or "?"
            )
        except (ValueError, RuntimeError) as e:
            self._set_status(str(e))

    def _set_tempo_ui(self, bpm: int) -> None:
        self._suppress_slider_midi = True
        try:
            self._tempo_sld.blockSignals(True)
            self._tempo_sld.setValue(bpm)
            self._tempo_sld.blockSignals(False)
            self._tempo_val.setText(str(bpm))
        finally:
            self._suppress_slider_midi = False

    def _send_metronome_probe(self) -> None:
        if not self._midi.is_open:
            self._set_status(self._tr("msg_connect_before_send"))
            return
        try:
            self._midi_user_send(midix.metronome_toggle())
        except OSError:
            self._disconnect_device(
                status_key="status_device_lost", name=self._last_output_port or "?"
            )
            return
        except (ValueError, RuntimeError) as e:
            self._set_status(str(e))
            return
        self._metronome_on = not self._metronome_on if self._metronome_on is not None else True
        self._update_metronome_btn()
        self._set_status(self._tr("status_metronome_probe_sent"))

    def _send_master_volume(self) -> None:
        if not self._midi.is_open:
            return
        value = self._master_sld.value()
        try:
            self._master_vol_sent_at = time.monotonic()
            self._midi_user_send(midix.master_volume_set(value))
            self._set_status(self._tr("status_master_volume_sent", value=value))
        except OSError:
            self._disconnect_device(
                status_key="status_device_lost", name=self._last_output_port or "?"
            )
        except (ValueError, RuntimeError) as e:
            self._set_status(str(e))

    # ── Piano Settings handlers ───────────────────────────────────────────────

    def _on_key_touch_changed(self, index: int) -> None:
        if self._suppress_slider_midi or index < 0:
            return
        self._send_key_touch()

    def _send_key_touch(self) -> None:
        if not self._midi.is_open:
            return
        idx = self._key_touch_combo.currentIndex()
        if idx < 0:
            return
        try:
            self._midi_user_send(midix.key_touch_set(idx))
        except OSError:
            self._disconnect_device(
                status_key="status_device_lost", name=self._last_output_port or "?"
            )
        except (ValueError, RuntimeError) as e:
            self._set_status(str(e))

    def _on_master_tuning_changed(self, raw: int) -> None:
        hz = midix.master_tuning_hz_from_raw(raw)
        self._master_tuning_hz_lbl.setText(f"{hz:.1f} Hz")

    def _send_master_tuning(self) -> None:
        if not self._midi.is_open:
            return
        raw = self._master_tuning_sld.value()
        hz = midix.master_tuning_hz_from_raw(raw)
        try:
            if self._verbose:
                print(
                    f"MIDI [MASTER_TUNING] send raw={raw} hz={hz:.1f}",
                    file=sys.stderr,
                    flush=True,
                )
            if self._last_input_port:
                self._midi_user_send_all(
                    (midix.master_tuning_set_raw(raw), midix.master_tuning_read()),
                    gap_s=0.05,
                )
            else:
                self._midi_user_send(midix.master_tuning_set_raw(raw))
        except OSError:
            self._disconnect_device(
                status_key="status_device_lost", name=self._last_output_port or "?"
            )
        except (ValueError, RuntimeError) as e:
            self._set_status(str(e))

    def _on_brilliance_changed(self, value: int) -> None:
        if self._suppress_slider_midi:
            return
        self._brilliance_lbl.setText(f"{value:+d}" if value != 0 else "0")
        self._send_brilliance()

    def _send_brilliance(self) -> None:
        if not self._midi.is_open:
            return
        try:
            self._midi_user_send(midix.brilliance_set(self._brilliance_sld.value()))
        except OSError:
            self._disconnect_device(
                status_key="status_device_lost", name=self._last_output_port or "?"
            )
        except (ValueError, RuntimeError) as e:
            self._set_status(str(e))

    def _on_ambience_changed(self, value: int) -> None:
        if self._suppress_slider_midi:
            return
        self._ambience_lbl.setText(str(value))
        self._send_ambience()

    def _send_ambience(self) -> None:
        if not self._midi.is_open:
            return
        try:
            self._midi_user_send(midix.ambience_set(self._ambience_sld.value()))
        except OSError:
            self._disconnect_device(
                status_key="status_device_lost", name=self._last_output_port or "?"
            )
        except (ValueError, RuntimeError) as e:
            self._set_status(str(e))

    # ── Tones tab handlers ───────────────────────────────────────────────────

    def _on_keyboard_mode_changed(self, mode: int) -> None:
        self._keyboard_mode = mode
        self._tones_stack.setCurrentIndex(mode)
        if self._midi_sync_updating or not self._midi.is_open:
            return
        try:
            self._midi_user_send(midix.keyboard_mode_set(mode))
        except OSError:
            self._disconnect_device(
                status_key="status_device_lost", name=self._last_output_port or "?"
            )
            return
        except (ValueError, RuntimeError) as e:
            self._set_status(str(e))
            return
        self._schedule_tone_refresh_from_piano()

    def _send_tone_single(self, tone: Tone) -> None:
        if not self._midi.is_open:
            return
        if self._tone_uses_bank_program(tone):
            self._send_tone_bank_program(tone)
            return
        cat_idx, n_hi, n_lo = tone_dt1_encoding(tone)
        num = n_hi * 128 + n_lo
        try:
            self._midi_user_send(midix.tone_for_single_set(cat_idx, num))
        except OSError:
            self._disconnect_device(
                status_key="status_device_lost", name=self._last_output_port or "?"
            )
        except (ValueError, RuntimeError) as e:
            self._set_status(str(e))

    def _on_single_tone_changed(self, tone: Tone | None) -> None:
        if tone is None or self._midi_sync_updating:
            return
        self._set_status(self._tr("status_preset_offline", name=tone.name) if not self._midi.is_open else "")
        if not self._midi.is_open:
            return
        self._send_tone_single(tone)
        if not self._tone_uses_bank_program(tone):
            self._schedule_tone_refresh_from_piano()
        self._set_status(self._tr("status_tone_from_piano", name=tone.name))

    def _on_split_right_tone_changed(self, tone: Tone | None) -> None:
        if tone is None or self._midi_sync_updating or not self._midi.is_open:
            return
        self._send_tone_single(tone)
        if not self._tone_uses_bank_program(tone):
            self._schedule_tone_refresh_from_piano()

    def _on_split_left_tone_changed(self, tone: Tone | None) -> None:
        if tone is None or self._midi_sync_updating or not self._midi.is_open:
            return
        cat_idx, n_hi, n_lo = tone_dt1_encoding(tone)
        num = n_hi * 128 + n_lo
        try:
            self._midi_user_send(midix.tone_for_split_set(cat_idx, num))
        except OSError:
            self._disconnect_device(
                status_key="status_device_lost", name=self._last_output_port or "?"
            )
        except (ValueError, RuntimeError) as e:
            self._set_status(str(e))

    def _on_dual_tone1_changed(self, tone: Tone | None) -> None:
        if tone is None or self._midi_sync_updating or not self._midi.is_open:
            return
        self._send_tone_single(tone)
        if not self._tone_uses_bank_program(tone):
            self._schedule_tone_refresh_from_piano()

    def _on_dual_tone2_changed(self, tone: Tone | None) -> None:
        if tone is None or self._midi_sync_updating or not self._midi.is_open:
            return
        cat_idx, n_hi, n_lo = tone_dt1_encoding(tone)
        num = n_hi * 128 + n_lo
        try:
            self._midi_user_send(midix.tone_for_dual_set(cat_idx, num))
        except OSError:
            self._disconnect_device(
                status_key="status_device_lost", name=self._last_output_port or "?"
            )
        except (ValueError, RuntimeError) as e:
            self._set_status(str(e))

    def _on_twin_tone_changed(self, tone: Tone | None) -> None:
        if tone is None or self._midi_sync_updating or not self._midi.is_open:
            return
        self._send_tone_single(tone)
        if not self._tone_uses_bank_program(tone):
            self._schedule_tone_refresh_from_piano()

    def _on_split_balance_changed(self, value: int) -> None:
        normalized = midix.split_balance_normalize_panel(value)
        if normalized != value:
            self._suppress_slider_midi = True
            try:
                self._split_balance_sld.blockSignals(True)
                self._split_balance_sld.setValue(normalized)
                self._split_balance_sld.blockSignals(False)
            finally:
                self._suppress_slider_midi = False
            value = normalized
        left, right = midix.split_balance_display_lr(value)
        self._split_balance_lbl.setText(f"{left}:{right}")
        if not self._midi.is_open:
            return
        try:
            self._midi.send(midix.split_balance_set(value))
            self._midi.send_all_spaced(
                midix.split_balance_control_changes(value),
                gap_s=midix.DEFAULT_MESSAGE_GAP_S,
            )
            self._suppress_piano_state_poll_after_user_change()
        except OSError:
            self._disconnect_device(
                status_key="status_device_lost", name=self._last_output_port or "?"
            )

    def _on_dual_balance_changed(self, value: int) -> None:
        left, right = midix.dual_balance_display_lr(value)
        self._dual_balance_lbl.setText(f"{left}:{right}")
        if not self._midi.is_open:
            return
        try:
            self._midi.send(midix.dual_balance_set(value))
            self._midi.send_all_spaced(
                midix.dual_balance_control_changes(value),
                gap_s=midix.DEFAULT_MESSAGE_GAP_S,
            )
            self._suppress_piano_state_poll_after_user_change()
        except OSError:
            self._disconnect_device(
                status_key="status_device_lost", name=self._last_output_port or "?"
            )

    def _update_split_point_label(self) -> None:
        self._split_point_lbl.setText(midi_note_name(self._split_point_val, self._lang))

    def _dec_split_point(self) -> None:
        if self._split_point_val > 0:
            self._split_point_val -= 1
            self._update_split_point_label()
            self._send_split_point()

    def _inc_split_point(self) -> None:
        if self._split_point_val < 127:
            self._split_point_val += 1
            self._update_split_point_label()
            self._send_split_point()

    def _send_split_point(self) -> None:
        if not self._midi.is_open:
            return
        try:
            self._midi_user_send(midix.split_point_set(self._split_point_val))
        except OSError:
            self._disconnect_device(
                status_key="status_device_lost", name=self._last_output_port or "?"
            )

    def _send_split_right_octave_shift(self, value: int) -> None:
        if not self._midi.is_open:
            return
        try:
            self._midi_user_send(midix.split_right_octave_shift_set(value))
        except OSError:
            self._disconnect_device(
                status_key="status_device_lost", name=self._last_output_port or "?"
            )

    def _send_split_left_octave_shift(self, value: int) -> None:
        if not self._midi.is_open:
            return
        try:
            self._midi_user_send(midix.split_octave_shift_set(value))
        except OSError:
            self._disconnect_device(
                status_key="status_device_lost", name=self._last_output_port or "?"
            )

    def _send_dual_tone1_octave_shift(self, value: int) -> None:
        if not self._midi.is_open:
            return
        try:
            self._midi_user_send(midix.dual_tone1_octave_shift_set(value))
        except OSError:
            self._disconnect_device(
                status_key="status_device_lost", name=self._last_output_port or "?"
            )

    def _send_dual_tone2_octave_shift(self, value: int) -> None:
        if not self._midi.is_open:
            return
        try:
            self._midi_user_send(midix.dual_octave_shift_set(value))
        except OSError:
            self._disconnect_device(
                status_key="status_device_lost", name=self._last_output_port or "?"
            )

    def _on_twin_mode_changed(self, mode: int) -> None:
        if self._midi_sync_updating or not self._midi.is_open:
            return
        try:
            self._midi_user_send(midix.twin_piano_mode_set(mode))
        except OSError:
            self._disconnect_device(
                status_key="status_device_lost", name=self._last_output_port or "?"
            )

    # ── Metronome tab handlers ───────────────────────────────────────────────

    def _on_metro_volume_changed(self, value: int) -> None:
        if self._suppress_slider_midi:
            return
        if not self._midi.is_open:
            return
        try:
            self._midi_user_send(midix.metronome_volume_set(value))
        except OSError:
            self._disconnect_device(
                status_key="status_device_lost", name=self._last_output_port or "?"
            )
        except (ValueError, RuntimeError) as e:
            self._set_status(str(e))

    def _on_metro_tone_changed(self, idx: int) -> None:
        if self._midi_sync_updating or not self._midi.is_open:
            return
        try:
            self._midi_user_send(midix.metronome_tone_set(idx))
        except OSError:
            self._disconnect_device(
                status_key="status_device_lost", name=self._last_output_port or "?"
            )
        except (ValueError, RuntimeError) as e:
            self._set_status(str(e))

    def _on_metro_beat_changed(self, midi_val: int) -> None:
        if self._midi_sync_updating or not self._midi.is_open:
            return
        try:
            self._midi_user_send(midix.metronome_beat_set(midi_val))
        except OSError:
            self._disconnect_device(
                status_key="status_device_lost", name=self._last_output_port or "?"
            )
        except (ValueError, RuntimeError) as e:
            self._set_status(str(e))

    def _on_metro_pattern_changed(self, pat: int) -> None:
        if self._midi_sync_updating or not self._midi.is_open:
            return
        try:
            self._midi_user_send(midix.metronome_pattern_set(pat))
        except OSError:
            self._disconnect_device(
                status_key="status_device_lost", name=self._last_output_port or "?"
            )
        except (ValueError, RuntimeError) as e:
            self._set_status(str(e))
