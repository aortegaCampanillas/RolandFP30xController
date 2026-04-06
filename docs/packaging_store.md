# Packaging for distribution, Microsoft Store, and Mac App Store

Plan for shipping **Roland FP-30X Controller** as a signed desktop app, optionally via **Microsoft Store (MSIX)** or **Mac App Store (MAS)**. This is operational guidance only—not legal advice.

---

## 1. Choose your license for *your* code (already set)

- **`LICENSE`**: **MIT** for project-authored code.  
- **Why MIT (vs BSD/GPL)?**  
  - **MIT**: very common, short, compatible with most stores and with shipping LGPL’d Qt next to your app.  
  - **BSD 2/3-clause**: similar permissiveness; 3-clause has “no endorsement” language.  
  - **GPL-3.0** for *your* app: usually **avoid** if you use PySide6 under **LGPL** and want to keep the rest of your code non-copyleft; GPLv3 would force a different compliance story.  
- **LGPL** applies to **Qt/PySide6** when you distribute binaries, not necessarily to your Python code; see `THIRD_PARTY_NOTICES.md`.

---

## 2. Baseline: reproducible build environment

- **Pin** Python (e.g. 3.11 or 3.12) and dependency versions for release (`requirements-release.txt` or `pip freeze`).  
- Build on the **target OS** (Windows build for Windows; macOS build for Mac).  
- Run tests: `pytest`.  
- Include **`LICENSE`**, **`THIRD_PARTY_NOTICES.md`**, and (if applicable) Qt/PySide license files inside the installer or app bundle.

---

## 3. Windows: PyInstaller → signed EXE → optional MSIX

### 3.1 One-folder vs one-file

- **One-folder** (`--onedir`): faster startup, easier to swap Qt DLLs for LGPL workflows.  
- **One-file** (`--onefile`): single EXE; still bundles Qt inside the extractor; verify LGPL obligations for your chosen layout.

### 3.2 PyInstaller sketch

1. Install deps in a clean venv.  
2. Add a **spec file** (e.g. `packaging/windows/roland_fp30x.spec`) that:  
   - Collects `roland_fp30x_controller` + data (`resources/*.svg`).  
   - Collects PySide6 Qt plugins (`platforms`, `styles`, etc.).  
   - Sets a Windows icon (`.ico`) if desired.  
3. Build: `pyinstaller packaging/windows/roland_fp30x.spec`

### 3.3 Code signing (outside Store)

- Sign the main executable and any bundled DLLs you sign (policy varies).  
- Use an **EV** certificate if you want SmartScreen reputation faster.

### 3.4 Microsoft Store (MSIX)

1. Produce an **MSIX** package (e.g. via **MSIX Packaging Tool**, or pipeline that wraps the PyInstaller output).  
2. **Declare capabilities**: e.g. access relevant device classes if Store policy requires explicit declaration for MIDI/USB; confirm current Partner Center docs.  
3. **Privacy policy URL** (even for local-only MIDI).  
4. **Store policies**: content, cryptography export, third-party notices (link or embed `THIRD_PARTY_NOTICES.md`).  
5. **Sign** the MSIX with a cert trusted for Store submission.

**Note:** LGPL compliance for Qt DLLs inside MSIX must still be satisfied (shared components, notices, and replacement/source obligations per LGPL-3.0).

---

## 4. macOS: PyInstaller (or briefcase) → .app → notarization → optional MAS

### 4.1 Bundle layout

- Use PyInstaller **`--windowed`** / **`BUNDLE`** target to produce `Roland FP30x Controller.app`.  
- **Info.plist**: `CFBundleIdentifier`, version, `CFBundleName`, `NSHighResolutionCapable`, optional `LSMinimumSystemVersion`.  
- **Icon**: `.icns` in the bundle.

### 4.2 Code signing & notarization (direct distribution)

1. **Developer ID Application** signing for all binaries and frameworks inside `.app`.  
2. **Hardened Runtime** entitlements (minimal set for MIDI; avoid unnecessary entitlements).  
3. **`codesign --deep --strict`** on the `.app`.  
4. **Notarize** with `notarytool` / `xcrun notarytool`, then staple.

### 4.3 Mac App Store (MAS)

MAS is **stricter** than Developer ID distribution:

- **App Sandbox** usually required; verify MIDI access under sandbox (CoreMIDI) with Apple’s current entitlement documentation.  
- **App Store Connect** metadata, privacy nutrition labels, export compliance.  
- **Third-party licenses**: include Qt/PySide LGPL notices in the bundle and/or legal links.  
- You may need to **remove or gate** macOS-only code paths that conflict with sandbox rules (e.g. optional PyObjC Dock tweaks if they imply disallowed behavior—re-test).

**Practical note:** Many PySide6 apps ship **outside** MAS via Developer ID + notarization first; MAS is a second, heavier milestone.

---

## 5. Alternative toolchains (optional)

- **Briefcase** (BeeWare): oriented to packaged apps; still need signing/notarization on Mac.  
- **cx_Freeze**, **Nuitka**: alternatives to PyInstaller; same signing/LGPL story.

---

## 6. Release checklist (short)

- [ ] Frozen build runs on a **clean VM** without Python installed.  
- [ ] MIDI device appears; Connect/Refresh works.  
- [ ] `LICENSE` + `THIRD_PARTY_NOTICES.md` shipped with the product or linked from Store listing.  
- [ ] Version bumped (`pyproject.toml` + bundle metadata).  
- [ ] Windows: signed binary / MSIX validated.  
- [ ] macOS: signed + notarized `.app`; Gatekeeper OK.  
- [ ] Lawyer review if publishing commercially or under strict enterprise policy.

---

## 7. References

- PyInstaller: <https://pyinstaller.org/>  
- Qt licensing: <https://www.qt.io/licensing/>  
- LGPL-3.0: <https://www.gnu.org/licenses/lgpl-3.0.html>  
- Microsoft MSIX: Microsoft Learn “MSIX” documentation  
- Apple: App Store Review Guidelines, App Sandbox, notarization docs  
