from __future__ import annotations

import sys
import time

import mido
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
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
from roland_fp30x_controller.midi.tone_catalog import TONE_PRESETS, Tone
from roland_fp30x_controller.ui.i18n import Lang, tr
from roland_fp30x_controller.ui.midi_in_worker import MidiInWorker

# Valores iniciales / «Restablecer». Parte MIDI fija en canal 4 (FP-30X + SMF Internal, Roland).
DEFAULT_PRESET_INDEX = 0
MIDI_PART_CHANNEL = 4
# Mezcla: valores iniciales del manual FP-30X (receive).
DEFAULT_VOLUME = 100
DEFAULT_EXPRESSION = 127
DEFAULT_PAN = 64
DEFAULT_MODULATION = 0
DEFAULT_REVERB = 40
DEFAULT_CHORUS = 0
DEFAULT_MASTER_VOLUME = 127

# Retardo tras el último movimiento del slider antes de enviar CC (teclado y ratón).
MIX_CC_DEBOUNCE_MS = 55
MASTER_VOL_DEBOUNCE_MS = 55
# Tras enviar banco/programa desde la app, ignorar eco del piano (segundos).
PIANO_PATCH_IGNORE_S = 0.55


def _cc_slider(
    label: str, default: int, *, tracking: bool = False
) -> tuple[QLabel, QSlider, QLabel]:
    name = QLabel(label)
    slider = QSlider(Qt.Orientation.Horizontal)
    slider.setRange(0, 127)
    slider.setValue(default)
    slider.setTracking(tracking)
    val = QLabel(str(default))
    val.setMinimumWidth(28)
    slider.valueChanged.connect(lambda v: val.setText(str(v)))
    return name, slider, val


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
        self._ignore_piano_patch_until = 0.0
        self._tone_combo_populating = False
        self._syncing_tone_widgets = False
        self._suppress_mix_slider_midi = False
        self._cc_debounce_timers: dict[int, QTimer] = {}
        self._master_vol_debounce_timer = QTimer(self)
        self._master_vol_debounce_timer.setSingleShot(True)
        self._master_vol_debounce_timer.timeout.connect(lambda: self._send_master_volume())

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
        lower_layout.addWidget(self._build_mix_group())
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
        self._master_sld.setToolTip(self._tr("tooltip_master_volume"))
        self._group_mix.setTitle(self._tr("group_mix"))
        self._vol_lbl.setText(self._tr("mix_volume"))
        self._expr_lbl.setText(self._tr("mix_expression"))
        self._pan_lbl.setText(self._tr("mix_pan"))
        self._mod_lbl.setText(self._tr("mix_modulation"))
        self._rev_lbl.setText(self._tr("mix_reverb"))
        self._cho_lbl.setText(self._tr("mix_chorus"))
        self._rev_sld.setToolTip(self._tr("tooltip_reverb"))
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

        self._tone_combo = QComboBox()
        self._tone_combo.setMaxVisibleItems(30)
        self._tone_combo_populating = True
        try:
            for t in TONE_PRESETS:
                self._tone_combo.addItem(t.name, t)
        finally:
            self._tone_combo_populating = False
        self._tone_combo.currentIndexChanged.connect(self._on_tone_combo_index_changed)
        v.addWidget(self._tone_combo)
        return self._group_main

    def _build_mix_group(self) -> QWidget:
        self._group_mix = QGroupBox()
        g = QFormLayout(self._group_mix)
        self._vol_lbl, self._vol_sld, self._vol_val = _cc_slider(
            self._tr("mix_volume"), DEFAULT_VOLUME, tracking=True
        )
        self._expr_lbl, self._expr_sld, self._expr_val = _cc_slider(
            self._tr("mix_expression"), DEFAULT_EXPRESSION, tracking=True
        )
        self._pan_lbl, self._pan_sld, self._pan_val = _cc_slider(
            self._tr("mix_pan"), DEFAULT_PAN, tracking=True
        )
        self._mod_lbl, self._mod_sld, self._mod_val = _cc_slider(
            self._tr("mix_modulation"), DEFAULT_MODULATION, tracking=True
        )
        self._rev_lbl, self._rev_sld, self._rev_val = _cc_slider(
            self._tr("mix_reverb"), DEFAULT_REVERB, tracking=True
        )
        self._cho_lbl, self._cho_sld, self._cho_val = _cc_slider(
            self._tr("mix_chorus"), DEFAULT_CHORUS, tracking=True
        )

        for lbl, sld, val in (
            (self._vol_lbl, self._vol_sld, self._vol_val),
            (self._expr_lbl, self._expr_sld, self._expr_val),
            (self._pan_lbl, self._pan_sld, self._pan_val),
            (self._mod_lbl, self._mod_sld, self._mod_val),
            (self._rev_lbl, self._rev_sld, self._rev_val),
            (self._cho_lbl, self._cho_sld, self._cho_val),
        ):
            row = QHBoxLayout()
            row.addWidget(lbl)
            row.addWidget(sld, stretch=1)
            row.addWidget(val)
            w = QWidget()
            w.setLayout(row)
            g.addRow(w)

        self._wire_mix_cc_slider(self._vol_sld, 7)
        self._wire_mix_cc_slider(self._expr_sld, 11)
        self._wire_mix_cc_slider(self._pan_sld, 10)
        self._wire_mix_cc_slider(self._mod_sld, 1)
        self._wire_mix_cc_slider(self._rev_sld, 91)
        self._wire_mix_cc_slider(self._cho_sld, 93)
        return self._group_mix

    def _build_sustain(self) -> QWidget:
        self._group_pedal = QGroupBox()
        h = QHBoxLayout(self._group_pedal)
        self._sustain = QCheckBox()
        self._sustain.toggled.connect(self._on_sustain)
        h.addWidget(self._sustain)
        h.addStretch(1)
        return self._group_pedal

    def closeEvent(self, event: QCloseEvent) -> None:
        self._cancel_mix_and_master_debounce()
        self._stop_midi_in_worker()
        self._midi.close()
        super().closeEvent(event)

    def _stop_midi_in_worker(self) -> None:
        if self._midi_in_worker is None:
            return
        try:
            self._midi_in_worker.message_received.disconnect(self._on_midi_in_message)
        except (RuntimeError, TypeError):
            pass
        self._midi_in_worker.stop_safely()
        self._midi_in_worker.wait(5000)
        self._midi_in_worker = None

    def _mark_app_bank_tx(self) -> None:
        self._ignore_piano_patch_until = time.monotonic() + PIANO_PATCH_IGNORE_S

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
            self._cancel_mix_and_master_debounce()
            self._stop_midi_in_worker()
            self._midi.close()
            self._last_output_port = None
            self._last_input_port = None
            self._update_connect_button_text()
            self._lower_panels.setEnabled(False)
            self._set_status(self._tr("status_disconnected"))
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
        self._update_connect_button_text()
        self._lower_panels.setEnabled(True)
        self._mark_app_bank_tx()
        self._reapply_full_part_to_device(
            latch_after_program=False,
            update_status=False,
        )
        input_names = list_input_names()
        in_name = name if name in input_names else ""
        if in_name:
            try:
                worker = MidiInWorker(in_name)
                worker.message_received.connect(self._on_midi_in_message)
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
        else:
            self._set_status(self._tr("status_connected", name=name))

    def _set_status(self, text: str) -> None:
        self._status.setText(text)

    def _reset_defaults(self) -> None:
        self._cancel_mix_and_master_debounce()
        self._suppress_mix_slider_midi = True
        try:
            self._syncing_tone_widgets = True
            try:
                self._tone_combo.blockSignals(True)
                self._tone_combo.setCurrentIndex(DEFAULT_PRESET_INDEX)
                self._tone_combo.blockSignals(False)
            finally:
                self._syncing_tone_widgets = False

            self._vol_sld.setValue(DEFAULT_VOLUME)
            self._expr_sld.setValue(DEFAULT_EXPRESSION)
            self._pan_sld.setValue(DEFAULT_PAN)
            self._mod_sld.setValue(DEFAULT_MODULATION)
            self._rev_sld.setValue(DEFAULT_REVERB)
            self._cho_sld.setValue(DEFAULT_CHORUS)

            self._sustain.blockSignals(True)
            self._sustain.setChecked(False)
            self._sustain.blockSignals(False)

            self._master_sld.setValue(DEFAULT_MASTER_VOLUME)
        finally:
            self._suppress_mix_slider_midi = False

        if not self._midi.is_open:
            self._set_status(self._tr("status_defaults_offline"))
            return

        self._reapply_full_part_to_device()
        self._set_status(self._tr("status_defaults_sent"))

    def _cancel_mix_and_master_debounce(self) -> None:
        for t in self._cc_debounce_timers.values():
            t.stop()
        self._master_vol_debounce_timer.stop()

    def _schedule_mix_cc(self, control: int, slider: QSlider) -> None:
        if self._suppress_mix_slider_midi:
            return
        timer = self._cc_debounce_timers.get(control)
        if timer is None:
            timer = QTimer(self)
            timer.setSingleShot(True)

            def _flush() -> None:
                self._flush_debounced_mix_cc(control, slider)

            timer.timeout.connect(_flush)
            self._cc_debounce_timers[control] = timer
        timer.stop()
        timer.start(MIX_CC_DEBOUNCE_MS)

    def _flush_debounced_mix_cc(self, control: int, slider: QSlider) -> None:
        if self._suppress_mix_slider_midi:
            return
        self._send_cc(control, slider.value())

    def _flush_mix_cc_immediate(self, control: int, slider: QSlider) -> None:
        if self._suppress_mix_slider_midi:
            return
        timer = self._cc_debounce_timers.get(control)
        if timer is not None:
            timer.stop()
        self._flush_debounced_mix_cc(control, slider)

    def _wire_mix_cc_slider(self, slider: QSlider, control: int) -> None:
        slider.valueChanged.connect(
            lambda _v, c=control, s=slider: self._schedule_mix_cc(c, s)
        )
        slider.sliderReleased.connect(
            lambda c=control, s=slider: self._flush_mix_cc_immediate(c, s)
        )

    def _schedule_master_volume_debounced(self, _value: int = 0) -> None:
        if self._suppress_mix_slider_midi:
            return
        self._master_vol_debounce_timer.stop()
        self._master_vol_debounce_timer.start(MASTER_VOL_DEBOUNCE_MS)

    def _on_master_volume_slider_released(self) -> None:
        if self._suppress_mix_slider_midi:
            return
        self._master_vol_debounce_timer.stop()
        self._send_master_volume()

    def _flush_mix_sliders_to_device(self) -> None:
        if not self._midi.is_open:
            return
        self._send_cc(7, self._vol_sld.value())
        self._send_cc(11, self._expr_sld.value())
        self._send_cc(10, self._pan_sld.value())
        self._send_cc(1, self._mod_sld.value())
        self._send_cc(91, self._rev_sld.value())
        self._send_cc(93, self._cho_sld.value())

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
        self._flush_mix_sliders_to_device()
        self._flush_sustain_pedal_to_device()
        self._send_master_volume()
        if update_status:
            self._set_status(self._tr("status_full_reapply"))

    def _send_cc(self, control: int, value: int) -> None:
        if not self._midi.is_open:
            return
        try:
            self._midi.send(midix.control_change(MIDI_PART_CHANNEL, control, value))
            if control == 91 and value > 0:
                tail = min(127, max(value, 28))
                self._midi.send(midix.gm2_global_reverb_parameter(1, tail))
        except (ValueError, RuntimeError) as e:
            self._set_status(str(e))

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
        try:
            self._midi.send(midix.master_volume_realtime(self._master_sld.value()))
        except (ValueError, RuntimeError) as e:
            self._set_status(str(e))
