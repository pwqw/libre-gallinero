# -*- coding: utf-8 -*-

set -e  # Hacer que el script falle si hay un error
set -u  # Hacer que el script falle si se usa una variable no definida

echo "
╔════════════════════════════════════════╗
║       🐔  LIBRE GALLINERO  🐔          ║
║         GRABADOR DE PLACA              ║
╚════════════════════════════════════════╝
"

# Dependencias mínimas
for cmd in git python3 ampy screen; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "⚠️  '$cmd' no encontrado. Instálalo con: pkg install $cmd"
    exit 1
  fi
done

# 0. Ir al directorio de libre-gallinero
cd $HOME/libre-gallinero
git pull --rebase

# 1. Confirmación para conectar la placa
read -p "Conecta la placa ESP8266 y presiona 'S' para continuar, o cualquier otra tecla para cancelar: " confirmacion
case "${confirmacion:-}" in
  [Ss]) ;; 
  *) echo "❌ Cancelado por el usuario ❌"; exit 0 ;; 
esac

# 2. Source python env
if [ -d "env" ]; then
  . env/bin/activate
else
  echo "⚠️ No se encontró el entorno virtual. Asegúrate de que esté creado y activado. ⚠️"
  exit 1
fi

# 3. Detección de puertos serie (POSIX)
ports=$(ls /dev/ttyUSB* /dev/ttyACM* /dev/ttyS* /dev/tty.* 2>/dev/null || true)
if [ -z "$ports" ]; then
  echo "🚫 No se encontraron puertos serie. Asegúrate de que la placa esté conectada 🔌"
  exit 1
fi
set -- $ports
if [ "$#" -eq 1 ]; then
  AMPY_PORT=$1
  echo "🔍 Puerto detectado automáticamente: $AMPY_PORT ✅"
else
  echo "Puertos serie detectados:"
  i=1
  for p in "$@"; do
    letter=$(printf "\\$(printf '%03o' $((96 + i)))")
    echo "  $letter) $p"
    i=$((i + 1))
  done
  read -p "Elige el puerto a usar (a, b, c...): " choice
  choice=$(printf '%s' "$choice" | tr '[:upper:]' '[:lower:]')
  i=1
  for p in "$@"; do
    letter=$(printf "\\$(printf '%03o' $((96 + i)))")
    if [ "$choice" = "$letter" ]; then
      AMPY_PORT=$p
      break
    fi
    i=$((i + 1))
  done
  [ -z "${AMPY_PORT:-}" ] && { echo "Selección inválida. Abortando."; exit 1; }
fi
export AMPY_PORT

# 4. Sube recursivamente el contenido de src/ a la raíz de la placa
ampy put -r src . && {
  echo "✨ ¡Carga exitosa de src/ en la placa ESP8266! ✅"
  echo ""
  echo "📊 Iniciando monitor serie (115200 baudios)"
  echo "Para salir: presiona Ctrl+A seguido de Ctrl+\\"
  sleep 2
  screen -T vt100 "$AMPY_PORT" 115200
} || {
  echo "⛔ Error al grabar los archivos en la placa ⚠️"
}
