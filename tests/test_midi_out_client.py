from __future__ import annotations

import mido

from roland_fp30x_controller.midi.client import MidiOutClient


def test_trace_send_runs_before_hardware_send(monkeypatch) -> None:
    hardware: list[mido.Message] = []

    class FakePort:
        def send(self, m: mido.Message) -> None:
            hardware.append(m)

        def close(self) -> None:
            pass

    monkeypatch.setattr(mido, "open_output", lambda _name: FakePort())
    traced: list[mido.Message] = []
    c = MidiOutClient(trace_send=traced.append)
    c.open("dummy")
    msg = mido.Message("control_change", channel=0, control=7, value=100)
    c.send(msg)
    assert traced == [msg]
    assert hardware == [msg]


def test_close_clears_port_when_underlying_close_fails(monkeypatch) -> None:
    class BadClosePort:
        def send(self, _m: mido.Message) -> None:
            pass

        def close(self) -> None:
            raise OSError("port gone")

    monkeypatch.setattr(mido, "open_output", lambda _name: BadClosePort())
    c = MidiOutClient()
    c.open("dummy")
    assert c.is_open
    c.close()
    assert not c.is_open
