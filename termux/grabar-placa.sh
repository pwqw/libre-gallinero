# -*- coding: utf-8 -*-

set -e  # Hacer que el script falle si hay un error
set -u  # Hacer que el script falle si se usa una variable no definida

echo "
╔════════════════════════════════════════╗
║       🐔  LIBRE GALLINERO  🐔          ║
║         GRABADOR DE PLACA              ║
╚════════════════════════════════════════╝
"

# 0. Ir al directorio de libre-gallinero
cd $HOME/libre-gallinero

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

# 3. Detección de puertos serie (POSIX o Termux)
if command -v termux-usb >/dev/null 2>&1; then
  echo "🔎 Detectando dispositivos USB con termux-usb..."
  devices=$(termux-usb -l | grep -o '"device": *"[^"]*"' | cut -d'"' -f4)
  if [ -z "$devices" ]; then
    echo "🚫 No se encontraron dispositivos USB. Conecta la placa y otorga permisos en Android."
    exit 1
  fi
  echo "Dispositivos USB detectados:"
  i=1
  for d in $devices; do
    letter=$(printf "\\$(printf '%03o' $((96 + i)))")
    echo "  $letter) $d"
    i=$((i + 1))
  done
  read -p "Elige el dispositivo a usar (a, b, c...): " choice
  choice=$(printf '%s' "$choice" | tr '[:upper:]' '[:lower:]')
  i=1
  for d in $devices; do
    letter=$(printf "\\$(printf '%03o' $((96 + i)))")
    if [ "$choice" = "$letter" ]; then
      USB_DEVICE=$d
      break
    fi
    i=$((i + 1))
  done
  [ -z "${USB_DEVICE:-}" ] && { echo "Selección inválida. Abortando."; exit 1; }

  # Solicitar acceso al dispositivo USB
  echo "Solicitando acceso a $USB_DEVICE..."
  termux-usb -r -e "$USB_DEVICE" &
  TERMUX_USB_PID=$!
  sleep 2

  # Buscar todos los dispositivos expuestos
  usb_devs=(/dev/bus/usb/*/*)
  if [ ${#usb_devs[@]} -eq 1 ]; then
    AMPY_PORT="${usb_devs[0]}"
  else
    echo "Dispositivos USB expuestos:"
    i=1
    for dev in "${usb_devs[@]}"; do
      letter=$(printf "\\$(printf '%03o' $((96 + i)))")
      echo "  $letter) $dev"
      i=$((i + 1))
    done
    read -p "Elige el dispositivo expuesto a usar (a, b, c...): " dev_choice
    dev_choice=$(printf '%s' "$dev_choice" | tr '[:upper:]' '[:lower:]')
    i=1
    for dev in "${usb_devs[@]}"; do
      letter=$(printf "\\$(printf '%03o' $((96 + i)))")
      if [ "$dev_choice" = "$letter" ]; then
        AMPY_PORT=$dev
        break
      fi
      i=$((i + 1))
    done
    [ -z "${AMPY_PORT:-}" ] && { echo "Selección inválida. Abortando."; kill "$TERMUX_USB_PID" 2>/dev/null; exit 1; }
  fi
  echo "🔍 Dispositivo USB expuesto como: $AMPY_PORT"
else
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
fi
export AMPY_PORT

# 4. Elegir método de grabación
echo
echo "¿Qué deseas hacer?"
echo "  1) Subir archivos Python (ampy)"
echo "  2) Flashear firmware (esptool.py)"
read -p "Elige una opción (1/2): " metodo

case "$metodo" in
  1)
    error=0
    for f in src/*.py; do
      if ! ampy put "$f"; then
        echo "⛔ Error al grabar el archivo $f en la placa ⚠️"
        error=1
      fi
    done
    if [ $error -eq 0 ]; then
      echo "✨ ¡Carga exitosa de src/ en la placa ESP8266! ✅"
      echo ""
      echo "📊 Iniciando monitor serie (115200 baudios)"
      echo "Para salir: presiona Ctrl+]"
      sleep 2
      python -m serial.tools.miniterm "$AMPY_PORT" 115200 --rts 0 --dtr 0
    else
      echo "⛔ Error al grabar uno o más archivos en la placa ⚠️"
    fi
    ;;
  2)
    read -p "Ruta al firmware .bin a flashear: " firmware
    if [ ! -f "$firmware" ]; then
      echo "Archivo no encontrado: $firmware"
      [ -n "${TERMUX_USB_PID:-}" ] && kill "$TERMUX_USB_PID" 2>/dev/null
      exit 1
    fi
    echo "Flasheando firmware con esptool.py..."
    esptool.py --port "$AMPY_PORT" write_flash 0x00000 "$firmware" && {
      echo "✅ Firmware flasheado correctamente."
    } || {
      echo "⛔ Error al flashear el firmware."
    }
    ;;
  *)
    echo "Opción inválida. Abortando."
    [ -n "${TERMUX_USB_PID:-}" ] && kill "$TERMUX_USB_PID" 2>/dev/null
    exit 1
    ;;
esac

# Limpieza de proceso termux-usb si corresponde
[ -n "${TERMUX_USB_PID:-}" ] && kill "$TERMUX_USB_PID" 2>/dev/null
