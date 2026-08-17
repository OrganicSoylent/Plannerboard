#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Creating virtual environment..."
python3 -m venv "$SCRIPT_DIR/.venv"

echo "==> Installing dependencies..."
"$SCRIPT_DIR/.venv/bin/pip" install --upgrade pip -q
"$SCRIPT_DIR/.venv/bin/pip" install -r "$SCRIPT_DIR/requirements.txt"

echo ""
echo "Setup complete."
echo "Run the app with:"
echo "  $SCRIPT_DIR/.venv/bin/python $SCRIPT_DIR/run.py"
echo ""
echo "To enable autostart, open the app → File → Settings → enable 'Launch on login'."
