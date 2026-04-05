from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import mido

from roland_fp30x_controller.midi import messages as midix
from roland_fp30x_controller.midi.bank_program_parser import BankProgramParser
from roland_fp30x_controller.midi.rpn_parser import (
    RpnParser,
    parse_master_coarse_tuning_sysex,
)
from roland_fp30x_controller.midi.tone_catalog import TONE_PRESETS

mido.set_backend("mido.backends.rtmidi")


def _format_raw(msg: mido.Message) -> str:
    try:
        return " ".join(f"{b:02X}" for b in msg.bytes())
    except (AttributeError, ValueError, TypeError):
        return "?"


def _guess_ports(name_hint: str | None) -> tuple[str | None, str | None]:
    ins = list(mido.get_input_names())
    outs = list(mido.get_output_names())
    if name_hint:
        in_name = next((n for n in ins if name_hint.lower() in n.lower()), None)
        out_name = next((n for n in outs if name_hint.lower() in n.lower()), None)
        return in_name, out_name
    common = next((n for n in ins if n in outs), None)
    return common, common


def _identity_request() -> mido.Message:
    # Universal Non-realtime Identity Request. Broadcast device id.
    return mido.Message("sysex", data=(0x7E, 0x7F, 0x06, 0x01))


def _probe_messages(profile: str) -> list[tuple[str, mido.Message]]:
    if profile == "identity":
        return [("identity_request", _identity_request())]
    if profile == "documented":
        return [
            ("identity_request", _identity_request()),
            ("master_volume_100", midix.master_volume_realtime(100)),
            ("master_fine_tuning_440hz", mido.Message("sysex", data=(0x7F, 0x7F, 0x04, 0x03, 0x00, 0x40))),
            ("master_coarse_tuning_0", midix.master_coarse_tuning_realtime(0)),
            ("reverb_time_40", midix.gm2_global_reverb_parameter(1, 40)),
        ]
    msg = f"Perfil de probe desconocido: {profile}"
    raise ValueError(msg)


def _annotate(
    msg: mido.Message,
    bank_parser: BankProgramParser,
    rpn_parser: RpnParser,
) -> list[str]:
    notes: list[str] = []
    if msg.type == "sysex":
        coarse = parse_master_coarse_tuning_sysex(msg)
        if coarse is not None:
            notes.append(f"master_coarse_tuning={coarse:+d}")
        data = tuple(msg.data)
        if data == (0x7E, 0x10, 0x06, 0x02, 0x41, 0x19, 0x03, 0x00, 0x00, 0x1C, 0x01, 0x00, 0x00):
            notes.append("identity_reply=Roland FP-30X")
    coarse_rpn = rpn_parser.feed_coarse_tuning(msg)
    if coarse_rpn is not None:
        notes.append(f"rpn_coarse_tuning={coarse_rpn:+d}")
    patch = bank_parser.feed(msg)
    if patch is not None:
        msb, lsb, pdoc = patch
        notes.append(f"bank_program={msb}/{lsb}/{pdoc}")
        tone = next(
            (
                t.name
                for t in TONE_PRESETS
                if t.bank_msb == msb and t.bank_lsb == lsb and t.program_doc == pdoc
            ),
            None,
        )
        if tone is not None:
            notes.append(f"tone={tone}")
    return notes


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Captura tráfico MIDI del piano para analizar qué valores transmite.",
    )
    parser.add_argument(
        "--port",
        help="Subcadena del nombre del puerto MIDI a usar. Si se omite, intenta autodetectar.",
    )
    parser.add_argument(
        "--seconds",
        type=float,
        default=0.0,
        help="Duración máxima de captura. 0 = hasta Ctrl+C.",
    )
    parser.add_argument(
        "--no-identity-request",
        action="store_true",
        help="No envía Universal Identity Request al arrancar.",
    )
    parser.add_argument(
        "--probe",
        choices=("identity", "documented"),
        help=(
            "Envía una batería de SysEx y registra respuestas. "
            "'identity' es seguro; 'documented' usa mensajes soportados por el manual "
            "y puede modificar temporalmente parámetros."
        ),
    )
    parser.add_argument(
        "--probe-gap",
        type=float,
        default=0.25,
        help="Separación entre mensajes de probe, en segundos.",
    )
    parser.add_argument(
        "--jsonl",
        type=Path,
        help="Ruta de salida opcional en formato JSONL para analizar luego.",
    )
    args = parser.parse_args()

    in_name, out_name = _guess_ports(args.port)
    if in_name is None:
        print("No se encontró puerto MIDI de entrada compatible.", file=sys.stderr)
        print("Entradas disponibles:", file=sys.stderr)
        for name in mido.get_input_names():
            print(f"  - {name}", file=sys.stderr)
        return 1

    out_port = None
    if out_name is not None:
        out_port = mido.open_output(out_name)

    bank_parser = BankProgramParser((1, 4))
    rpn_parser = RpnParser((1, 4))
    jsonl = args.jsonl.open("w", encoding="utf-8") if args.jsonl else None

    print(f"Entrada MIDI: {in_name}")
    print(f"Salida MIDI: {out_name or '(ninguna)'}")
    print("Mueve controles en el piano y observa el log. Ctrl+C para terminar.")

    start = time.monotonic()

    def _log(direction: str, msg: mido.Message, *, notes: list[str] | None = None) -> None:
        ts = time.monotonic() - start
        note_suffix = f" | note={'; '.join(notes)}" if notes else ""
        print(f"[{ts:8.3f}] [{direction}] {msg} | {_format_raw(msg)}{note_suffix}")
        if jsonl is not None:
            json.dump(
                {
                    "t": round(ts, 3),
                    "direction": direction.lower(),
                    "message": str(msg),
                    "raw": _format_raw(msg),
                    "notes": notes or [],
                },
                jsonl,
                ensure_ascii=True,
            )
            jsonl.write("\n")
            jsonl.flush()

    try:
        with mido.open_input(in_name) as in_port:
            if out_port is not None:
                if args.probe:
                    for note, msg in _probe_messages(args.probe):
                        out_port.send(msg)
                        _log("OUT", msg, notes=[note])
                        time.sleep(max(0.0, args.probe_gap))
                elif not args.no_identity_request:
                    req = _identity_request()
                    out_port.send(req)
                    _log("OUT", req, notes=["identity_request"])

            while True:
                for msg in in_port.iter_pending():
                    notes = _annotate(msg, bank_parser, rpn_parser)
                    _log("IN ", msg, notes=notes)
                if args.seconds > 0 and time.monotonic() - start >= args.seconds:
                    break
                time.sleep(0.015)
    except KeyboardInterrupt:
        pass
    finally:
        if out_port is not None:
            out_port.close()
        if jsonl is not None:
            jsonl.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
