#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Build and sign a Mac App Store package for PianoPilot for FP-30X.

Uso:
  scripts/build_mas_pkg.sh \
    --app-dist-identity "3rd Party Mac Developer Application: Tu Nombre (TEAMID)" \
    --installer-identity "3rd Party Mac Developer Installer: Tu Nombre (TEAMID)" \
    --bundle-id "com.tuempresa.pianopilot" \
    --provisioning-profile "/path/to/PianoPilot.provisionprofile"

Opciones:
  --app-dist-identity     Identidad de firma App Store para el .app (requerido)
  --installer-identity    Identidad de firma para el .pkg (requerido)
  --bundle-id             CFBundleIdentifier (requerido)
  --provisioning-profile  Ruta al perfil de provisioning MAS (requerido)
  --version               CFBundleShortVersionString (opcional)
  --build-number          CFBundleVersion (opcional)
  --output-pkg            Ruta de salida del .pkg (defecto: PianoPilot-macos-appstore.pkg)
  --min-system-version    LSMinimumSystemVersion (defecto: 12.0)
  --icon-source           PNG o SVG para generar AppIcon.icns (defecto: src/roland_fp30x_controller/resources/app_icon.svg)
  --skip-icon             No generar/incrustar AppIcon.icns
  --skip-build            No ejecutar PyInstaller (usa el .app ya existente en dist/)
  --skip-store-validation Omitir `installer -store` (recomendado; Transporter valida al subir)
  -h, --help              Mostrar esta ayuda

Notas:
  - Script para subida a Mac App Store, no para distribución directa (DMG/Developer ID).
  - Sube el .pkg resultante con Transporter o Xcode Organizer.
  - PyInstaller se invoca como: PYTHON_BIN -m PyInstaller (defecto: python3).
    Crea el venv con: scripts/bootstrap_mas_build_env.sh
    y define PYTHON_BIN en signing/local/mas.env apuntando a .venv-mas/bin/python.
EOF
}

# ── Valores por defecto ───────────────────────────────────────────────────
APP_NAME="PianoPilot"
DISPLAY_NAME="PianoPilot for FP-30X"
ENTRYPOINT="src/roland_fp30x_controller/__main__.py"
APP_DIST_IDENTITY=""
INSTALLER_IDENTITY=""
BUNDLE_ID=""
PROVISIONING_PROFILE=""
VERSION=""
BUILD_NUMBER=""
OUTPUT_PKG=""
CATEGORY_UTI="public.app-category.music"
MIN_SYSTEM_VERSION="12.0"
ICON_SOURCE="src/roland_fp30x_controller/resources/app_icon.svg"
SKIP_ICON=0
SKIP_BUILD=0
SKIP_STORE_VALIDATION=0
PYTHON_BIN="${PYTHON_BIN:-python3}"

# ── Helpers ───────────────────────────────────────────────────────────────
clear_quarantine_attrs() {
  local path="$1"
  [[ -e "$path" ]] || return 0
  xattr -cr "$path" 2>/dev/null || true
  xattr -dr com.apple.quarantine "$path" 2>/dev/null || true
}

remove_dead_symlinks_under() {
  local root="$1"
  [[ -d "$root" ]] || return 0
  find "$root" -type l ! -exec test -e {} \; -delete 2>/dev/null || true
}

# ── Parse args ────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --app-dist-identity)    APP_DIST_IDENTITY="${2:-}";    shift 2 ;;
    --installer-identity)   INSTALLER_IDENTITY="${2:-}";   shift 2 ;;
    --bundle-id)            BUNDLE_ID="${2:-}";            shift 2 ;;
    --provisioning-profile) PROVISIONING_PROFILE="${2:-}"; shift 2 ;;
    --version)              VERSION="${2:-}";              shift 2 ;;
    --build-number)         BUILD_NUMBER="${2:-}";         shift 2 ;;
    --output-pkg)           OUTPUT_PKG="${2:-}";           shift 2 ;;
    --min-system-version)   MIN_SYSTEM_VERSION="${2:-}";   shift 2 ;;
    --icon-source)          ICON_SOURCE="${2:-}";          shift 2 ;;
    --skip-icon)            SKIP_ICON=1;                   shift   ;;
    --skip-build)           SKIP_BUILD=1;                  shift   ;;
    --skip-store-validation) SKIP_STORE_VALIDATION=1;      shift   ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Argumento desconocido: $1" >&2; usage; exit 1 ;;
  esac
done

# ── Validaciones básicas ──────────────────────────────────────────────────
if [[ -z "$APP_DIST_IDENTITY" || -z "$INSTALLER_IDENTITY" || -z "$BUNDLE_ID" || -z "$PROVISIONING_PROFILE" ]]; then
  echo "Error: --app-dist-identity, --installer-identity, --bundle-id y --provisioning-profile son requeridos." >&2
  usage
  exit 1
fi

if [[ ! -f "$PROVISIONING_PROFILE" ]]; then
  echo "Error: perfil de provisioning no encontrado: $PROVISIONING_PROFILE" >&2
  exit 1
fi

# ── Rutas ─────────────────────────────────────────────────────────────────
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_PATH="$ROOT_DIR/dist/${APP_NAME}.app"
ENTITLEMENTS_PATH="$ROOT_DIR/scripts/entitlements.mas.generated.plist"
ICONSET_TMP_DIR=""
PROFILE_PLIST_TMP=""

[[ -z "$OUTPUT_PKG" ]] && OUTPUT_PKG="$ROOT_DIR/${APP_NAME}-macos-appstore.pkg"
[[ "$ICON_SOURCE" != /* ]] && ICON_SOURCE="$ROOT_DIR/$ICON_SOURCE"

mkdir -p "$ROOT_DIR/build"
PROFILE_PLIST_TMP="$(mktemp "$ROOT_DIR/build/profile.XXXXXX.plist")"
trap 'rm -rf "${ICONSET_TMP_DIR:-}" "${PROFILE_PLIST_TMP:-}"' EXIT

cd "$ROOT_DIR"

# ── PyInstaller build ─────────────────────────────────────────────────────
if [[ "$SKIP_BUILD" -eq 0 ]]; then
  if ! "$PYTHON_BIN" -m PyInstaller --version >/dev/null 2>&1; then
    echo "Error: PyInstaller no está instalado para: $PYTHON_BIN" >&2
    echo "  Crea el venv con: scripts/bootstrap_mas_build_env.sh" >&2
    echo "  y define PYTHON_BIN en signing/local/mas.env apuntando a .venv-mas/bin/python" >&2
    exit 1
  fi

  if [[ ! -f "$ENTRYPOINT" ]]; then
    echo "Error: entrypoint no encontrado: $ENTRYPOINT" >&2
    exit 1
  fi

  echo "Construyendo ${APP_NAME}.app con PyInstaller ($PYTHON_BIN)..."

  # Qt WebEngine no se usa y causa rechazos en TestFlight (código 90885).
  # Se excluye en tiempo de análisis y se eliminan restos tras el build.
  "$PYTHON_BIN" -m PyInstaller --noconfirm --clean --windowed --name "$APP_NAME" \
    --collect-all PySide6 \
    --collect-submodules PySide6 \
    --collect-all roland_fp30x_controller \
    --hidden-import mido.backends.rtmidi \
    --exclude-module PySide6.QtWebEngineCore \
    --exclude-module PySide6.QtWebEngineWidgets \
    --exclude-module PySide6.QtWebEngineQuick \
    --exclude-module PySide6.QtWebView \
    --exclude-module PySide6.QtWebChannel \
    --exclude-module PySide6.QtSql \
    --exclude-module tkinter \
    "$ENTRYPOINT"
fi

if [[ ! -d "$APP_PATH" ]]; then
  echo "Error: bundle no encontrado: $APP_PATH" >&2
  exit 1
fi

# ── Verificar plugin Qt Cocoa ─────────────────────────────────────────────
echo "Comprobando que el bundle incluye el plugin Qt (libqcocoa.dylib)..."
if ! "$PYTHON_BIN" "$ROOT_DIR/scripts/mas_embed_pyside6_bundle.py" "$APP_PATH"; then
  echo "Error: el .app no contiene libqcocoa.dylib; la app se cerrará al iniciar en sandbox." >&2
  exit 1
fi

# ── Limpiar sub-bundles y componentes incompatibles con MAS sandbox ───────
echo "Quitando herramientas Qt anidadas (Assistant/Designer/Linguist)..."
for _pyside_root in \
    "$APP_PATH/Contents/Frameworks/PySide6" \
    "$APP_PATH/Contents/Resources/PySide6"; do
  if [[ -d "$_pyside_root" ]]; then
    for _tool in Assistant Designer Linguist; do
      rm -rf "$_pyside_root/${_tool}.app" "$_pyside_root/${_tool}__dot__app"
    done
  fi
done

echo "Quitando Qt WebEngine / WebView / WebChannel del bundle..."
find "$APP_PATH/Contents/Frameworks" "$APP_PATH/Contents/Resources" \
  -type d \( -name 'QtWebEngine*.framework' -o -name 'QtWebView*.framework' -o -name 'QtWebChannel*.framework' \) \
  2>/dev/null | while IFS= read -r _fw; do rm -rf "$_fw"; done
find "$APP_PATH/Contents/Frameworks" "$APP_PATH/Contents/Resources" \
  -type d -name 'QtWebEngineProcess.app' 2>/dev/null | while IFS= read -r _hap; do rm -rf "$_hap"; done
for _pyside_root in \
    "$APP_PATH/Contents/Frameworks/PySide6" \
    "$APP_PATH/Contents/Resources/PySide6"; do
  if [[ -d "$_pyside_root" ]]; then
    rm -f "$_pyside_root"/QtWebEngine*.abi3.so "$_pyside_root"/QtWebEngine*.pyi 2>/dev/null || true
    rm -f "$_pyside_root"/QtWebView*.abi3.so "$_pyside_root"/QtWebView*.pyi 2>/dev/null || true
    rm -f "$_pyside_root"/QtWebChannel*.abi3.so "$_pyside_root"/QtWebChannel*.pyi 2>/dev/null || true
  fi
done

echo "Quitando Qt libexec y herramientas CLI (TestFlight 90885)..."
for _root in \
    "$APP_PATH/Contents/Frameworks/PySide6" \
    "$APP_PATH/Contents/Resources/PySide6"; do
  if [[ -d "$_root" ]]; then
    rm -rf "$_root/Qt/libexec"
    find "$_root" -maxdepth 1 -type f 2>/dev/null | while IFS= read -r _f; do
      case "$(file -b "$_f" 2>/dev/null)" in
        *Mach-O*executable*) rm -f "$_f" ;;
      esac
    done
  fi
done

echo "Quitando plugins Qt SQL (sqldrivers)..."
find "$APP_PATH/Contents/Frameworks" "$APP_PATH/Contents/Resources" \
  -type d -path '*/Qt/plugins/sqldrivers' 2>/dev/null | while IFS= read -r _sd; do rm -rf "$_sd"; done

remove_dead_symlinks_under "$APP_PATH"

# ── Info.plist ────────────────────────────────────────────────────────────
INFO_PLIST="$APP_PATH/Contents/Info.plist"

echo "Configurando bundle identifier: $BUNDLE_ID"
/usr/libexec/PlistBuddy -c "Set :CFBundleIdentifier $BUNDLE_ID" "$INFO_PLIST" 2>/dev/null || \
/usr/libexec/PlistBuddy -c "Add :CFBundleIdentifier string $BUNDLE_ID" "$INFO_PLIST"

echo "Configurando display name: $DISPLAY_NAME"
/usr/libexec/PlistBuddy -c "Set :CFBundleDisplayName $DISPLAY_NAME" "$INFO_PLIST" 2>/dev/null || \
/usr/libexec/PlistBuddy -c "Add :CFBundleDisplayName string $DISPLAY_NAME" "$INFO_PLIST"
/usr/libexec/PlistBuddy -c "Set :CFBundleName $DISPLAY_NAME" "$INFO_PLIST" 2>/dev/null || \
/usr/libexec/PlistBuddy -c "Add :CFBundleName string $DISPLAY_NAME" "$INFO_PLIST"

if [[ -n "$VERSION" ]]; then
  echo "Configurando versión: $VERSION"
  /usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString $VERSION" "$INFO_PLIST" 2>/dev/null || \
  /usr/libexec/PlistBuddy -c "Add :CFBundleShortVersionString string $VERSION" "$INFO_PLIST"
fi

if [[ -n "$BUILD_NUMBER" ]]; then
  echo "Configurando build number: $BUILD_NUMBER"
  /usr/libexec/PlistBuddy -c "Set :CFBundleVersion $BUILD_NUMBER" "$INFO_PLIST" 2>/dev/null || \
  /usr/libexec/PlistBuddy -c "Add :CFBundleVersion string $BUILD_NUMBER" "$INFO_PLIST"
fi

echo "Configurando categoría App Store: $CATEGORY_UTI"
/usr/libexec/PlistBuddy -c "Set :LSApplicationCategoryType $CATEGORY_UTI" "$INFO_PLIST" 2>/dev/null || \
/usr/libexec/PlistBuddy -c "Add :LSApplicationCategoryType string $CATEGORY_UTI" "$INFO_PLIST"

echo "Configurando versión mínima de macOS: $MIN_SYSTEM_VERSION"
/usr/libexec/PlistBuddy -c "Set :LSMinimumSystemVersion $MIN_SYSTEM_VERSION" "$INFO_PLIST" 2>/dev/null || \
/usr/libexec/PlistBuddy -c "Add :LSMinimumSystemVersion string $MIN_SYSTEM_VERSION" "$INFO_PLIST"

# ── Icono ─────────────────────────────────────────────────────────────────
if [[ "$SKIP_ICON" -eq 0 ]]; then
  if [[ ! -f "$ICON_SOURCE" ]]; then
    echo "Error: icono no encontrado: $ICON_SOURCE" >&2
    exit 1
  fi

  mkdir -p "$ROOT_DIR/build"
  ICONSET_TMP_DIR="$(mktemp -d "$ROOT_DIR/build/iconset.XXXXXX")"
  ICON_PNG="$ICONSET_TMP_DIR/icon_source.png"

  # Convertir SVG → PNG si es necesario
  if [[ "$ICON_SOURCE" == *.svg || "$ICON_SOURCE" == *.SVG ]]; then
    echo "Convirtiendo SVG a PNG: $ICON_SOURCE"
    "$PYTHON_BIN" "$ROOT_DIR/scripts/svg_to_png.py" "$ICON_SOURCE" "$ICON_PNG" 1024
  else
    ICON_PNG="$ICON_SOURCE"
  fi

  echo "Generando AppIcon.icns desde: $ICON_PNG"
  ICONSET_DIR="$ICONSET_TMP_DIR/AppIcon.iconset"
  mkdir -p "$ICONSET_DIR"

  sips -z 16   16   "$ICON_PNG" --out "$ICONSET_DIR/icon_16x16.png"      >/dev/null
  sips -z 32   32   "$ICON_PNG" --out "$ICONSET_DIR/icon_16x16@2x.png"   >/dev/null
  sips -z 32   32   "$ICON_PNG" --out "$ICONSET_DIR/icon_32x32.png"       >/dev/null
  sips -z 64   64   "$ICON_PNG" --out "$ICONSET_DIR/icon_32x32@2x.png"   >/dev/null
  sips -z 128  128  "$ICON_PNG" --out "$ICONSET_DIR/icon_128x128.png"     >/dev/null
  sips -z 256  256  "$ICON_PNG" --out "$ICONSET_DIR/icon_128x128@2x.png" >/dev/null
  sips -z 256  256  "$ICON_PNG" --out "$ICONSET_DIR/icon_256x256.png"     >/dev/null
  sips -z 512  512  "$ICON_PNG" --out "$ICONSET_DIR/icon_256x256@2x.png" >/dev/null
  sips -z 512  512  "$ICON_PNG" --out "$ICONSET_DIR/icon_512x512.png"     >/dev/null
  sips -z 1024 1024 "$ICON_PNG" --out "$ICONSET_DIR/icon_512x512@2x.png" >/dev/null

  mkdir -p "$APP_PATH/Contents/Resources"
  iconutil -c icns "$ICONSET_DIR" -o "$APP_PATH/Contents/Resources/AppIcon.icns"

  /usr/libexec/PlistBuddy -c "Set :CFBundleIconFile AppIcon" "$INFO_PLIST" 2>/dev/null || \
  /usr/libexec/PlistBuddy -c "Add :CFBundleIconFile string AppIcon" "$INFO_PLIST"
fi

# ── Perfil de provisioning ────────────────────────────────────────────────
echo "Incrustando perfil de provisioning..."
cp "$PROVISIONING_PROFILE" "$APP_PATH/Contents/embedded.provisionprofile"

clear_quarantine_attrs "$APP_PATH/Contents/Resources"
clear_quarantine_attrs "$APP_PATH/Contents/Frameworks"
clear_quarantine_attrs "$APP_PATH/Contents/embedded.provisionprofile"

# ── Entitlements desde el perfil ──────────────────────────────────────────
echo "Leyendo entitlements del perfil de provisioning..."
if ! security cms -D -i "$PROVISIONING_PROFILE" > "$PROFILE_PLIST_TMP" 2>/dev/null; then
  if ! openssl smime -inform der -verify -noverify -in "$PROVISIONING_PROFILE" \
      -out "$PROFILE_PLIST_TMP" >/dev/null 2>&1; then
    echo "Error: no se pudo decodificar el perfil de provisioning: $PROVISIONING_PROFILE" >&2
    exit 1
  fi
fi

PROFILE_APP_IDENTIFIER="$(/usr/libexec/PlistBuddy \
  -c "Print :Entitlements:com.apple.application-identifier" "$PROFILE_PLIST_TMP" 2>/dev/null || true)"
if [[ -z "$PROFILE_APP_IDENTIFIER" ]]; then
  PROFILE_APP_IDENTIFIER="$(/usr/libexec/PlistBuddy \
    -c "Print :ApplicationIdentifierPrefix:0" "$PROFILE_PLIST_TMP" 2>/dev/null || true).$BUNDLE_ID"
fi

PROFILE_TEAM_ID="$(/usr/libexec/PlistBuddy \
  -c "Print :Entitlements:com.apple.developer.team-identifier" "$PROFILE_PLIST_TMP" 2>/dev/null || true)"
if [[ -z "$PROFILE_TEAM_ID" ]]; then
  PROFILE_TEAM_ID="$(/usr/libexec/PlistBuddy \
    -c "Print :TeamIdentifier:0" "$PROFILE_PLIST_TMP" 2>/dev/null || true)"
fi

if [[ -z "$PROFILE_APP_IDENTIFIER" || -z "$PROFILE_TEAM_ID" ]]; then
  echo "Error: no se pudo extraer application/team identifier del perfil." >&2
  exit 1
fi

# ── Generar entitlements App Sandbox ─────────────────────────────────────
# PianoPilot no necesita red ni acceso a archivos del usuario;
# solo accede a dispositivos MIDI (CoreMIDI, permitido en sandbox).
echo "Generando entitlements App Sandbox..."
cat > "$ENTITLEMENTS_PATH" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>com.apple.application-identifier</key>
  <string>$PROFILE_APP_IDENTIFIER</string>
  <key>com.apple.developer.team-identifier</key>
  <string>$PROFILE_TEAM_ID</string>
  <key>com.apple.security.app-sandbox</key>
  <true/>
</dict>
</plist>
EOF

# ── Firma ─────────────────────────────────────────────────────────────────
clear_quarantine_attrs "$APP_PATH"
remove_dead_symlinks_under "$APP_PATH"

echo "Firmando app para Mac App Store..."
codesign --force --deep --timestamp \
  --entitlements "$ENTITLEMENTS_PATH" \
  --sign "$APP_DIST_IDENTITY" \
  "$APP_PATH"

echo "Verificando firma..."
if ! codesign --verify --deep --strict --verbose=2 "$APP_PATH"; then
  echo "codesign --verify falló. Buscando symlinks rotos..." >&2
  find "$APP_PATH" -type l ! -exec test -e {} \; -print 2>/dev/null | head -20 >&2 || true
  exit 1
fi

# ── Crear .pkg ────────────────────────────────────────────────────────────
echo "Creando paquete instalador firmado..."
rm -f "$OUTPUT_PKG"
productbuild \
  --component "$APP_PATH" /Applications \
  --sign "$INSTALLER_IDENTITY" \
  "$OUTPUT_PKG"

xattr -cr "$OUTPUT_PKG"
xattr -d com.apple.quarantine "$OUTPUT_PKG" 2>/dev/null || true

echo "Verificando firma del instalador..."
pkgutil --check-signature "$OUTPUT_PKG"

# ── Validación local (opcional) ───────────────────────────────────────────
if [[ "$SKIP_STORE_VALIDATION" -eq 0 ]]; then
  cat >&2 <<'EOF'
Ejecutando validación local (installer -store)…
Si no termina en 1-2 minutos, pulsa Ctrl+C — el .pkg ya está listo para subir con Transporter.
Re-ejecuta con --skip-store-validation para omitir este paso en el futuro.
EOF
  installer -store -pkg "$OUTPUT_PKG" -target /
else
  echo "Validación local omitida. Sube el .pkg con Transporter; Apple valida al recibirlo."
fi

echo
echo "✓ Listo."
echo "  App:          $APP_PATH"
echo "  Entitlements: $ENTITLEMENTS_PATH"
echo "  PKG:          $OUTPUT_PKG"
echo
echo "Siguiente paso: sube el .pkg con Transporter o Xcode Organizer."
