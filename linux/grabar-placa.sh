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

# 1. Ir al directorio de libre-gallinero
cd "$HOME/libre-gallinero"

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
ampy put -r src . && {
  echo "✨ ¡Carga exitosa de src/ en la placa ESP8266! ✅"
  echo ""
  echo "📊 Iniciando monitor serie (115200 baudios)"
  echo "Para salir: presiona Ctrl-]"
  sleep 2
  python -m serial.tools.miniterm "${AMPY_PORT}" 115200
} || {
  echo "⛔ Error al grabar los archivos en la placa ⚠️"
}
