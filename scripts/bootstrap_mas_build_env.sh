#!/usr/bin/env bash
# Crea un virtualenv limpio para builds Mac App Store.
set -euo pipefail

usage() {
  cat <<'EOF'
Crea un virtualenv limpio para builds Mac App Store de PianoPilot.

Uso:
  scripts/bootstrap_mas_build_env.sh [--python /path/to/python3.11] [--venv .venv-mas]

Opciones:
  --python  Binario Python a usar. Defecto:
            /Library/Frameworks/Python.framework/Versions/3.11/bin/python3.11
  --venv    Directorio del virtualenv. Defecto: .venv-mas
  -h, --help
EOF
}

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="/Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13"
VENV_DIR="$ROOT_DIR/.venv-mas"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --python)
      PYTHON_BIN="${2:-}"
      shift 2
      ;;
    --venv)
      VENV_DIR="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Argumento desconocido: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Error: Python no encontrado o no ejecutable: $PYTHON_BIN" >&2
  echo "  Instala Python 3.11 desde python.org (no Homebrew) para builds MAS estables." >&2
  exit 1
fi

py_ver="$("$PYTHON_BIN" -c 'import sys; print(sys.version.split()[0])')"
echo "Usando Python: $PYTHON_BIN"
echo "Versión: $py_ver"

if [[ ! -d "$VENV_DIR" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/python" -m pip install --upgrade pip setuptools wheel
"$VENV_DIR/bin/python" -m pip install -e "$ROOT_DIR"
"$VENV_DIR/bin/python" -m pip install pyinstaller pyinstaller-hooks-contrib

echo
echo "Listo."
echo "Virtualenv: $VENV_DIR"
echo "Python:     $VENV_DIR/bin/python"
echo
echo "Próximo paso:"
echo "  1) cp scripts/mas-env.example signing/local/mas.env"
echo "  2) Edita signing/local/mas.env"
echo "  3) ./scripts/build_mas_store.sh"
