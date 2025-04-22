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
git pull --rebase

# 1. Confirmación para conectar la placa
read -p "Conecta la placa ESP8266 y presiona 'S' para continuar, o cualquier otra tecla para cancelar: " confirmacion
if [ "$confirmacion" != "S" ] && [ "$confirmacion" != "s" ]; then
  echo "❌ Cancelado por el usuario ❌"
  exit 0
fi

# 2. Source python env
if [ -d "env" ]; then
  . env/bin/activate
else
  echo "⚠️ No se encontró el entorno virtual. Asegúrate de que esté creado y activado. ⚠️"
  exit 1
fi

# 3. Buscar puertos serie disponibles en Android/Termux
# Generalmente son /dev/ttyUSB*, /dev/ttyACM*, /dev/ttyS*, /dev/tty.*
puertos=(/dev/ttyUSB* /dev/ttyACM* /dev/ttyS* /dev/tty.*)
puertos_disponibles=()
for p in "${puertos[@]}"; do
  if [ -e "$p" ]; then
    puertos_disponibles+=("$p")
  fi
done

if [ ${#puertos_disponibles[@]} -eq 0 ]; then
  echo "🚫 No se encontraron puertos serie. Asegúrate de que la placa esté conectada 🔌"
  exit 1
fi

# 4. Selección automática o manual del puerto
if [ ${#puertos_disponibles[@]} -eq 1 ]; then
  AMPY_PORT="${puertos_disponibles[0]}"
  echo "🔍 Puerto detectado automáticamente: $AMPY_PORT ✅"
else
  echo "Puertos serie detectados:"
  letras=(a b c d e f g h i j)
  for i in "${!puertos_disponibles[@]}"; do
    echo "  ${letras[$i]}) ${puertos_disponibles[$i]}"
  done
  read -p "Elige el puerto a usar (a, b, c...): " eleccion
  idx=-1
  for i in "${!letras[@]}"; do
    if [ "$eleccion" = "${letras[$i]}" ]; then
      idx=$i
      break
    fi
  done
  if [ $idx -lt 0 ] || [ $idx -ge ${#puertos_disponibles[@]} ]; then
    echo "Selección inválida. Abortando."
    exit 1
  fi
  AMPY_PORT="${puertos_disponibles[$idx]}"
fi

export AMPY_PORT

# 5. Sube recursivamente el contenido de src/ a la raíz de la placa
ampy put -r src .

if [ $? -eq 0 ]; then
  echo "✨ ¡Carga exitosa de src/ en la placa ESP8266! ✅"
else
  echo "⛔ Error al grabar los archivos en la placa ⚠️"
fi
