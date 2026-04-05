from __future__ import annotations

import argparse
import time

import mido

mido.set_backend("mido.backends.rtmidi")

ROLAND_ID = 0x41
DEVICE_ID = 0x10
MODEL_ID = (0x00, 0x00, 0x00, 0x28)
CMD_RQ1 = 0x11
CMD_DT1 = 0x12


def roland_checksum(values: list[int]) -> int:
    return (128 - (sum(values) % 128)) % 128


def roland_sysex(command: int, address: list[int], data: list[int]) -> mido.Message:
    body = [ROLAND_ID, DEVICE_ID, *MODEL_ID, command, *address, *data]
    checksum = roland_checksum([*address, *data])
    return mido.Message("sysex", data=tuple([*body, checksum]))


def rq1(address: list[int], size: list[int]) -> mido.Message:
    return roland_sysex(CMD_RQ1, address, size)


def dt1(address: list[int], data: list[int]) -> mido.Message:
    return roland_sysex(CMD_DT1, address, data)


def guess_port(name_hint: str | None) -> str | None:
    outs = list(mido.get_output_names())
    if name_hint:
        return next((n for n in outs if name_hint.lower() in n.lower()), None)
    return next(iter(outs), None)


def fmt(msg: mido.Message) -> str:
    return " ".join(f"{b:02X}" for b in msg.bytes())


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prueba SysEx Roland para validar la dirección del metrónomo.",
    )
    parser.add_argument("--port", help="Subcadena del nombre del puerto MIDI.")
    parser.add_argument(
        "--action",
        choices=("read", "on", "off"),
        default="read",
        help="read consulta la dirección; on/off escriben 01/00.",
    )
    args = parser.parse_args()

    port_name = guess_port(args.port)
    if port_name is None:
        print("No se encontró puerto MIDI de salida.")
        return 1

    addr = [0x01, 0x00, 0x03, 0x06]
    if args.action == "read":
        msg = rq1(addr, [0x00, 0x00, 0x00, 0x01])
    elif args.action == "on":
        msg = dt1(addr, [0x01])
    else:
        msg = dt1(addr, [0x00])

    print(f"Salida MIDI: {port_name}")
    print(f"Enviando: {fmt(msg)}")
    with mido.open_output(port_name) as out_port:
        out_port.send(msg)
        time.sleep(0.2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
