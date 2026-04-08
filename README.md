# Roland FP-30X Controller

**Project page:** https://freemidichords.com/fp30x  
**Microsoft Store:** [Get PianoPilot for FP-30X](https://apps.microsoft.com/detail/9mtt67vb0g74?ocid=webpdpshare)

A **desktop application** for **macOS** and **Windows** that lets you **control your Roland FP-30X digital piano from your computer** over standard **USB MIDI** or **Bluetooth**. Adjust sounds, layers, metronome, tuning, and deep piano parameters from a single window—without reaching for the instrument’s panel for every change.

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

### Apple Mac App Store (macOS) — English

**Name (30 characters max for display—verify in App Store Connect):**  
e.g. `FP-30X Controller`

**Subtitle (30 characters max):**  
`Desktop MIDI for FP-30X`

**Promotional text (170 characters max, editable without review):**  
Control your Roland FP-30X from a desktop application.

**Description (up to 4000 characters):**  
Roland FP-30X Controller brings FP-30X editing to your Mac. Connect the piano via USB or bluetooth, select it as your MIDI device, and manage:

**Piano settings**  
Master volume and fine tuning, key touch response, brilliance, transpose, and ambience depth—plus quick metronome start/stop.

**Tones**  
Switch between Single, Split, Dual, and Twin. Browse presets by category (piano, E.piano, organ, strings, pads, synth, drums, GM2, and more). Adjust balances, split point, and octave shifts as modes require.

**Metronome**  
Set BPM, volume, click character, subdivision pattern, and beat/time signature from a clear grid.

**Piano Designer**  
Shape cabinet lid, resonances, temperament and root key. Save your setup back to the piano when supported.

The interface is available in **English** and **Spanish**.

**Keywords (100 characters total, comma-separated, no spaces after commas in App Store Connect):**  
`midi,piano,fp30x,keyboard,metronome,transpose,digitalpiano,controller,tuning,layers,roland,usb`  
*(93 chars — 7 chars of headroom. Do not include the app name; Apple indexes it separately. Avoid competitor brand names.)*

| Keyword | Rationale |
|---|---|
| `midi` | Core technology; high-volume search term |
| `piano` | Primary instrument type |
| `fp30x` | Exact model — captures buyers who already own the piano |
| `keyboard` | Broader instrument category |
| `metronome` | Prominent feature; users search for metronome apps |
| `transpose` | Specific parameter many pianists need |
| `digitalpiano` | Compound form to cover "digital piano" searches |
| `controller` | Describes the app role; common search term |
| `tuning` | Covers master tuning and note voicing use cases |
| `layers` | Dual/Split mode feature; differentiator |
| `roland` | Brand association (no trademark conflict with keywords) |
| `usb` | Clarifies connection method; filters out Bluetooth-only users |

---

### Apple Mac App Store (macOS) — Spanish

**Name:**  
`FP-30X Controller`

**Subtitle:**  
`Control MIDI para FP-30X`

**Promotional text (170 characters max, editable without review):**  
Controla tu Roland FP-30X desde una aplicación de escritorio.

**Description (up to 4000 characters):**  
Roland FP-30X Controller lleva la edición del FP-30X a tu Mac. Conecta el piano por USB o bluetooth, selecciónalo como dispositivo MIDI y gestiona:

**Ajustes del piano**  
Volumen maestro y afinación fina, respuesta al tacto, brillo, transposición y profundidad de ambiente, más arranque rápido del metrónomo.

**Timbres**  
Cambia entre los modos Single, Split, Dual y Twin. Explora presets por categoría (piano, piano eléctrico, órgano, cuerdas, pads, synth, batería, GM2 y más). Ajusta balances, punto de división y transposiciones de octava según el modo.

**Metrónomo**  
Configura BPM, volumen, tipo de click, patrón de subdivisión y compás desde una cuadrícula clara.

**Piano Designer**  
Moldea la posición de la tapa, resonancias, temperamento y tónica. Guarda la configuración en el piano cuando el instrumento lo permite.

La interfaz está disponible en **español** e **inglés**.

**Keywords (100 characters total, sin espacios tras las comas en App Store Connect):**  
`midi,piano,fp30x,keyboard,metronome,transpose,digitalpiano,controller,tuning,layers,roland,usb`  
*(93 chars — 7 chars de margen. No incluir el nombre de la app; Apple lo indexa por separado.)*

| Keyword | Justificación |
|---|---|
| `midi` | Tecnología central; término de búsqueda de alto volumen |
| `piano` | Tipo de instrumento principal |
| `fp30x` | Modelo exacto — capta a compradores que ya tienen el piano |
| `keyboard` | Categoría de instrumento más amplia |
| `metronome` | Función destacada; los usuarios buscan apps de metrónomo |
| `transpose` | Parámetro específico muy buscado por pianistas |
| `digitalpiano` | Forma compuesta para cubrir búsquedas de "digital piano" |
| `controller` | Describe el rol de la app; término de búsqueda común |
| `tuning` | Cubre afinación maestra y Note voicing |
| `layers` | Función Split/Dual; diferenciador frente a apps genéricas |
| `roland` | Asociación de marca (sin conflicto de marca en keywords) |
| `usb` | Aclara el método de conexión; filtra usuarios solo Bluetooth |

---

**Support URL:**  
`https://freemidichords.com/fp30x`

**Marketing URL (optional):**  
`https://freemidichords.com/fp30x`

**Privacy policy URL:**  
`https://sites.google.com/d/1e04u-XgmzXTBorPbcV9R-RX34QansCTX/p/1YuchH8tmmW80RuHM-8RiOrg9mcs86Y5u/edit`

**What’s to Test (for App Review):**  
1. Connect Roland FP-30X via USB.  
2. Grant no special permissions unless future versions add microphone, files, or network.  
3. Select MIDI port and Connect; adjust a slider and confirm the piano responds.  
4. Note: Piano Designer / Note voicing require compatible mode (Single + supported tones)—dialog explains this.

**Age rating:** Typically **4+** if no user-generated content, no web browsing, and no social features—confirm with Apple’s questionnaire.

---

### Microsoft Store (Windows) — English

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

**Search keywords** (Microsoft Store uses free-form tags; more flexibility than App Store):  
`MIDI, FP-30X, Roland piano, digital piano, controller, metronome, transpose, USB MIDI, tuning, layers, keyboard, music production`

| Keyword | Rationale |
|---|---|
| `MIDI` | Core technology |
| `FP-30X` | Exact model — high-intent buyers |
| `Roland piano` | Brand + category combination |
| `digital piano` | Broad category |
| `controller` | App role descriptor |
| `metronome` | Prominent feature |
| `transpose` | Specific parameter |
| `USB MIDI` | Connection method; filters out Bluetooth-only users |
| `tuning` | Master tuning and note voicing |
| `layers` | Split/Dual mode differentiator |
| `keyboard` | Instrument category |
| `music production` | Reaches broader musician audience |

**Capabilities / notes for submission:**  
- Declares use of **MIDI devices** (USB).  
- No account required unless you add cloud features later.  
- Add **Privacy policy** URL (even if you only process data locally).

**What’s new (template):**  
Initial release on Microsoft Store. [List fixes after updates.]

---

### Microsoft Store (Windows) — Spanish

**Short description (≤ 500 characters recommended):**  
Controla tu piano digital Roland FP-30X desde Windows: elige timbres, capas, metrónomo, afinación, ambiente y las opciones avanzadas del Piano Designer por USB MIDI. Edición cómoda en pantalla completa sin depender del pequeño panel del instrumento.

**Long description:**  
Roland FP-30X Controller es el compañero de escritorio para músicos que usan un FP-30X conectado al PC. Selecciona entrada y salida MIDI y ajusta:

- Ajustes del piano: volumen maestro y afinación, tacto, brillo, transposición, ambiente  
- Timbres: modos Single, Split, Dual y Twin con selección de presets por categoría, balances, punto de división y transposiciones de octava  
- Metrónomo: tempo, volumen, tipo de click, patrón rítmico y compás  
- Piano Designer (Beta): tapa del cabinet, resonancias, temperamento y tónica, guardar en el instrumento  
- Note voicing (Beta): afinación y carácter por tecla  

La app usa USB MIDI estándar. Un modo verbose opcional ayuda a diagnosticar problemas de conexión. Interfaz en español e inglés.

**Search keywords** (Microsoft Store — formato libre, más flexibilidad que App Store):  
`MIDI, FP-30X, Roland piano, piano digital, controlador, metrónomo, transposición, USB MIDI, afinación, capas, teclado, producción musical`

| Keyword | Justificación |
|---|---|
| `MIDI` | Tecnología central |
| `FP-30X` | Modelo exacto — compradores de alta intención |
| `Roland piano` | Marca + categoría |
| `piano digital` | Categoría amplia |
| `controlador` | Describe el rol de la app |
| `metrónomo` | Función destacada |
| `transposición` | Parámetro específico muy buscado |
| `USB MIDI` | Método de conexión; filtra usuarios solo Bluetooth |
| `afinación` | Afinación maestra y Note voicing |
| `capas` | Diferenciador Split/Dual frente a apps genéricas |
| `teclado` | Categoría de instrumento |
| `producción musical` | Alcanza a músicos con perfil productor |

**What’s new (template):**  
Versión inicial en Microsoft Store. [Listar correcciones tras actualizaciones.]

---

## License and third-party components

- **Project code:** [LICENSE](LICENSE) (**MIT**).
- **Bundled libraries (Qt/PySide6, mido, etc.):** [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md), including **LGPL-3.0** notes for Qt/PySide6 when you distribute binaries.
- **Store / frozen builds:** see [docs/packaging_store.md](docs/packaging_store.md).
