# Third-party notices

This file lists open-source components used by **Roland FP-30X Controller** (the “Application”) and summarizes license obligations relevant to distribution.

The **Application’s own source code** is licensed under the **MIT License** (see `LICENSE` in this repository). That license applies **only** to code written for this project, **not** to third-party libraries or to **Qt** / **PySide6**, which are governed by their respective licenses below.

---

## LGPL / Qt / PySide6 (important for store and binary distribution)

The graphical user interface uses **Qt for Python (PySide6)** and the **Qt** libraries. According to the PySide6 package metadata, those components are offered under:

**LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only**

For typical **binary distribution** of a PySide6 application, distributors choose compliance with the **GNU Lesser General Public License v3.0 (LGPL-3.0)** for the Qt/PySide6 stack (rather than GPLv2/v3 for the whole work), provided the distribution meets LGPL-3.0 requirements.

### LGPL-3.0 — practical checklist (non-exhaustive; not legal advice)

Consult a lawyer for commercial or store distribution. In general, for LGPL-3.0–licensed libraries linked into your app:

1. **License texts and notices**  
   Include the LGPL-3.0 license text (or a clear link) and copyright notices for Qt/PySide6 and related components, together with this file, in your installer / app bundle / store listing materials as applicable.

2. **Identify LGPL components**  
   State that the Application uses Qt and PySide6 under LGPL-3.0 (this file does that).

3. **Source / object code and “replacement” requirement**  
   LGPL-3.0 requires that users can **relink** or **replace** the LGPL-covered library with a modified version. For interpreted bindings (Python) + shared Qt libraries, common practice is to ship Qt as **shared libraries** (`.so` / `.dylib` / `.dll`) and document how a user may substitute compatible versions, **or** otherwise follow the exact LGPL-3.0 mechanisms (including, where applicable, offering corresponding source and build information).  
   **PyInstaller / frozen bundles:** special care is needed; many vendors ship Qt DLLs side-by-side and publish instructions or comply via the **written offer** / source provision routes described in LGPL-3.0 §4 and §6. Verify against current Qt Company / KDE guidance.

4. **No extra restrictions**  
   Do not impose legal terms that contradict LGPL-3.0 on the LGPL-covered libraries.

5. **Trademarks**  
   LGPL does **not** grant trademark rights for “Qt”, “PySide”, etc.

**Official references (read the full licenses):**

- LGPL-3.0: <https://www.gnu.org/licenses/lgpl-3.0.html>  
- Qt licensing: <https://www.qt.io/licensing/>  
- PySide / Qt for Python: <https://www.qt.io/qt-for-python>

**Full license texts in your build environment** (after `pip install`), see site-packages metadata, e.g.:

- `PySide6-*.dist-info/LICENSE.*`  
- `PySide6_Essentials-*.dist-info/`  
- `shiboken6-*.dist-info/`

---

## Bundled / runtime dependencies (direct)

| Component | SPDX / stated license | Notes |
|-----------|----------------------|--------|
| **PySide6** (includes **PySide6_Essentials**, **PySide6_Addons**, **shiboken6**) | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | Qt for Python; pulls in Qt shared libraries. |
| **mido** | MIT | MIDI message utilities. |
| **python-rtmidi** | MIT | Python binding; bundles/links **RtMidi** (see below). |
| **RtMidi** (via python-rtmidi) | Modified MIT / MIT-like | C++ MIDI I/O; see upstream `RtMidi` license in python-rtmidi sources / PyPI metadata. |
| **pyobjc-framework-Cocoa** (macOS only) | MIT | Optional; Dock icon integration on macOS. |
| **pyobjc-core** and other **pyobjc** deps (macOS) | MIT | Pulled in by pyobjc-framework-Cocoa. |

### MIT license (reference text)

The MIT License is reproduced here for convenience for components that use it:

```
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

**Copyright holders:** see each package’s `METADATA` / `LICENSE` in `site-packages` or the project’s repository (e.g. mido, python-rtmidi, pyobjc on GitHub).

---

## Indirect dependencies

**mido** depends on **packaging** (Apache-2.0 / BSD-style, per current PyPI metadata). If you ship a frozen executable, include its notices if your compliance process requires listing transitive deps.

---

## How to regenerate / verify

```bash
python -m pip install -e .
python -m pip show PySide6 mido python-rtmidi pyobjc-framework-Cocoa
```

For a **frozen** build, run `pip freeze` in the same environment used by PyInstaller and archive that output with your release artifacts for auditability.

---

## Disclaimer

This document is for **information only** and is **not** legal advice. LGPL and store policies (Microsoft Store, Apple App Store) are complex; consult qualified counsel before publishing.
