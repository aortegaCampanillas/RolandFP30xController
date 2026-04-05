from __future__ import annotations

import sys
import time

import mido
from PySide6.QtCore import Qt, QSettings, QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from roland_fp30x_controller.midi import messages as midix
from roland_fp30x_controller.midi.bank_program_parser import BankProgramParser
from roland_fp30x_controller.midi.client import MidiOutClient
from roland_fp30x_controller.midi.ports import list_input_names, list_output_names
from roland_fp30x_controller.midi.rpn_parser import RpnParser, parse_master_coarse_tuning_sysex
from roland_fp30x_controller.midi.sysex_parser import parse_roland_dt1
from roland_fp30x_controller.midi.tone_catalog import TONE_PRESETS, Tone
from roland_fp30x_controller.ui.i18n import Lang, tr
from roland_fp30x_controller.ui.midi_in_worker import MidiInWorker

# Valores iniciales / «Restablecer». Parte MIDI fija en canal 4 (FP-30X + SMF Internal, Roland).
DEFAULT_PRESET_INDEX = 0
MIDI_PART_CHANNEL = 4
DEFAULT_MASTER_VOLUME = 127
DEFAULT_TRANSPOSE = 0
DEFAULT_TEMPO = 120
TEMPO_MIN = 20
TEMPO_MAX = 250

# Retardo tras el último movimiento del slider antes de enviar (teclado y ratón).
MASTER_VOL_DEBOUNCE_MS = 55
TEMPO_DEBOUNCE_MS = 120
# Tras enviar banco/programa desde la app, ignorar eco del piano (segundos).
PIANO_PATCH_IGNORE_S = 0.55
# Tras enviar DT1 master volume, ignorar la respuesta DT1 del piano (evita que el eco
# de la confirmación sobreescriba el slider con el valor anterior del piano).
MASTER_VOL_IGNORE_DT1_S = 1.5
PORT_WATCHDOG_MS = 1000



class MainWindow(QMainWindow):
    def __init__(self, *, verbose: bool = False) -> None:
        super().__init__()
        self._verbose = verbose
        self._lang: Lang = "en"
        self._last_output_port: str | None = None
        self._last_input_port: str | None = None
        self._midi = MidiOutClient(
            trace_send=self._trace_midi_out if verbose else None,
        )
        self._midi_in_worker: MidiInWorker | None = None
        # Entrada: canal 1 (transmisión típica panel FP-30X) y 4 (parte lista MIDI).
        self._bank_parser = BankProgramParser((1, MIDI_PART_CHANNEL))
        self._rpn_parser = RpnParser((1, MIDI_PART_CHANNEL))
        self._ignore_piano_patch_until = 0.0
        self._master_vol_sent_at = 0.0
        self._settings = QSettings("RolandFP30xController", "RolandFP30xController")
        self._transpose_known = False
        self._metronome_on: bool | None = None
        self._tone_combo_populating = False
        self._syncing_tone_widgets = False
        self._suppress_slider_midi = False
        self._master_vol_debounce_timer = QTimer(self)
        self._master_vol_debounce_timer.setSingleShot(True)
        self._master_vol_debounce_timer.timeout.connect(lambda: self._send_master_volume())
        self._state_request_timer = QTimer(self)
        self._state_request_timer.setSingleShot(True)
        self._state_request_timer.timeout.connect(self._request_piano_state)
        self._tempo_debounce_timer = QTimer(self)
        self._tempo_debounce_timer.setSingleShot(True)
        self._tempo_debounce_timer.timeout.connect(self._flush_tempo)
        self._port_watchdog_timer = QTimer(self)
        self._port_watchdog_timer.setInterval(PORT_WATCHDOG_MS)
        self._port_watchdog_timer.timeout.connect(self._check_connected_ports)
        self._port_watchdog_timer.start()

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        scroll.setWidget(inner)
        root.addWidget(scroll)
        layout = QVBoxLayout(inner)
        # Evita que el contenido del scroll se comprima por debajo del ancho útil.
        inner.setMinimumWidth(560)

        layout.addWidget(self._build_configuration_panel())

        self._lower_panels = QWidget()
        lower_layout = QVBoxLayout(self._lower_panels)
        lower_layout.setContentsMargins(0, 0, 0, 0)
        lower_layout.addWidget(self._build_main_panel())
        lower_layout.addWidget(self._build_sustain())
        self._lower_panels.setEnabled(False)
        layout.addWidget(self._lower_panels)

        layout.addStretch(1)

        reset_bar = QHBoxLayout()
        self._reset_btn = QPushButton()
        self._reset_btn.clicked.connect(self._reset_defaults)
        reset_bar.addWidget(self._reset_btn)
        reset_bar.addStretch(1)
        root.addLayout(reset_bar)

        self._status = QLabel()
        self._status.setWordWrap(True)
        root.addWidget(self._status)

        self._retranslate_ui()
        self._refresh_ports()
        self.setMinimumWidth(580)
        self.resize(640, 680)

    def _tr(self, key: str, **kwargs: object) -> str:
        return tr(self._lang, key, **kwargs)

    def _trace_midi_out(self, msg: mido.Message) -> None:
        self._print_midi_trace("OUT", msg)

    def _print_midi_trace(self, direction: str, msg: mido.Message) -> None:
        try:
            raw = " ".join(f"{b:02X}" for b in msg.bytes())
        except (AttributeError, ValueError, TypeError):
            raw = "?"
        print(
            f"MIDI [{direction}] {msg!s}  |  {raw}",
            file=sys.stderr,
            flush=True,
        )

    def _on_language_changed(self, index: int) -> None:
        if index < 0:
            return
        code = self._lang_combo.itemData(index)
        if code == "en" or code == "es":
            self._lang = code
        else:
            return
        self._retranslate_ui()

    def _retranslate_ui(self) -> None:
        self.setWindowTitle(self._tr("window_title"))
        self._group_configuration.setTitle(self._tr("group_configuration"))
        self._lang_lbl.setText(self._tr("label_language"))
        self._label_device.setText(self._tr("label_device"))
        self._refresh_btn.setText(self._tr("btn_refresh"))
        self._update_connect_button_text()
        self._group_main.setTitle(self._tr("group_main"))
        self._label_master_vol.setText(self._tr("label_master_volume"))
        self._label_transpose.setText(self._tr("label_transpose"))
        self._label_instrument.setText(self._tr("label_instrument"))
        self._update_metronome_btn()
        self._label_tempo.setText(self._tr("label_tempo"))
        self._transpose_sld.setToolTip(self._tr("tooltip_transpose"))
        self._master_sld.setToolTip(self._tr("tooltip_master_volume"))
        self._group_pedal.setTitle(self._tr("group_pedal"))
        self._sustain.setText(self._tr("pedal_sustain"))
        self._reset_btn.setText(self._tr("btn_reset_defaults"))
        if not self._midi.is_open:
            self._status.setText(self._tr("status_no_midi"))
        elif self._last_output_port:
            if self._midi_in_worker is not None and self._last_input_port:
                self._status.setText(
                    self._tr(
                        "status_connected_sync",
                        out=self._last_output_port,
                        inn=self._last_input_port,
                    )
                )
            else:
                self._status.setText(
                    self._tr("status_connected", name=self._last_output_port)
                )

    def _update_connect_button_text(self) -> None:
        self._connect_btn.setText(
            self._tr("btn_disconnect")
            if self._midi.is_open
            else self._tr("btn_connect")
        )

    def _build_configuration_panel(self) -> QWidget:
        self._group_configuration = QGroupBox()
        v = QVBoxLayout(self._group_configuration)

        lang_row = QHBoxLayout()
        self._lang_lbl = QLabel()
        self._lang_combo = QComboBox()
        self._lang_combo.addItem("English", "en")
        self._lang_combo.addItem("Español", "es")
        self._lang_combo.blockSignals(True)
        self._lang_combo.setCurrentIndex(0)
        self._lang_combo.blockSignals(False)
        self._lang_combo.currentIndexChanged.connect(self._on_language_changed)
        lang_row.addWidget(self._lang_lbl)
        lang_row.addWidget(self._lang_combo, stretch=1)
        v.addLayout(lang_row)

        port_row = QHBoxLayout()
        self._port_combo = QComboBox()
        self._port_combo.setMinimumWidth(240)
        self._refresh_btn = QPushButton()
        self._refresh_btn.clicked.connect(self._refresh_ports)
        self._connect_btn = QPushButton()
        self._connect_btn.clicked.connect(self._toggle_connect)
        self._label_device = QLabel()
        port_row.addWidget(self._label_device)
        port_row.addWidget(self._port_combo, stretch=1)
        port_row.addWidget(self._refresh_btn)
        port_row.addWidget(self._connect_btn)
        v.addLayout(port_row)

        return self._group_configuration

    def _build_main_panel(self) -> QWidget:
        self._group_main = QGroupBox()
        v = QVBoxLayout(self._group_main)

        master_row = QHBoxLayout()
        self._label_master_vol = QLabel()
        self._master_sld = QSlider(Qt.Orientation.Horizontal)
        self._master_sld.setRange(0, 127)
        self._master_sld.setValue(DEFAULT_MASTER_VOLUME)
        self._master_sld.setTracking(True)
        self._master_lbl = QLabel("127")
        self._master_lbl.setMinimumWidth(36)
        self._master_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._master_sld.valueChanged.connect(lambda v: self._master_lbl.setText(str(v)))
        self._master_sld.valueChanged.connect(self._schedule_master_volume_debounced)
        self._master_sld.sliderReleased.connect(self._on_master_volume_slider_released)
        master_row.addWidget(self._label_master_vol)
        master_row.addWidget(self._master_sld, stretch=1)
        master_row.addWidget(self._master_lbl)
        v.addLayout(master_row)

        transpose_row = QHBoxLayout()
        self._label_transpose = QLabel()
        self._transpose_sld = QSlider(Qt.Orientation.Horizontal)
        self._transpose_sld.setRange(-24, 24)
        saved_transpose = int(self._settings.value("transpose/value", DEFAULT_TRANSPOSE))
        self._transpose_sld.setValue(saved_transpose)
        self._transpose_known = True
        self._transpose_sld.setTracking(True)
        self._transpose_lbl = QLabel(f"{saved_transpose:+d}")
        self._transpose_lbl.setMinimumWidth(36)
        self._transpose_lbl.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self._transpose_sld.valueChanged.connect(
            lambda v: self._sync_transpose_label(v if self._transpose_known else None)
        )
        self._transpose_sld.valueChanged.connect(self._on_transpose_changed)
        transpose_row.addWidget(self._label_transpose)
        transpose_row.addWidget(self._transpose_sld, stretch=1)
        transpose_row.addWidget(self._transpose_lbl)
        v.addLayout(transpose_row)

        instrument_row = QHBoxLayout()
        self._label_instrument = QLabel()
        self._tone_combo = QComboBox()
        self._tone_combo.setMaxVisibleItems(30)
        self._tone_combo_populating = True
        try:
            for t in TONE_PRESETS:
                self._tone_combo.addItem(t.name, t)
        finally:
            self._tone_combo_populating = False
        self._tone_combo.currentIndexChanged.connect(self._on_tone_combo_index_changed)
        instrument_row.addWidget(self._label_instrument)
        instrument_row.addWidget(self._tone_combo, stretch=1)
        v.addLayout(instrument_row)

        test_row = QHBoxLayout()
        self._metronome_btn = QPushButton()
        self._metronome_btn.clicked.connect(self._send_metronome_probe)
        test_row.addWidget(self._metronome_btn)
        test_row.addStretch(1)
        v.addLayout(test_row)

        tempo_row = QHBoxLayout()
        self._label_tempo = QLabel()
        self._tempo_sld = QSlider(Qt.Orientation.Horizontal)
        self._tempo_sld.setRange(TEMPO_MIN, TEMPO_MAX)
        self._tempo_sld.setValue(DEFAULT_TEMPO)
        self._tempo_sld.setTracking(True)
        self._tempo_val = QLabel(str(DEFAULT_TEMPO))
        self._tempo_val.setMinimumWidth(36)
        self._tempo_val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._tempo_sld.valueChanged.connect(lambda v: self._tempo_val.setText(str(v)))
        self._tempo_sld.valueChanged.connect(self._on_tempo_changed)
        self._tempo_sld.sliderReleased.connect(self._flush_tempo)
        tempo_row.addWidget(self._label_tempo)
        tempo_row.addWidget(self._tempo_sld, stretch=1)
        tempo_row.addWidget(self._tempo_val)
        v.addLayout(tempo_row)

        return self._group_main

    def _build_sustain(self) -> QWidget:
        self._group_pedal = QGroupBox()
        h = QHBoxLayout(self._group_pedal)
        self._sustain = QCheckBox()
        self._sustain.toggled.connect(self._on_sustain)
        h.addWidget(self._sustain)
        h.addStretch(1)
        return self._group_pedal

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
        self._transpose_lbl.setText("--" if value is None else f"{value:+d}")

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
        self._state_request_timer.stop()
        self._cancel_debounce_timers()
        self._stop_midi_in_worker()
        self._midi.close()
        self._last_output_port = None
        self._last_input_port = None
        self._metronome_on = None
        self._update_metronome_btn()
        self._update_connect_button_text()
        self._lower_panels.setEnabled(False)
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
            self._disconnect_device(
                status_key="status_device_lost",
                name=self._last_output_port,
            )
            return
        if self._last_input_port and self._last_input_port not in list_input_names():
            lost_name = self._last_input_port
            self._stop_midi_in_worker()
            self._last_input_port = None
            self._set_status(self._tr("status_device_lost", name=lost_name))
            self._refresh_ports()

    def _on_midi_in_port_lost(self, _error: str) -> None:
        if not self._last_input_port:
            return
        lost_name = self._last_input_port
        self._stop_midi_in_worker()
        self._last_input_port = None
        if self._last_output_port and self._midi.is_open:
            self._set_status(self._tr("status_device_lost", name=lost_name))

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
        if time.monotonic() < self._ignore_piano_patch_until:
            return
        dt1 = parse_roland_dt1(msg)
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
        msb, lsb, pdoc = parsed
        for i, t in enumerate(TONE_PRESETS):
            if t.bank_msb == msb and t.bank_lsb == lsb and t.program_doc == pdoc:
                if self._tone_combo.currentIndex() != i:
                    self._apply_patch_from_piano(i)
                return
        self._set_status(
            self._tr("status_piano_tone_unknown", msb=msb, lsb=lsb, pdoc=pdoc)
        )

    def _apply_patch_from_piano(self, index: int) -> None:
        self._syncing_tone_widgets = True
        try:
            self._tone_combo.blockSignals(True)
            self._tone_combo.setCurrentIndex(index)
            self._tone_combo.blockSignals(False)
        finally:
            self._syncing_tone_widgets = False
        name = TONE_PRESETS[index].name
        self._set_status(self._tr("status_tone_from_piano", name=name))

    def _toggle_connect(self) -> None:
        if self._midi.is_open:
            self._disconnect_device(status_key="status_disconnected")
            return
        name = self._port_combo.currentText().strip()
        if not name:
            QMessageBox.warning(
                self, self._tr("dlg_midi"), self._tr("err_no_port")
            )
            return
        try:
            self._midi.open(name)
        except OSError as e:
            QMessageBox.critical(
                self,
                self._tr("dlg_midi"),
                self._tr("err_open_port", error=str(e)),
            )
            return
        self._last_output_port = name
        self._last_input_port = None
        self._transpose_known = False
        self._metronome_on = None
        self._sync_transpose_label(None)
        self._update_metronome_btn()
        self._update_connect_button_text()
        self._lower_panels.setEnabled(True)
        # Handshake: notifica al FP-30X que una app está conectada.
        # Sin este mensaje el piano ignora DT1 de master volume y metrónomo.
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
                QMessageBox.warning(
                    self,
                    self._tr("dlg_midi"),
                    self._tr("warn_input_open", error=str(e)),
                )
        if self._midi_in_worker is not None and self._last_input_port:
            self._set_status(
                self._tr(
                    "status_connected_sync",
                    out=name,
                    inn=self._last_input_port,
                )
            )
            # Leer estado del piano 200 ms después de que el worker esté listo
            self._state_request_timer.start(200)
        else:
            self._set_status(self._tr("status_connected", name=name))
        # Re-enviar el transpose guardado si no es 0
        if self._transpose_sld.value() != 0:
            self._send_transpose(update_status=False)

    def _set_status(self, text: str) -> None:
        self._status.setText(text)

    def _reset_defaults(self) -> None:
        self._cancel_debounce_timers()
        self._suppress_slider_midi = True
        try:
            self._syncing_tone_widgets = True
            try:
                self._tone_combo.blockSignals(True)
                self._tone_combo.setCurrentIndex(DEFAULT_PRESET_INDEX)
                self._tone_combo.blockSignals(False)
            finally:
                self._syncing_tone_widgets = False

            self._sustain.blockSignals(True)
            self._sustain.setChecked(False)
            self._sustain.blockSignals(False)

            self._master_sld.setValue(DEFAULT_MASTER_VOLUME)
            self._set_transpose_ui(DEFAULT_TRANSPOSE, known=True)
            self._set_tempo_ui(DEFAULT_TEMPO)
        finally:
            self._suppress_slider_midi = False

        if not self._midi.is_open:
            self._set_status(self._tr("status_defaults_offline"))
            return

        self._reapply_full_part_to_device()
        self._set_status(self._tr("status_defaults_sent"))

    def _cancel_debounce_timers(self) -> None:
        self._master_vol_debounce_timer.stop()
        self._tempo_debounce_timer.stop()

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

    def _flush_sustain_pedal_to_device(self) -> None:
        if not self._midi.is_open:
            return
        self._send_cc(64, 127 if self._sustain.isChecked() else 0)

    def _reapply_full_part_to_device(
        self,
        *,
        latch_after_program: bool = True,
        update_status: bool = True,
    ) -> None:
        if not self._midi.is_open:
            return
        tone = self._tone_from_combo()
        if tone is not None:
            self._send_bank_program(
                tone.bank_msb,
                tone.bank_lsb,
                tone.program_doc,
                tone_name=tone.name,
                silent_if_disconnected=True,
                latch_after_program=latch_after_program,
                update_status=update_status,
            )
        self._flush_sustain_pedal_to_device()
        self._send_master_volume()
        self._send_transpose(update_status=False)
        if update_status:
            self._set_status(
                self._tr("status_full_reapply")
                + " "
                + self._tr("status_transpose_sent", value=self._transpose_sld.value())
            )

    def _send_cc(self, control: int, value: int) -> None:
        if not self._midi.is_open:
            return
        try:
            self._midi.send(midix.control_change(MIDI_PART_CHANNEL, control, value))
            if control == 91 and value > 0:
                tail = min(127, max(value, 28))
                self._midi.send(midix.gm2_global_reverb_parameter(1, tail))
        except OSError:
            self._disconnect_device(
                status_key="status_device_lost",
                name=self._last_output_port or "?",
            )
        except (ValueError, RuntimeError) as e:
            self._set_status(str(e))

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
            self._midi.send(midix.master_coarse_tuning_realtime(value))
        except OSError:
            self._disconnect_device(
                status_key="status_device_lost",
                name=self._last_output_port or "?",
            )
            return
        except (ValueError, RuntimeError) as e:
            self._set_status(str(e))
            return
        if update_status:
            self._set_status(
                self._tr("status_transpose_sent", value=self._transpose_sld.value())
            )

    def _update_metronome_btn(self) -> None:
        if self._metronome_on is True:
            self._metronome_btn.setText(self._tr("btn_metronome_on"))
            self._metronome_btn.setStyleSheet(
                "QPushButton { background-color: #c0392b; color: white; font-weight: bold; }"
                "QPushButton:hover { background-color: #e74c3c; }"
                "QPushButton:pressed { background-color: #922b21; }"
            )
        else:
            self._metronome_btn.setText(self._tr("btn_metronome_off"))
            self._metronome_btn.setStyleSheet("")

    def _request_piano_state(self) -> None:
        """Envía RQ1 al piano para leer master volume, tempo y estado metrónomo."""
        if not self._midi.is_open:
            return
        try:
            self._midi.send(midix.master_volume_read())
            self._midi.send(midix.metronome_read_tempo())
            self._midi.send(midix.metronome_read_status())
        except OSError:
            self._disconnect_device(
                status_key="status_device_lost",
                name=self._last_output_port or "?",
            )

    def _handle_dt1(self, addr: tuple[int, int, int, int], data: tuple[int, ...]) -> None:
        """Procesa respuestas DT1 del piano y actualiza la UI."""
        # Master Volume: 01 00 02 13, 1 byte, 0-127
        if addr == (0x01, 0x00, 0x02, 0x13) and data:
            # Ignorar DT1 del piano si hemos enviado recientemente: el piano responde
            # con su valor previo (ó confirmación) y sobreescribiría el slider.
            if time.monotonic() - self._master_vol_sent_at < MASTER_VOL_IGNORE_DT1_S:
                return
            self._suppress_slider_midi = True
            try:
                self._master_sld.blockSignals(True)
                self._master_sld.setValue(data[0])
                self._master_sld.blockSignals(False)
                self._master_lbl.setText(str(data[0]))
            finally:
                self._suppress_slider_midi = False
            return
        # Sequencer Tempo RO: 01 00 01 08, 2 bytes, value = b0*128 + b1
        if addr == (0x01, 0x00, 0x01, 0x08) and len(data) >= 2:
            bpm = data[0] * 128 + data[1]
            if TEMPO_MIN <= bpm <= TEMPO_MAX:
                self._set_tempo_ui(bpm)
            return
        # Metronome Status: 01 00 01 0F, 1 byte, 0=off 1=on
        if addr == (0x01, 0x00, 0x01, 0x0F) and data:
            self._metronome_on = bool(data[0])
            self._update_metronome_btn()
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
            self._midi.send(midix.metronome_set_tempo(self._tempo_sld.value()))
        except OSError:
            self._disconnect_device(
                status_key="status_device_lost",
                name=self._last_output_port or "?",
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
            self._midi.send(midix.metronome_toggle())
        except OSError:
            self._disconnect_device(
                status_key="status_device_lost",
                name=self._last_output_port or "?",
            )
            return
        except (ValueError, RuntimeError) as e:
            self._set_status(str(e))
            return
        # Actualización optimista del estado (el piano confirmará vía DT1 si hay entrada MIDI).
        # Si el estado era desconocido, asumimos que el metrónomo estaba apagado → pasa a encendido.
        self._metronome_on = not self._metronome_on if self._metronome_on is not None else True
        self._update_metronome_btn()
        self._set_status(self._tr("status_metronome_probe_sent"))

    def _tone_from_combo(self) -> Tone | None:
        idx = self._tone_combo.currentIndex()
        if idx < 0:
            return None
        data = self._tone_combo.itemData(idx)
        return data if isinstance(data, Tone) else None

    def _on_tone_combo_index_changed(self, index: int) -> None:
        if self._tone_combo_populating or self._syncing_tone_widgets or index < 0:
            return
        data = self._tone_combo.itemData(index)
        if not isinstance(data, Tone):
            return
        self._apply_tone(data)

    def _apply_tone(self, tone: Tone) -> None:
        if self._midi.is_open:
            self._send_bank_program(
                tone.bank_msb,
                tone.bank_lsb,
                tone.program_doc,
                tone_name=tone.name,
                latch_after_program=False,
                update_status=True,
            )
        else:
            self._set_status(self._tr("status_preset_offline", name=tone.name))

    def _send_bank_program(
        self,
        bank_msb: int,
        bank_lsb: int,
        program_doc: int,
        *,
        tone_name: str | None = None,
        silent_if_disconnected: bool = False,
        latch_after_program: bool = True,
        update_status: bool = True,
    ) -> None:
        if not self._midi.is_open:
            if not silent_if_disconnected:
                QMessageBox.information(
                    self,
                    self._tr("dlg_midi"),
                    self._tr("msg_connect_before_send"),
                )
            return
        self._mark_app_bank_tx()
        prog_midi = max(0, min(127, program_doc - 1))
        try:
            core, latch = midix.bank_select_program_and_latch_parts(
                MIDI_PART_CHANNEL,
                bank_msb,
                bank_lsb,
                prog_midi,
                latch_after_program=latch_after_program,
            )
            self._midi.send_all_spaced(core, gap_s=midix.DEFAULT_MESSAGE_GAP_S)
            if latch:
                time.sleep(midix.POST_PROGRAM_CHANGE_LATCH_DELAY_S)
                self._midi.send_all_spaced(latch, gap_s=midix.DEFAULT_MESSAGE_GAP_S)
        except OSError:
            self._disconnect_device(
                status_key="status_device_lost",
                name=self._last_output_port or "?",
            )
            return
        except (ValueError, RuntimeError) as e:
            QMessageBox.warning(self, self._tr("dlg_midi"), str(e))
            return
        if update_status:
            prefix = f"«{tone_name}»: " if tone_name else ""
            latch_note = (
                self._tr("latch_suffix") if latch_after_program and latch else ""
            )
            self._set_status(
                self._tr(
                    "status_bank_line",
                    prefix=prefix,
                    msb=bank_msb,
                    lsb=bank_lsb,
                    pdoc=program_doc,
                    pmidi=prog_midi,
                    latch=latch_note,
                )
            )

    def _on_sustain(self, on: bool) -> None:
        self._send_cc(64, 127 if on else 0)

    def _send_master_volume(self) -> None:
        if not self._midi.is_open:
            return
        value = self._master_sld.value()
        try:
            self._master_vol_sent_at = time.monotonic()
            self._midi.send(midix.master_volume_set(value))
            self._set_status(self._tr("status_master_volume_sent", value=value))
        except OSError:
            self._disconnect_device(
                status_key="status_device_lost",
                name=self._last_output_port or "?",
            )
        except (ValueError, RuntimeError) as e:
            self._set_status(str(e))
