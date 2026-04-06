#!/usr/bin/env bash
# Carga signing/local/mas.env y ejecuta build_mas_pkg.sh para Mac App Store.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${MAS_ENV_FILE:-$ROOT_DIR/signing/local/mas.env}"

if [[ ! -f "$ENV_FILE" ]]; then
  cat >&2 <<EOF
No se encuentra: $ENV_FILE

Pasos:
  1) cp scripts/mas-env.example signing/local/mas.env
  2) Edita signing/local/mas.env  (identidades, bundle id, perfil, versión, build)
  3) Vuelve a ejecutar: ./scripts/build_mas_store.sh

Para ver tus identidades de firma:
  security find-identity -v -p codesigning
EOF
  exit 1
fi

# shellcheck disable=SC1090
source "$ENV_FILE"

: "${MAS_APP_DIST_IDENTITY:?Definir MAS_APP_DIST_IDENTITY en mas.env}"
: "${MAS_INSTALLER_IDENTITY:?Definir MAS_INSTALLER_IDENTITY en mas.env}"
: "${MAS_BUNDLE_ID:?Definir MAS_BUNDLE_ID en mas.env}"
: "${MAS_PROVISIONING_PROFILE:?Definir MAS_PROVISIONING_PROFILE en mas.env}"

EXTRA=()
[[ -n "${MAS_VERSION:-}"      ]] && EXTRA+=(--version       "$MAS_VERSION")
[[ -n "${MAS_BUILD_NUMBER:-}" ]] && EXTRA+=(--build-number  "$MAS_BUILD_NUMBER")

# installer -store suele colgarse; Transporter valida al subir el .pkg.
[[ "${MAS_SKIP_STORE_VALIDATION:-1}" == "1" ]] && EXTRA+=(--skip-store-validation)
[[ "${MAS_SKIP_BUILD:-0}"            == "1" ]] && EXTRA+=(--skip-build)

exec "$ROOT_DIR/scripts/build_mas_pkg.sh" \
  --app-dist-identity    "$MAS_APP_DIST_IDENTITY" \
  --installer-identity   "$MAS_INSTALLER_IDENTITY" \
  --bundle-id            "$MAS_BUNDLE_ID" \
  --provisioning-profile "$MAS_PROVISIONING_PROFILE" \
  "${EXTRA[@]}"
