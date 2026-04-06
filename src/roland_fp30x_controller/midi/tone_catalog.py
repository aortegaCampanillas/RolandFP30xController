# Generado a partir de FP-30X MIDI Implementation secc. 4 Tone List / GM2.
# PC es el nº de programa en documentación Roland (1–128); en MIDI se envía PC-1 (0–127).
from __future__ import annotations

from typing import NamedTuple


class Tone(NamedTuple):
    name: str
    bank_msb: int
    bank_lsb: int
    program_doc: int  # 1–128 según manual

    @property
    def program_midi(self) -> int:
        return max(0, min(127, self.program_doc - 1))


TONE_PRESETS: list[Tone] = [
    Tone('Concert Piano', 0, 68, 1),
    Tone('Ballad Piano', 16, 67, 1),
    Tone('Mellow Piano', 4, 64, 1),
    Tone('Bright Piano', 8, 66, 2),
    Tone('Upright Piano', 16, 64, 1),
    Tone('Mellow Upright', 1, 65, 1),
    Tone('Bright Upright', 1, 66, 1),
    Tone('Rock Piano', 8, 64, 3),
    Tone('1976SuitCase', 8, 71, 5),
    Tone('Wurly 200', 25, 64, 5),
    Tone('Phase EP Mix', 8, 68, 5),
    Tone("80's FM EP", 0, 68, 6),
    Tone('Clav.', 121, 0, 8),
    Tone('Vibraphone', 121, 0, 12),
    Tone('Celesta', 121, 0, 9),
    Tone('B.Organ Slow', 1, 65, 19),
    Tone('Combo Jz.Org', 0, 70, 19),
    Tone('Ballad Organ', 0, 69, 19),
    Tone('Gospel Spin', 0, 71, 17),
    Tone('Full Stops', 0, 69, 17),
    Tone('Mellow Bars', 32, 68, 17),
    Tone('Lower Organ', 0, 66, 17),
    Tone('Light Organ', 32, 69, 17),
    Tone('Pipe Organ', 8, 70, 20),
    Tone("Nason Flt 8'", 16, 66, 20),
    Tone('ChurchOrgan1', 0, 66, 20),
    Tone('ChurchOrgan2', 8, 69, 20),
    Tone('Epic Strings', 1, 67, 49),
    Tone('Rich Strings', 0, 71, 50),
    Tone('SymphonicStr1', 1, 67, 50),
    Tone('SymphonicStr2', 1, 65, 50),
    Tone('Orchestra', 8, 66, 49),
    Tone('String Trio', 0, 64, 41),
    Tone('Harpiness', 0, 70, 47),
    Tone('OrchestraBrs', 1, 66, 61),
    Tone('Super SynPad', 1, 71, 90),
    Tone('Choir Aahs 1', 8, 71, 53),
    Tone('Choir Aahs 2', 8, 72, 53),
    Tone('D50 StackPad', 1, 64, 89),
    Tone('JP8 Strings', 0, 68, 51),
    Tone('Soft Pad', 0, 64, 90),
    Tone('Solina', 0, 66, 51),
    Tone('Super Saw', 8, 67, 82),
    Tone('Trancy Synth', 1, 65, 91),
    Tone('Flip Pad', 1, 64, 91),
    Tone('Jazz Scat', 0, 65, 55),
    Tone("Comp'd JBass", 0, 66, 34),
    Tone('Nylon-str.Gt', 121, 0, 25),
    Tone('Steel-str.Gt', 121, 0, 26),
    Tone('AcousticBass', 121, 0, 33),
    Tone('A.Bass+Cymbl', 0, 66, 33),
    Tone('Standard Set', 120, 0, 1),
    Tone('Room Set', 120, 0, 9),
    Tone('Power Set', 120, 0, 17),
    Tone('Electric Set', 120, 0, 25),
    Tone('Analog Set', 120, 0, 26),
    Tone('Jazz Set', 120, 0, 33),
    Tone('Brush Set', 120, 0, 41),
    Tone('Orchestra Set', 120, 0, 49),
    Tone('SFX Set', 120, 0, 57),
    Tone('Piano 1', 121, 0, 1),
    Tone('Piano 1w', 121, 1, 1),
    Tone('Piano 1d', 121, 2, 1),
    Tone('Piano 2', 121, 0, 2),
    Tone('Piano 2w', 121, 1, 2),
    Tone('Piano 3', 121, 0, 3),
    Tone('Piano 3w', 121, 1, 3),
    Tone('Honky-tonk', 121, 0, 4),
    Tone('Honky-tonk w', 121, 1, 4),
    Tone('E.Piano 1', 121, 0, 5),
    Tone('Detuned EP 1', 121, 1, 5),
    Tone('Vintage EP', 121, 2, 5),
    Tone("60's E.Piano", 121, 3, 5),
    Tone('E.Piano 2', 121, 0, 6),
    Tone('Detuned EP 2', 121, 1, 6),
    Tone('St.FM EP', 121, 2, 6),
    Tone('EP Legend', 121, 3, 6),
    Tone('EP Phaser', 121, 4, 6),
    Tone('Harpsi.', 121, 0, 7),
    Tone('Coupled Hps.', 121, 1, 7),
    Tone('Harpsi.w', 121, 2, 7),
    Tone('Harpsi.o', 121, 3, 7),
    Tone('Pulse Clav.', 121, 1, 8),
    Tone('Glockenspiel', 121, 0, 10),
    Tone('Music Box', 121, 0, 11),
    Tone('Vibraphone w', 121, 1, 12),
    Tone('Marimba', 121, 0, 13),
    Tone('Marimba w', 121, 1, 13),
    Tone('Xylophone', 121, 0, 14),
    Tone('TubularBells', 121, 0, 15),
    Tone('Church Bell', 121, 1, 15),
    Tone('Carillon', 121, 2, 15),
    Tone('Santur', 121, 0, 16),
    Tone('Organ 1', 121, 0, 17),
    Tone('TremoloOrgan', 121, 1, 17),
    Tone("60's Organ", 121, 2, 17),
    Tone('Organ 2', 121, 3, 17),
    Tone('Perc.Organ 1', 121, 0, 18),
    Tone('Chorus Organ', 121, 1, 18),
    Tone('Perc.Organ 2', 121, 2, 18),
    Tone('Rock Organ', 121, 0, 19),
    Tone('Church Org.1', 121, 0, 20),
    Tone('Church Org.2', 121, 1, 20),
    Tone('Church Org.3', 121, 2, 20),
    Tone('Reed Organ', 121, 0, 21),
    Tone('Puff Organ', 121, 1, 21),
    Tone('Accordion 1', 121, 0, 22),
    Tone('Accordion 2', 121, 1, 22),
    Tone('Harmonica', 121, 0, 23),
    Tone('Bandoneon', 121, 0, 24),
    Tone('Ukulele', 121, 1, 25),
    Tone('Nylon Gt o', 121, 2, 25),
    Tone('Nylon Gt 2', 121, 3, 25),
    Tone('12-str.Gt', 121, 1, 26),
    Tone('Mandolin', 121, 2, 26),
    Tone('Steel+Body', 121, 3, 26),
    Tone('Jazz Guitar', 121, 0, 27),
    Tone('Hawaiian Gt', 121, 1, 27),
    Tone('Clean Guitar', 121, 0, 28),
    Tone('Chorus Gt 1', 121, 1, 28),
    Tone('Mid Tone Gt', 121, 2, 28),
    Tone('Muted Guitar', 121, 0, 29),
    Tone('Funk Guitar1', 121, 1, 29),
    Tone('Funk Guitar2', 121, 2, 29),
    Tone('Chorus Gt 2', 121, 3, 29),
    Tone('Overdrive Gt', 121, 0, 30),
    Tone('Guitar Pinch', 121, 1, 30),
    Tone('DistortionGt', 121, 0, 31),
    Tone('Gt Feedback1', 121, 1, 31),
    Tone('Dist.Rhy Gt', 121, 2, 31),
    Tone('Gt Harmonics', 121, 0, 32),
    Tone('Gt Feedback2', 121, 1, 32),
    Tone('FingeredBass', 121, 0, 34),
    Tone('Finger Slap', 121, 1, 34),
    Tone('Picked Bass', 121, 0, 35),
    Tone('FretlessBass', 121, 0, 36),
    Tone('Slap Bass 1', 121, 0, 37),
    Tone('Slap Bass 2', 121, 0, 38),
    Tone('Synth Bass 1', 121, 0, 39),
    Tone('WarmSyn.Bass', 121, 1, 39),
    Tone('Synth Bass 3', 121, 2, 39),
    Tone('Clav.Bass', 121, 3, 39),
    Tone('Hammer Bass', 121, 4, 39),
    Tone('Synth Bass 2', 121, 0, 40),
    Tone('Synth Bass 4', 121, 1, 40),
    Tone('RubberSyn.Bs', 121, 2, 40),
    Tone('Attack Pulse', 121, 3, 40),
    Tone('Violin', 121, 0, 41),
    Tone('Slow Violin', 121, 1, 41),
    Tone('Viola', 121, 0, 42),
    Tone('Cello', 121, 0, 43),
    Tone('Contrabass', 121, 0, 44),
    Tone('Tremolo Str.', 121, 0, 45)
]

# ── Categorías ───────────────────────────────────────────────────────────────

CATEGORIES: list[str] = [
    "Piano", "E.Piano", "Organ", "Strings", "Pad", "Synth", "Other", "Drums", "GM2"
]

_CATEGORY_FOR: dict[str, str] = {
    # Piano
    'Concert Piano': 'Piano', 'Ballad Piano': 'Piano', 'Mellow Piano': 'Piano',
    'Bright Piano': 'Piano', 'Upright Piano': 'Piano', 'Mellow Upright': 'Piano',
    'Bright Upright': 'Piano', 'Rock Piano': 'Piano',
    # E.Piano
    '1976SuitCase': 'E.Piano', 'Wurly 200': 'E.Piano', 'Phase EP Mix': 'E.Piano',
    "80's FM EP": 'E.Piano', 'Clav.': 'E.Piano', 'Vibraphone': 'E.Piano', 'Celesta': 'E.Piano',
    # Organ
    'B.Organ Slow': 'Organ', 'Combo Jz.Org': 'Organ', 'Ballad Organ': 'Organ',
    'Gospel Spin': 'Organ', 'Full Stops': 'Organ', 'Mellow Bars': 'Organ',
    'Lower Organ': 'Organ', 'Light Organ': 'Organ', 'Pipe Organ': 'Organ',
    "Nason Flt 8'": 'Organ', 'ChurchOrgan1': 'Organ', 'ChurchOrgan2': 'Organ',
    'Accordion 1': 'Organ',
    # Strings
    'Epic Strings': 'Strings', 'Rich Strings': 'Strings', 'SymphonicStr1': 'Strings',
    'SymphonicStr2': 'Strings', 'Orchestra': 'Strings', 'String Trio': 'Strings',
    'Harpiness': 'Strings', 'OrchestraBrs': 'Strings',
    # Pad
    'Super SynPad': 'Pad', 'Choir Aahs 1': 'Pad', 'Choir Aahs 2': 'Pad',
    'D50 StackPad': 'Pad', 'JP8 Strings': 'Pad', 'Soft Pad': 'Pad', 'Solina': 'Pad',
    # Synth
    'Super Saw': 'Synth', 'Trancy Synth': 'Synth', 'Flip Pad': 'Synth',
    # Other (vocals, guitar, bass — no drums/GM2)
    'Jazz Scat': 'Other', "Comp'd JBass": 'Other', 'Nylon-str.Gt': 'Other',
    'Steel-str.Gt': 'Other', 'AcousticBass': 'Other', 'A.Bass+Cymbl': 'Other',
}


def category_of(tone: Tone) -> str:
    """Devuelve la categoría de un tono según banco MIDI o nombre."""
    explicit = _CATEGORY_FOR.get(tone.name)
    if explicit is not None:
        return explicit
    if tone.bank_msb == 120:
        return "Drums"
    if tone.bank_msb == 121:
        return "GM2"
    return "Other"


# Mapa ordenado: categoría → lista de tonos en ese orden
TONE_CATEGORIES: dict[str, list[Tone]] = {cat: [] for cat in CATEGORIES}
for _t in TONE_PRESETS:
    TONE_CATEGORIES[category_of(_t)].append(_t)


def tone_dt1_encoding(tone: Tone) -> tuple[int, int, int]:
    """Devuelve los 3 bytes internos Roland para toneForSingle/Split/Dual.

    Formato: [category_idx, num // 128, num % 128]
    donde num es el índice del tono dentro de su categoría.
    """
    cat = category_of(tone)
    cat_idx = CATEGORIES.index(cat)
    tones_in_cat = TONE_CATEGORIES[cat]
    num = tones_in_cat.index(tone) if tone in tones_in_cat else 0
    return (cat_idx, num // 128, num % 128)


def tone_from_dt1_bytes(category_idx: int, num_hi: int, num_lo: int) -> Tone | None:
    """Inverso de los 3 bytes DT1 del piano → tono del catálogo, o None si fuera de rango."""
    if not 0 <= category_idx < len(CATEGORIES):
        return None
    cat = CATEGORIES[category_idx]
    tones = TONE_CATEGORIES.get(cat, [])
    num = num_hi * 128 + num_lo
    if not 0 <= num < len(tones):
        return None
    return tones[num]
