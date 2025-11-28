#!/data/data/com.termux/files/usr/bin/bash
# Shortcut para limpiar ESP8266 desde Termux
# Uso: ./termux/clean.sh

cd "$(dirname "$0")/.." || exit 1
python3 tools/clean_esp8266.py
