#!/usr/bin/env bash
# -*- coding: utf-8 -*-

set -e  # Hacer que el script falle si hay un error
set -u  # Hacer que el script falle si se usa una variable no definida

# Banner
cat <<EOF
╔════════════════════════════════════════╗
║       🐔  LIBRE GALLINERO  🐔          ║
║         GRABADOR DE PLACA              ║
╚════════════════════════════════════════╝
EOF

# 2. Activar entorno virtual Python
if [ -d "env" ]; then
  . env/bin/activate
else
  echo "⚠️ No se encontró el entorno virtual. Asegúrate de que esté creado y activado. ⚠️"
  exit 1
fi

# 3. Detección de puertos serie en un array
mapfile -t ports < <(printf '%s
' /dev/ttyUSB* /dev/ttyACM* /dev/ttyS* \
                    /dev/tty.usbserial* /dev/tty.usbmodem* /dev/tty.SLAB_USBtoUART* \
                    2>/dev/null)

case "${#ports[@]}" in
  0)
    echo "🚫 No se encontraron puertos serie. Asegúrate de que la placa esté conectada 🔌"
    exit 1
    ;;
  1)
    AMPY_PORT=${ports[0]}
    echo "🔍 Puerto detectado automáticamente: $AMPY_PORT ✅"
    ;;
  *)
    echo "Puertos serie detectados:"
    PS3="Elige el puerto a usar: "
    select AMPY_PORT in "${ports[@]}"; do
      [[ -n $AMPY_PORT ]] && break
      echo "Selección inválida."
    done
    ;;
esac
export AMPY_PORT

# 4. Sube recursivamente el contenido de src/ a la raíz de la placa
if [ -d src ]; then
  # Subir directorios vacíos primero
  find src -type d | while read -r dir; do
    remote_dir="${dir#src/}"
    [ -z "$remote_dir" ] && continue
    ampy mkdir "$remote_dir" 2>/dev/null || true
  done
  # Subir archivos
  find src -type f | while read -r file; do
    remote_file="${file#src/}"
    ampy put "$file" "$remote_file"
  done
  echo "✨ ¡Carga exitosa de src/ en la placa ESP8266! ✅"
  echo ""
  echo "📊 Iniciando monitor serie (python serial.tools.miniterm 115200 baudios)"
  echo "Para salir: presiona Ctrl-]"
  sleep 2
  python -m serial.tools.miniterm "${AMPY_PORT}" 115200
else
  echo "⛔ No se encontró el directorio src/ ⚠️"
fi
