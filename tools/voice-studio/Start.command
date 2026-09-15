#!/bin/bash
set -e
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  echo 'Avval Install.command faylini oching.'
  read -r -p 'Yopish uchun Enter bosing.'
  exit 1
fi
.venv/bin/python launch.py
