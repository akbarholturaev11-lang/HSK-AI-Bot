#!/bin/bash
set -e
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  PYTHON=$(command -v python3.11 || command -v python3)
  "$PYTHON" -m venv .venv
fi
.venv/bin/python -m pip install --index-url https://pypi.org/simple -r requirements.txt
.venv/bin/python download_models.py
printf '\nTayyor. Endi Start.command faylini oching.\n'
read -r -p 'Yopish uchun Enter bosing.'
