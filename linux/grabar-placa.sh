#!/usr/bin/env bash
# -*- coding: utf-8 -*-

set -e  # Hacer que el script falle si hay un error
set -u  # Hacer que el script falle si se usa una variable no definida

# Banner
printf "╔════════════════════════════════════════╗\n"
printf "║       🐔  LIBRE GALLINERO  🐔          ║\n"
printf "║         GRABADOR DE PLACA              ║\n"
printf "╚════════════════════════════════════════╝\n\n"

# 2. Activar entorno virtual Python
if [ -d "env" ]; then
  . env/bin/activate
else
  printf "⚠️ No se encontró el entorno virtual. Asegúrate de que esté creado y activado. ⚠️\n"
  exit 1
fi

# 3. Detección de puertos serie en un array
mapfile -t ports < <(printf '%s' /dev/ttyUSB* 2>/dev/null)

case "${#ports[@]}" in
  0)
    printf "🚫 No se encontraron puertos serie. Asegúrate de que la placa esté conectada 🔌\n"
    exit 1
    ;;
  1)
    AMPY_PORT=${ports[0]}
    printf "🔍 Puerto detectado automáticamente: %s ✅\n" "$AMPY_PORT"
    ;;
  *)
    printf "Puertos serie detectados:\n"
    PS3="Elige el puerto a usar: "
    select AMPY_PORT in "${ports[@]}"; do
      [[ -n $AMPY_PORT ]] && break
      printf "Selección inválida.\n"
    done
    ;;
esac
export AMPY_PORT

# 4. Sube recursivamente el contenido de src/ a la raíz de la placa
if [ -d src ]; then
  # Subir directorios vacíos primero, excluyendo __pycache__
  find src -type d \
    -not -path "*/__pycache__*" | while read -r dir; do
    remote_dir="${dir#src/}"
    [ -z "$remote_dir" ] && continue
    ampy mkdir "$remote_dir" 2>/dev/null || true
  done
  # Subir archivos, excluyendo __pycache__ y archivos .pyc
  find src -type f \
    -not -path "*/__pycache__*" \
    -not -name '*.pyc' | while read -r file; do
    remote_file="${file#src/}"
    ampy put "$file" "$remote_file"
  done
  printf "\n✨ ¡Carga exitosa de src/ en la placa ESP8266! ✅\n\n"
  printf "🔄 Recuerda resetear la plaquita !!\n"
  printf "\n📊 Iniciando monitor serie (python serial.tools.miniterm 115200 baudios)\n"
  printf "Para salir: presiona Ctrl-]\n\n"
  python -m serial.tools.miniterm "${AMPY_PORT}" 115200
else
  printf "⛔ No se encontró el directorio src/ ⚠️\n"
fi