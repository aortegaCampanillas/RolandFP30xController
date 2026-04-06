# Roland FP-30X Controller

A **desktop application** for **macOS** and **Windows** that lets you **control your Roland FP-30X digital piano from your computer** over standard **USB MIDI**. Adjust sounds, layers, metronome, tuning, and deep piano parameters from a single window—without reaching for the instrument’s panel for every change.

> **Disclaimer:** This is an **independent, open-source project**. It is **not** affiliated with, endorsed by, or sponsored by **Roland Corporation**. *Roland* and *FP-30X* are trademarks of their respective owners. If you publish this app in a store, verify naming and trademark use with qualified counsel and comply with each store’s policies.

---

## Why use it?

- **Full-screen comfort:** Edit parameters on a large monitor with mouse, trackpad, or keyboard.
- **Cross-platform:** Same workflow on **Mac** and **Windows** (see [Requirements](#requirements)).
- **MIDI-native:** Uses the same class of messages as the official documentation (SysEx, RPN/CC where applicable)—no replacement for the Roland Piano App on mobile; this targets **desktop** users who want a **native PC/Mac controller**.

---

## Requirements

| Item | Notes |
|------|--------|
| **OS** | macOS 10.15+ or Windows 10/11 (64-bit) |
| **Python** | 3.11 or newer |
| **FP-30X** | Connected via **USB**, MIDI driver installed (OS usually provides this) |
| **MIDI** | The piano must appear as a MIDI input/output device to the OS |

**Dependencies (see `pyproject.toml`):** PySide6 (Qt UI), mido, python-rtmidi. On macOS, **pyobjc-framework-Cocoa** is used optionally for a correct **Dock / app switcher icon** when running from Python.

---

## Installation (from source)

```bash
git clone <your-repo-url>
cd RolandFP30xController
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

Run the app:

```bash
roland-fp30x
# or
python -m roland_fp30x_controller
```

Optional verbose MIDI trace (stderr):

```bash
python -m roland_fp30x_controller --verbose
```

Optional debug UI helpers (shows the **Read Piano Values** button):

```bash
python -m roland_fp30x_controller /debug
```

---

## Quick start

1. Connect the **FP-30X** with USB and power it on.
2. Launch the app and choose the piano under **Device** (MIDI output). Use **Connect**.
3. If MIDI **input** opens successfully, the app can **sync tones and some state** from the instrument.
4. Explore the tabs below. **Piano Designer** and **Note voicing** are marked **(Beta)** and apply only under the conditions described in-app (e.g. Single mode, compatible piano tones).

---

## Features (by tab)

### Connection & language

- **MIDI device list** with **Refresh**, **Connect** / **Disconnect**.
- Optional **MIDI input** for reading state from the piano (tone, transpose, etc.).
- **English** and **Spanish** UI.
- **Status line** for connection, errors, and operation feedback.
- **`--verbose`** mode to log MIDI traffic for troubleshooting.

### Piano Settings

- **Master volume** (SysEx; keeps the panel LEDs in sync with the instrument where supported).
- **Master tuning** (fine pitch).
- **Key Touch** (Fix / Light / Medium / Heavy).
- **Brilliance**.
- **Transpose** (Universal MIDI Master Coarse Tuning).
- **Ambience depth**.
- **Metronome** quick **Start / Stop** (probe/toggle) from the header area.
- **Reset to defaults** (local UI + send to piano when connected).

### Tones

- **Keyboard modes:** **Single**, **Split**, **Dual**, **Twin**.
- **Tone selection** by **category** and **preset** (catalog aligned with FP-30X tone map / GM2-style banks).
- **Split:** left/right tones, **balance**, **split point**, **octave shifts** per side.
- **Dual:** two tones, **balance**, **shifts** per tone.
- **Twin:** tone + **Pair / Individual** mode.
- Sending tones uses Roland **DT1**-style encoding for mode-appropriate SysEx.

### Metronome

- **BPM** (tempo).
- **Volume**.
- **Tone** (e.g. Click, Electronic, Japanese, English).
- **Rhythm pattern** (8th, triplet, 16th, etc.).
- **Beat / time signature** grid matching FP-30X metronome presets.
- **Start** / **Stop**.

### Piano Designer (Beta)

- **Cabinet:** lid position.
- **String / Damper / Key Off resonance** levels.
- **Temperament** and **temperament key** (multiple historical temperaments).
- **Save to Piano** to persist settings on the instrument (where supported).
- First-time **guidance dialog** when entering Designer-related tabs if mode/tones are not compatible.

### Note voicing (Beta)

- Per-key editing across the **88 keys** (MIDI note range).
- **Single note tuning** (fine, in tenths of a cent in the UI logic).
- **Single note character**.
- Debounced sends to avoid MIDI flooding while dragging sliders.
- Persisting to hardware is done via **Save to Piano** on the **Piano Designer** tab, as noted in the in-app hint.

---

## Technical reference

Authoritative MIDI behavior is documented in:

- `docs/FP-30X_MIDI_Imple_eng01_W.pdf` — official **FP-30X MIDI Implementation** (primary spec).
- `docs/midi_reference.md` — consolidated **SysEx address map** and notes (includes reverse-engineered context from Roland Piano App 1.5.9 where applicable).

Application architecture (see `CLAUDE.md`):

- **`midi/`** — Pure Python MIDI: messages, ports, parsers, tone catalog.
- **`ui/`** — PySide6 widgets, i18n, MIDI input worker.

---

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check src
```

---

## Store listing copy (draft)

Use the blocks below as a starting point. **Replace** placeholders (`[…]`), add your **privacy policy URL**, **support email**, and **screenshots**. Review **trademark** and **minimum age** requirements before submission.

---

### Microsoft Store (Windows)

**Suggested product name (check trademark rules):**  
`FP-30X MIDI Controller` *or* `[YourBrand] for FP-30X`

**Short description (≤ 500 characters recommended):**  
Control your Roland FP-30X digital piano from Windows: choose tones, layers, metronome, tuning, ambience, and advanced Piano Designer options over USB MIDI—comfortable full-screen editing without relying on the small onboard display.

**Long description:**  
Roland FP-30X Controller is a desktop companion for musicians who use an FP-30X connected to a PC. Pick MIDI input and output, then adjust:

- Piano settings: master volume and tuning, key touch, brilliance, transpose, ambience  
- Tones: Single, Split, Dual, and Twin modes with category-based preset selection, balances, split point, and octave shifts  
- Metronome: tempo, volume, click type, rhythm pattern, and time signature  
- Piano Designer (Beta): cabinet lid, string/damper/key-off resonance, temperament and key, save to instrument  
- Note voicing (Beta): per-key tuning and character  

The app speaks standard USB MIDI. An optional verbose mode helps diagnose connection issues. English and Spanish interface.

**Search keywords (examples):**  
MIDI, FP-30X, Roland piano, digital piano, metronome, transpose, USB MIDI, music production, keyboard

**Capabilities / notes for submission:**  
- Declares use of **MIDI devices** (USB).  
- No account required unless you add cloud features later.  
- Add **Privacy policy** URL (even if you only process data locally).

**What’s new (template):**  
Initial release on Microsoft Store. [List fixes after updates.]

---

### Apple Mac App Store (macOS)

**Name (30 characters max for display—verify in App Store Connect):**  
e.g. `FP-30X Controller`

**Subtitle (30 characters max):**  
`Desktop MIDI for FP-30X`

**Promotional text (170 characters max, editable without review):**  
Full-screen control of your FP-30X: tones, layers, metronome, tuning, and Piano Designer over USB MIDI. English & Spanish.

**Description (up to 4000 characters):**  
Roland FP-30X Controller brings FP-30X editing to your Mac. Connect the piano via USB, select it as your MIDI device, and manage:

**Piano settings**  
Master volume and fine tuning, key touch response, brilliance, transpose, and ambience depth—plus quick metronome start/stop.

**Tones**  
Switch between Single, Split, Dual, and Twin. Browse presets by category (piano, E.piano, organ, strings, pads, synth, drums, GM2, and more). Adjust balances, split point, and octave shifts as modes require.

**Metronome**  
Set BPM, volume, click character, subdivision pattern, and beat/time signature from a clear grid.

**Piano Designer (Beta)**  
Shape cabinet lid, resonances, temperament and root key. Save your setup back to the piano when supported.

**Note voicing (Beta)**  
Tweak tuning and character per key across the keyboard.

The interface is available in **English** and **Spanish**. Optional MIDI logging helps support and power users.

**Keywords (100 characters total, comma-separated, no spaces after commas in App Store Connect):**  
midi,piano,fp30x,keyboard,metronome,transpose,digitalpiano,usb,roland,music

**Support URL:**  
`https://[your-domain]/support`

**Marketing URL (optional):**  
`https://[your-domain]/`

**Privacy policy URL:**  
`https://[your-domain]/privacy`

**What’s to Test (for App Review):**  
1. Connect Roland FP-30X via USB.  
2. Grant no special permissions unless future versions add microphone, files, or network.  
3. Select MIDI port and Connect; adjust a slider and confirm the piano responds.  
4. Note: Piano Designer / Note voicing require compatible mode (Single + supported tones)—dialog explains this.

**Age rating:** Typically **4+** if no user-generated content, no web browsing, and no social features—confirm with Apple’s questionnaire.

---

## License and third-party components

- **Project code:** [LICENSE](LICENSE) (**MIT**).
- **Bundled libraries (Qt/PySide6, mido, etc.):** [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md), including **LGPL-3.0** notes for Qt/PySide6 when you distribute binaries.
- **Store / frozen builds:** see [docs/packaging_store.md](docs/packaging_store.md).
