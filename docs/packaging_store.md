# Generación de builds para distribución y tiendas

Guía operativa para producir los artefactos de distribución de **PianoPilot for FP-30X**: DMG (macOS directo), `.pkg` (Mac App Store), `.exe` (Windows directo) y `.msix` (Windows Store).

---

## Resumen rápido

| Artefacto | Plataforma | Cómo se genera | Cuándo |
|-----------|-----------|----------------|--------|
| `.dmg` | macOS (descarga directa) | CI automático | Push de tag `v*.*.*` |
| `.pkg` | Mac App Store | Script local `build_mas_store.sh` | Manualmente antes de subir |
| `.exe` | Windows (descarga directa) | CI automático | Push de tag `v*.*.*` |
| `.msix` | Windows Store | CI automático | Push de tag `v*.*.*` |

---

## 1. CI automático — push de un tag

Todos los builds automáticos se lanzan al hacer push de un tag con formato `vX.Y.Z`:

```bash
git tag v1.2.3
git push origin v1.2.3
```

El workflow [`.github/workflows/release.yml`](../.github/workflows/release.yml) ejecuta tres jobs en paralelo (`build-macos`, `build-windows`, `build-msix`) y luego el job `release` que publica la GitHub Release con todos los artefactos adjuntos.

---

## 2. macOS — DMG (distribución directa)

**Job:** `build-macos` · Runner: `macos-latest`

### Proceso

1. PyInstaller con `--windowed` genera `dist/PianoPilot for FP-30X.app`.
2. `codesign --force --deep --sign -` firma ad-hoc (suficiente para Apple Silicon).
3. `create-dmg` produce el DMG.

### Ad-hoc vs Developer ID

La firma ad-hoc permite ejecutar el `.app` en el propio Mac que lo compiló o en Macs del mismo arq. Si quieres distribuirlo sin el aviso de Gatekeeper a usuarios externos, necesitas una firma con **Developer ID Application** y **notarización** (`xcrun notarytool`). Eso no está automatizado aún en CI; se haría localmente antes de crear el DMG.

---

## 3. macOS — Mac App Store (`.pkg`)

Este build **no está en CI** porque requiere certificados y un perfil de provisioning de Apple Developer que no deben subirse al repositorio.

### Prerrequisitos (una sola vez)

1. Ser miembro del **Apple Developer Program** (99 $/año).
2. En Xcode / Keychain: tener instaladas las identidades de firma:
   - `3rd Party Mac Developer Application: Tu Nombre (TEAMID)`
   - `3rd Party Mac Developer Installer: Tu Nombre (TEAMID)`
3. Crear un **provisioning profile** de tipo *Mac App Store* en App Store Connect y descargarlo (`.provisionprofile`).
4. Crear el venv de build MAS (necesario porque el build MAS usa flags distintos a los del venv de desarrollo):
   ```bash
   scripts/bootstrap_mas_build_env.sh
   ```

### Configurar `signing/local/mas.env`

```bash
cp scripts/mas-env.example signing/local/mas.env
# Edita el archivo con tus valores:
#   MAS_APP_DIST_IDENTITY   → "3rd Party Mac Developer Application: ..."
#   MAS_INSTALLER_IDENTITY  → "3rd Party Mac Developer Installer: ..."
#   MAS_BUNDLE_ID           → "com.tuempresa.pianopilot"
#   MAS_PROVISIONING_PROFILE → "/ruta/al/archivo.provisionprofile"
#   PYTHON_BIN              → ".venv-mas/bin/python"
#   MAS_VERSION             → "1.2.3"
#   MAS_BUILD_NUMBER        → "123"
```

> `signing/local/` está en `.gitignore`. Nunca subas certificados ni este archivo.

### Generar el `.pkg`

```bash
./scripts/build_mas_store.sh
```

El script ejecuta internamente `build_mas_pkg.sh` y realiza:

1. **PyInstaller** (`--windowed`, sin WebEngine ni componentes incompatibles con sandbox).
2. **Limpieza**: elimina Qt WebEngine, Qt libexec, herramientas CLI y symlinks rotos (causas comunes de rechazo en TestFlight, error 90885).
3. **Info.plist**: inyecta `CFBundleIdentifier`, `CFBundleDisplayName`, versión y `LSMinimumSystemVersion`.
4. **Icono**: convierte el SVG a `.icns` con `sips` + `iconutil` y lo incrusta.
5. **Provisioning profile**: copia `embedded.provisionprofile` en el bundle.
6. **Entitlements**: genera un `.plist` mínimo con `com.apple.security.app-sandbox` (CoreMIDI funciona en sandbox sin entitlements adicionales).
7. **`codesign`**: firma con `--force --deep --timestamp`.
8. **`productbuild`**: crea y firma el `.pkg` instalador.

### Subir a App Store Connect

```bash
# Con Transporter (GUI) o por CLI:
xcrun altool --upload-package PianoPilot-macos-appstore.pkg \
  --type osx --apiKey TU_KEY --apiIssuer TU_ISSUER
```

O abre **Transporter.app**, arrastra el `.pkg` y pulsa *Deliver*.

---

## 4. Windows — EXE (distribución directa)

**Job:** `build-windows` · Runner: `windows-latest`

### Proceso

1. `scripts/make_ico.py` genera `app_icon.ico` desde el SVG (requiere Pillow).
2. PyInstaller con `--onefile --windowed --icon` produce un único `.exe`.
3. Se renombra a `PianoPilot-for-FP30X-vX.Y.Z-windows.exe` y se sube como artefacto.

---

## 5. Windows — MSIX (Windows Store)

**Job:** `build-msix` · Runner: `windows-latest`

### Prerrequisito: secreto `MSIX_PUBLISHER`

En **GitHub → Settings → Secrets and variables → Actions**, añade:

| Secreto | Valor |
|---------|-------|
| `MSIX_PUBLISHER` | El Publisher CN de Partner Center, p. ej. `CN=E70C548D-768A-4F80-B0D6-41DB1F7A402F` |

Se encuentra en **Partner Center → tu app → Product Identity**.

### Proceso del job

1. **`make_ico.py`**: genera el `.ico` para el ejecutable.
2. **PyInstaller en modo carpeta** (sin `--onefile`): produce `dist/PianoPilot/` con `PianoPilot.exe` y la carpeta `_internal/` con todas las dependencias. El modo carpeta es necesario porque `--onefile` extrae a `%TEMP%` en cada ejecución, lo que puede conflictuar con las restricciones del sandbox de la Store.
3. **`make_msix_assets.py`**: renderiza el SVG del icono a los 6 tamaños PNG requeridos por el Store:
   - `Square44x44Logo.png` (44×44)
   - `Square150x150Logo.png` (150×150)
   - `Square310x310Logo.png` (310×310)
   - `StoreLogo.png` (50×50)
   - `Wide310x150Logo.png` (310×150) — SVG centrado con padding
   - `SplashScreen.png` (620×300) — SVG centrado con padding
4. **Ensamblado del layout**: copia `packaging/windows/AppxManifest.xml` e inyecta la versión (`vX.Y.Z` → `X.Y.Z.0`) y el Publisher CN (desde el secreto) mediante sustitución de texto en PowerShell.
5. **`makeappx.exe`** (del Windows SDK): empaqueta la carpeta en un `.msix`.

### Estructura del layout antes de empaquetar

```
dist/PianoPilot/
  AppxManifest.xml        ← inyectado por CI
  Assets/
    Square44x44Logo.png
    Square150x150Logo.png
    Square310x310Logo.png
    StoreLogo.png
    Wide310x150Logo.png
    SplashScreen.png
  PianoPilot.exe
  _internal/              ← dependencias PyInstaller
    ...
```

### Subir a Partner Center

1. En **Partner Center → tu app → Manage packages**, sube el `.msix`.
2. Microsoft valida y firma el paquete por su cuenta antes de publicarlo.
3. No es necesario firmar el `.msix` tú mismo para la subida al Store.

---

## 6. Bumping de versión antes de un release

Antes de crear el tag, actualiza la versión en `pyproject.toml`:

```toml
[project]
version = "1.2.3"
```

Luego:

```bash
git add pyproject.toml
git commit -m "Bump version to 1.2.3"
git tag v1.2.3
git push origin main --tags
```

---

## 7. Checklist de release

- [ ] `pyproject.toml` tiene la versión correcta.
- [ ] El build del CI pasa en verde (macOS DMG, Windows EXE, Windows MSIX).
- [ ] El `.msix` se sube a Partner Center.
- [ ] El `.pkg` MAS se genera localmente y se sube con Transporter.
- [ ] `LICENSE` y `THIRD_PARTY_NOTICES.md` incluidos en el bundle / enlazados en el listing.
- [ ] Revisión de privacidad (la app no envía datos a servidores; solo USB MIDI local).

---

## 8. Referencias

- PyInstaller: <https://pyinstaller.org/>
- MSIX overview: Microsoft Learn — "What is MSIX?"
- makeappx: Windows SDK, `C:\Program Files (x86)\Windows Kits\10\bin\…\x64\makeappx.exe`
- Mac App Store: App Store Review Guidelines, App Sandbox entitlements
- Qt / PySide6 licensing (LGPL-3.0): <https://www.qt.io/licensing/>
