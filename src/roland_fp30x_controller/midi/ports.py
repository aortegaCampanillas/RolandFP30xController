from __future__ import annotations

import mido

mido.set_backend("mido.backends.rtmidi")


def list_input_names() -> list[str]:
    return list(mido.get_input_names())


def list_output_names() -> list[str]:
    return list(mido.get_output_names())
