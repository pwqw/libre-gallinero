#!/data/data/com.termux/files/usr/bin/bash
# -*- coding: utf-8 -*-
# Shortcut para deployar app "heladera" via WiFi
# Usa caché de IPs para acelerar el descubrimiento

set -e
set -u

cd "$HOME/libre-gallinero"

printf "\n"
printf "╔════════════════════════════════════════╗\n"
printf "║       🐔  LIBRE GALLINERO  🐔          ║\n"
printf "║      DEPLOY: HELADERA APP              ║\n"
printf "╚════════════════════════════════════════╝\n"
printf "\n"

# Actualizar repo y ejecutar deploy
exec python3 tools/deploy_app.py heladera
