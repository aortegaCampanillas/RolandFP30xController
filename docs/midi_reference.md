# Referencia MIDI — Roland FP-30X ↔ RolandFP30xController

Fuentes de este documento:
- `docs/FP-30X_MIDI_Imple_eng01_W.pdf` — manual oficial Roland (fuente de verdad)
- Ingeniería inversa de **Roland Piano App 1.5.9** (Android, APKPure) — `js/common/services/midiConnector.js` y `valuesGenerator.js`

Ante cualquier conflicto entre las secciones "Fuente: PDF" y "Fuente: App", el PDF tiene prioridad.

---

## 1. Estructura de mensajes Roland SysEx (DT1 / RQ1)

```
F0  41  10  00 00 00 28  <CMD>  <ADDR×4>  <DATA…>  <CHK>  F7
│   │   │   └─────────┘  │     └───────┘           │
│   │   │   Model ID     │     4 bytes             Roland checksum
│   │   Device ID=0x10   │     (dirección)
│   ROLAND_ID=0x41       RQ1=0x11 / DT1=0x12
└── F0 SysEx start
```

**Checksum:** `(128 − (sum(addr_bytes + data_bytes) % 128)) % 128`

**Codificación de valores multi-byte** (Roland 7-bit encoding):
- 1 byte: valor directo `0x00–0x7F`
- 2 bytes: `[v // 128, v % 128]` → reconstrucción: `b0 * 128 + b1`
- 3 bytes (tonos/canciones): `[category, number // 128, number % 128]`

Implementado en Python: `roland_data_set_1()` y `roland_data_request_1()` en
`src/roland_fp30x_controller/midi/messages.py`.

---

## 2. Mapa de direcciones SysEx del FP-30X

Todas las direcciones son de 4 bytes. Las de la columna **Bytes** distintas de 1
requieren codificación multi-byte. La columna **Dir.** indica sentido: R=leer, W=escribir.

### 2.1 Bloque 01 00 01 xx — Estado de lectura (solo RQ1)

| Nombre lógico         | Dirección       | Bytes | Dir. | Valores / Notas |
|-----------------------|-----------------|-------|------|-----------------|
| `songToneLanguage`    | `01 00 01 00`   | 1     | R    | |
| `keyTransposeRO`      | `01 00 01 01`   | 1     | R    | Transposición teclado. Encoding: `semitones = value − 64`. Rango FP-30X: −6..+5 (valores 58..69). Default 64=0. |
| `songTransposeRO`     | `01 00 01 02`   | 1     | R    | Leer transposición activa de canción |
| `sequencerStatus`     | `01 00 01 03`   | 1     | R    | Estado del secuenciador |
| `sequencerMeasure`    | `01 00 01 05`   | 2     | R    | Compás actual |
| `sequencerTempoNotation` | `01 00 01 07` | 1    | R    | Notación de tempo: 3=corchea negra, 4=negra, 7=negra×2... |
| `sequencerTempoRO`    | `01 00 01 08`   | 2     | R    | Tempo actual en BPM (7-bit ×2) |
| `sequencerBeatNumerator` | `01 00 01 0A` | 1    | R    | Numerador del compás |
| `sequencerBeatDenominator` | `01 00 01 0B` | 1  | R    | Denominador del compás |
| `sequencerPartSwAccomp` | `01 00 01 0C` | 1    | R    | Parte acompañamiento: Off(0) On(1) NoData(2) |
| `sequencerPartSwLeft` | `01 00 01 0D`   | 1     | R    | Parte izquierda: Off(0) On(1) NoData(2) |
| `sequencerPartSwRight` | `01 00 01 0E`  | 1     | R    | Parte derecha: Off(0) On(1) NoData(2) |
| `metronomeStatus`     | `01 00 01 0F`   | 1     | R    | Metrónomo: 0=off 1=on. El piano emite DT1 espontáneamente al cambiar desde el panel. |
| `headphonesConnection` | `01 00 01 10`  | 1     | R    | Auriculares conectados |
| `ambienceTypeAvailable` | `01 00 01 11` | 1    | R    | 0=No disponible 1=Disponible |

### 2.2 Bloque 01 00 02 xx — Parámetros de piano (R/W)

| Nombre lógico         | Dirección       | Bytes | Dir. | Valores / Notas |
|-----------------------|-----------------|-------|------|-----------------|
| `keyBoardMode`        | `01 00 02 00`   | 1     | R/W  | Single(0) Split(1) Dual(2) TwinPiano(3) |
| `splitPoint`          | `01 00 02 01`   | 1     | R/W  | Nota MIDI del punto de split |
| `splitOctaveShift`    | `01 00 02 02`   | 1     | R/W  | |
| `splitBalance`        | `01 00 02 03`   | 1     | R/W  | |
| `dualOctaveShift`     | `01 00 02 04`   | 1     | R/W  | Encoding: octava+64 |
| `dualBalance`         | `01 00 02 05`   | 1     | R/W  | En FP-30X el byte suele ir **centrado en 64** (`64 + (panel−9)×3` para 0..18). Además el manual indica CC7 por parte (canales 4 + capa). |
| `twinPianoMode`       | `01 00 02 06`   | 1     | R/W  | |
| `toneForSingle`       | `01 00 02 07`   | 3     | R/W  | `[category, num//128, num%128]` |
| `toneForSplit`        | `01 00 02 0A`   | 3     | R/W  | Ídem |
| `toneForDual`         | `01 00 02 0D`   | 3     | R/W  | Ídem |
| `songNumber`          | `01 00 02 10`   | 3     | R/W  | `[category, num//128, num%128]` |
| `masterVolume`        | `01 00 02 13`   | 1     | R/W  | 0–127. **Usar este para controlar el volumen** — actualiza las luces del panel. El Universal Realtime Master Volume (§4.1) NO mueve las luces. |
| `masterVolumeLimit`   | `01 00 02 14`   | 1     | R/W  | |
| `allSongPlayMode`     | `01 00 02 15`   | 1     | R/W  | |
| `masterTuning`        | `01 00 02 18`   | 2     | R/W  | Fine tuning, 7-bit ×2 |
| `ambience`            | `01 00 02 1A`   | 1     | R/W  | Nivel de ambiente 0–… |
| `headphones3DAmbience` | `01 00 02 1B`  | 1     | R/W  | |
| `brilliance`          | `01 00 02 1C`   | 1     | R/W  | Brillo del sonido |
| `keyTouch`            | `01 00 02 1D`   | 1     | R/W  | Sensibilidad del teclado (ver §5.1) |
| `transposeMode`       | `01 00 02 1E`   | 1     | R/W  | KeyboardAndSong(0) Keyboard(1) Song(2) |
| `metronomeBeat`       | `01 00 02 1F`   | 1     | R/W  | Compás del metrónomo (ver §4.3) |
| `metronomePattern`    | `01 00 02 20`   | 1     | R/W  | Patrón 0–7 |
| `metronomeVolume`     | `01 00 02 21`   | 1     | R/W  | Volumen: 0=off, 1–10 |
| `metronomeTone`       | `01 00 02 22`   | 1     | R/W  | Click(0) Electronic(1) Voice-JP(2) Voice-EN(3) |
| `metronomeDownBeat`   | `01 00 02 23`   | 1     | R/W  | |
| `metronomeType`       | `01 00 02 25`   | 1     | R/W  | Metronome(0) RhythmPattern(1) |
| `rhythmPatternNumber` | `01 00 02 26`   | 3     | R/W  | |

### 2.3 Bloque 01 00 03 xx — Comandos de escritura (DT1)

| Nombre lógico         | Dirección       | Bytes | Dir. | Valores / Notas |
|-----------------------|-----------------|-------|------|-----------------|
| `applicationMode`     | `01 00 03 00`   | 1     | W    | |
| `scorePageTurn`       | `01 00 03 02`   | 1     | W    | On(1)/Off(0) |
| `arrangerPedalFunction` | `01 00 03 03` | 2     | W    | |
| `arrangerBalance`     | `01 00 03 05`   | 1     | W    | |
| `connection`          | `01 00 03 06`   | 1     | W    | **Handshake app**: enviar `01` al conectar. Sin este mensaje el piano ignora DT1 de master volume y metrónomo. La app Roland lo llama `sendConnection(1)` y lo envía justo tras abrir el puerto MIDI. |
| `keyTransposeWO`      | `01 00 03 07`   | 1     | W    | Transposición teclado. Encoding: `value = semitones + 64`. Rango FP-30X: −6..+5. Par write de `keyTransposeRO`. |
| `songTransposeWO`     | `01 00 03 08`   | 1     | W    | Transposición de canción (write-only) |
| `sequencerTempoWO`    | `01 00 03 09`   | 2     | W    | Tempo BPM: `[bpm//128, bpm%128]`, rango 20–250 |
| `tempoReset`          | `01 00 03 0B`   | 1     | W    | Reset tempo al valor original |
| `sequencerLoopStartMeasure` | `01 00 03 0C` | 2  | W    | |
| `sequencerLoopEndMeasure`   | `01 00 03 0E` | 2  | W    | |
| `sequencerPlay`       | `01 00 03 17`   | 1     | W    | Start(1) — *no funciona en PP2* |
| `sequencerStop`       | `01 00 03 19`   | 1     | W    | Stop(1) — *no funciona en PP2* |
| `metronomeSwitch`     | `01 00 03 1A`   | 1     | W    | Off(0) On(1) OnRequestNextStart(2) |
| `sequencerRecStandby` | `01 00 03 1B`   | 1     | W    | CancelRecStandby(0) RecStandby(1) |
| `playbackReadyRequest` | `01 00 03 1D`  | 1     | W    | Ready(1) — reset estado sin GM2SystemOn |

### 2.4 Bloque 01 00 05 xx — Botones (simulación de pulsación)

Semántica: `00`=primera pulsación, `01`=repetición (pulsación sostenida).

| Nombre lógico              | Dirección       | Dir. | Notas |
|----------------------------|-----------------|------|-------|
| `sequencerREW`             | `01 00 05 00`   | W    | Rebobinar |
| `sequencerFF`              | `01 00 05 01`   | W    | Avance rápido |
| `sequencerReset`           | `01 00 05 02`   | W    | Ir al inicio |
| `sequencerTempoDown`       | `01 00 05 03`   | W    | Bajar tempo 1 BPM |
| `sequencerTempoUp`         | `01 00 05 04`   | W    | Subir tempo 1 BPM |
| `sequencerPlayStopToggle`  | `01 00 05 05`   | W    | Play/Stop toggle |
| `sequencerAccompPartSwToggle` | `01 00 05 06` | W   | Toggle parte acompañamiento |
| `sequencerLeftPartSwToggle` | `01 00 05 07`  | W    | Toggle parte izquierda |
| `sequencerRightPartSwToggle` | `01 00 05 08` | W    | Toggle parte derecha |
| `metronomeSwToggle`        | `01 00 05 09`   | W    | **Toggle metrónomo on/off** |
| `sequencerPreviousSong`    | `01 00 05 0A`   | W    | Canción anterior |
| `sequencerNextSong`        | `01 00 05 0B`   | W    | Canción siguiente |
| `sequencerTempoDownBy10`   | `01 00 05 0C`   | W    | Bajar tempo 10 BPM |
| `sequencerTempoUpBy10`     | `01 00 05 0D`   | W    | Subir tempo 10 BPM |

### 2.5 Bloque 01 00 08 xx — Información del piano

| Nombre lógico    | Dirección       | Bytes | Dir. | Notas |
|------------------|-----------------|-------|------|-------|
| `addressMapVersion` | `01 00 08 00` | 1    | R    | 0=producto antiguo (no responde DT1); 1=soporta Apple Watch |
| `aliveCheck`     | `01 00 08 01`   | 1     | R    | Siempre devuelve 0; usado para detectar conexión activa |

---

## 3. Mensajes MIDI estándar (no SysEx)

### 3.1 Control Change (CC)

| CC  | Nombre       | Canal típico | Rango | Notas |
|-----|--------------|--------------|-------|-------|
| 0   | Bank MSB     | 4            | 0–127 | Precede a PC; enviar con gap ≥ 20 ms |
| 32  | Bank LSB     | 4            | 0–127 | |
| 6   | Data Entry MSB | cualquiera | 0–127 | Parte del flujo RPN |
| 38  | Data Entry LSB | cualquiera | 0–127 | Siempre 0 en Coarse Tuning |
| 100 | RPN LSB      | cualquiera   | 0/127 | |
| 101 | RPN MSB      | cualquiera   | 0/127 | |

### 3.2 Program Change

Enviar siempre precedido de CC0 + CC32. El FP-30X no aplica el cambio de sonido
hasta el siguiente Note On; se recomienda enviar un Note On/Off de enganche
(velocity=1, any note) ≥ 80 ms después del PC.

```
CC0(bank_msb) → CC32(bank_lsb) → PC(program) → [wait 80ms] → NoteOn(60,1) → NoteOff(60,0)
```

### 3.3 RPN — Registered Parameter Numbers (Fuente: PDF)

#### Coarse Tuning (RPN 0,2)

```
CC101=0 → CC100=2 → CC6=value → CC38=0 → CC101=127 → CC100=127 (Null RPN)
```
- `value = semitones + 64` (64 = 0 semitonos, rango −64..+63)

---

## 4. Universal SysEx (no Roland)

### 4.1 Master Volume (Universal Realtime)

```
F0 7F 7F 04 01 00 <vv> F7
```
- `vv` = 0–127
- ⚠️ El FP-30X **no actualiza las luces del panel** con este mensaje. Para controlar el volumen con feedback visual usar DT1 `masterVolume` (`01 00 02 13`, §2.2).

### 4.2 Master Coarse Tuning (Universal Realtime) — Fuente: PDF

```
F0 7F 7F 04 04 00 <mm> F7
```
- `mm = 0x40 + semitones` (0x40 = 0 semitonos, rango −24..+24)
- El byte `ll` (posición 5) se ignora; se envía `00`

### 4.3 GM2 Global Reverb (Universal Realtime) — Fuente: PDF

```
F0 7F 7F 04 05 01 01 01 01 01 <pp> <vv> F7
```
- `pp=0` → tipo de reverb (0–127)
- `pp=1` → tiempo de cola (0–127)

---

## 5. Tablas de valores de referencia

### 5.1 Key Touch (`01 00 02 1D`)

FP-30X usa `keyTouchTypeValue=0` (continuo 0–100) o `keyTouchTypeValue=2` (discreto):

| Valor | Nombre (type=2) |
|-------|-----------------|
| 0     | Fix (fuerza constante) |
| 1     | Light |
| 2     | Medium |
| 3     | Heavy |

### 5.2 Metronome Beat (`01 00 02 1F`) — FP-30X usa type=0

| Valor | Compás |
|-------|--------|
| 0     | 2/2    |
| 1     | 3/2    |
| 2     | 2/4    |
| 3     | 3/4    |
| 4     | 4/4    |
| 5     | 5/4    |
| 6     | 6/4    |
| 7     | 7/4    |
| 8     | 3/8    |
| 9     | 6/8    |
| 10    | 8/8    |
| 11    | 9/8    |
| 12    | 12/8   |

### 5.3 Metronome Tone (`01 00 02 22`)

| Valor | Sonido |
|-------|--------|
| 0     | Click |
| 1     | Electronic |
| 2     | Voice (JP) |
| 3     | Voice (EN) |

### 5.4 Metronome Volume (`01 00 02 21`)

0 = silenciado, 1–10 = niveles de volumen.

### 5.5 Keyboard Mode (`01 00 02 00`)

| Valor | Modo |
|-------|------|
| 0     | Single |
| 1     | Split |
| 2     | Dual |
| 3     | Twin Piano |

### 5.6 Transpose Mode (`01 00 02 1E`)

| Valor | Efecto |
|-------|--------|
| 0     | Keyboard + Song |
| 1     | Solo Keyboard |
| 2     | Solo Song |

---

## 6. Metrónomo — flujo completo

```python
# Encender (sin importar estado actual):
roland_data_set_1((0x01, 0x00, 0x03, 0x1A), (0x01,))

# Apagar:
roland_data_set_1((0x01, 0x00, 0x03, 0x1A), (0x00,))

# Toggle (equivale al botón start/stop de la app):
roland_data_set_1((0x01, 0x00, 0x05, 0x09), (0x00,))

# Fijar tempo a 120 BPM:
roland_data_set_1((0x01, 0x00, 0x03, 0x09), (120 // 128, 120 % 128))  # → (0x00, 0x78)

# Leer estado actual (RQ1 → el piano responde con DT1 en 01 00 01 0F):
roland_data_request_1((0x01, 0x00, 0x01, 0x0F), (0x00, 0x00, 0x00, 0x01))

# Leer tempo actual (RQ1 → respuesta en 01 00 01 08, 2 bytes):
roland_data_request_1((0x01, 0x00, 0x01, 0x08), (0x00, 0x00, 0x00, 0x02))
```

---

## 7. Audit: controles remotos vs CCs estándar

Resultado de auditar la Roland Piano App 1.5.9: **la app no expone controles de CC estándar** (CC7, CC11, CC10, CC1, CC91, CC93) en su interfaz remota. Todos los controles de dispositivo usan DT1 SysEx. Los CCs estándar solo aparecen en la reproducción SMF (player interno).

Sin embargo, el FP-30X responde correctamente a los CCs estándar como dispositivo MIDI normal. Nuestra app los usa para el grupo "Mix" — esto es válido aunque distinto al enfoque de la app Roland.

| Control          | Nuestra app          | Roland Piano App  |
|------------------|----------------------|-------------------|
| Master Volume    | DT1 `01 00 02 13` ✓  | DT1 `01 00 02 13` |
| Part Volume      | CC7 (canal 4)        | No expuesto       |
| Expression       | CC11 (canal 4)       | No expuesto       |
| Pan              | CC10 (canal 4)       | No expuesto       |
| Modulation       | CC1 (canal 4)        | No expuesto       |
| Reverb send      | CC91 + GM2 SysEx     | No expuesto       |
| Chorus send      | CC93 (canal 4)       | No expuesto       |
| Sustain          | CC64 (canal 4)       | No expuesto       |
| Transpose        | Universal RT SysEx   | DT1 `01 00 03 07` (rango −6..+5) |
| Metronome on/off | DT1 `01 00 05 09` ✓  | DT1 `01 00 05 09` |
| Metronome tempo  | DT1 `01 00 03 09` ✓  | DT1 `01 00 03 09` |
| Instrument       | CC0+CC32+PC          | DT1 `01 00 02 07` (3 bytes) |

**Nota transpose:** nuestra app usa Universal Realtime Master Coarse Tuning (rango −24..+24) mientras la Roland app usa DT1 keyTranspose (rango −6..+5). Ambos funcionan en el FP-30X aunque son parámetros independientes.

---

## 8. Lectura de estado al conectar

Al abrir la conexión MIDI con el piano, la app envía estos RQ1 (con ~200 ms de delay
para que el worker de entrada esté listo) y actualiza la UI al recibir las respuestas DT1:

```python
master_volume_read()    # RQ1 → 01 00 02 13, 1 byte  → actualiza slider Master Volume
metronome_read_tempo()  # RQ1 → 01 00 01 08, 2 bytes → actualiza slider Tempo
metronome_read_status() # RQ1 → 01 00 01 0F, 1 byte  → actualiza etiqueta ON/OFF
```

**Decodificación de las respuestas:**
- `masterVolume` (01 00 02 13): `data[0]` directo, 0–127
- `sequencerTempoRO` (01 00 01 08): `bpm = data[0] * 128 + data[1]`, rango 20–250
- `metronomeStatus` (01 00 01 0F): `on = bool(data[0])`

El piano también emite DT1 **espontáneamente** (sin RQ1 previo) para `metronomeStatus`
cada vez que el usuario pulsa el botón del metrónomo en el panel físico. El parser
`parse_roland_dt1()` en `midi/sysex_parser.py` maneja ambos casos.

**Nota sobre Key Transpose vs Master Coarse Tuning:**
- `keyTransposeRO/WO` controla la transposición del teclado físico (rango −6..+5).
- Master Coarse Tuning (Universal Realtime SysEx §4.2 / RPN 0,2) es un offset de pitch
  global independiente (rango −24..+24). Nuestra app usa este segundo mecanismo en el
  slider de transposición. La lectura de `keyTransposeRO` al conectar solo sincroniza si
  el piano tiene una transposición aplicada desde su panel.

---

## 8. Notas de implementación

- **Device ID:** `0x10`. Si el piano no responde, probar `0x00` (broadcast).
- **Gap entre mensajes:** ≥ 20 ms entre CC0/CC32/PC para evitar agrupación errónea.
- **Delay post-PC:** ≥ 80 ms antes del Note On de enganche.
- **Delay post-connect para RQ1:** ≥ 200 ms desde que se abre el MIDI input, para
  garantizar que el worker esté escuchando antes de enviar las solicitudes de estado.
- **`sequencerPlay` / `sequencerStop`** (`01 00 03 17 / 19`) están documentados en la
  app como *"not working for PP2 piano"* — el FP-30X los ignora.
- **Dirección `connection`** (`01 00 03 06`): usada internamente por la app para señalar
  que hay una app conectada, no para controlar funciones de sonido. Fue la dirección
  incorrectamente usada en la implementación original de `metronome_probe_on()`.
- La app Roland es una **WebView híbrida**: la UI es HTML/JS que llama a `midiConnector.js`,
  el cual construye los SysEx y los envía a través de una capa Java/JNI al driver USB MIDI.
- **Parser DT1 entrante:** `midi/sysex_parser.py` → `parse_roland_dt1(msg)` valida y
  extrae `(address_tuple, data_bytes)` de cualquier SysEx DT1 del FP-30X.
