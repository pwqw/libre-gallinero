#!/data/data/com.termux/files/usr/bin/bash
# -*- coding: utf-8 -*-
# Shortcut para leer logs del ESP8266 en tiempo real

set -e
set -u

cd "$HOME/libre-gallinero"

printf "\n"
printf "╔════════════════════════════════════════╗\n"
printf "║       🐔  LIBRE GALLINERO  🐔          ║\n"
printf "║         LEER LOGS ESP8266              ║\n"
printf "╚════════════════════════════════════════╝\n"
printf "\n"

# Ejecutar script de logs
exec python3 tools/read_logs.py heladera
