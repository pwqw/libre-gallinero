#!/usr/bin/env bash

# -*- coding: utf-8 -*-

# Script para subir archivos a ESP8266 vía USB Serial (ampy)
# Compatible con Mac y Linux

set -e  # Hacer que el script falle si hay un error
set -u  # Hacer que el script falle si se usa una variable no definida

# Banner
printf "╔════════════════════════════════════════╗\n"
printf "║       🐔  LIBRE GALLINERO  🐔          ║\n"
printf "║         GRABADOR DE PLACA              ║\n"
printf "║         (Mac/Linux - USB Serial)       ║\n"
printf "╚════════════════════════════════════════╝\n\n"

# Función para detectar el sistema operativo
detect_os() {
    case "$(uname -s)" in
        Darwin*)
            echo "macos"
            ;;
        Linux*)
            echo "linux"
            ;;
        *)
            echo "unknown"
            ;;
    esac
}

OS=$(detect_os)

# 2. Activar entorno virtual Python
if [ -d "env" ]; then
    . env/bin/activate
elif [ -d "../env" ]; then
    . ../env/bin/activate
else
    printf "⚠️  No se encontró el entorno virtual. Asegúrate de que esté creado y activado. ⚠️\n"
    printf "   Crea el entorno virtual con: python3 -m venv env\n"
    exit 1
fi

# 3. Detección de puertos serie según el sistema operativo
detect_ports() {
    local ports=()
    
    if [ "$OS" = "macos" ]; then
        # Mac: /dev/tty.usbserial-*, /dev/tty.wchusbserial*, /dev/cu.*
        while IFS= read -r port; do
            [ -n "$port" ] && ports+=("$port")
        done < <(printf '%s\n' /dev/tty.usbserial-* /dev/tty.wchusbserial* /dev/cu.usbserial-* /dev/cu.wchusbserial* 2>/dev/null | sort -u)
    elif [ "$OS" = "linux" ]; then
        # Linux: /dev/ttyUSB*, /dev/ttyACM*
        while IFS= read -r port; do
            [ -n "$port" ] && ports+=("$port")
        done < <(printf '%s\n' /dev/ttyUSB* /dev/ttyACM* 2>/dev/null | sort -u)
    fi
    
    printf '%s\n' "${ports[@]}"
}

# Detectar puertos disponibles
mapfile -t ports < <(detect_ports)

case "${#ports[@]}" in
    0)
        printf "🚫 No se encontraron puertos serie. Asegúrate de que la placa esté conectada 🔌\n"
        if [ "$OS" = "macos" ]; then
            printf "   En Mac, busca puertos en: /dev/tty.usbserial-* o /dev/tty.wchusbserial*\n"
        elif [ "$OS" = "linux" ]; then
            printf "   En Linux, busca puertos en: /dev/ttyUSB* o /dev/ttyACM*\n"
        fi
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

# Verificar que ampy esté instalado
if ! command -v ampy &> /dev/null; then
    printf "⚠️  ampy no está instalado. Instalando...\n"
    pip install adafruit-ampy
fi

# 4. Determinar directorio del proyecto
if [ -d "src" ]; then
    PROJECT_DIR="."
elif [ -d "../src" ]; then
    PROJECT_DIR=".."
else
    printf "⛔ No se encontró el directorio src/ ⚠️\n"
    exit 1
fi

cd "$PROJECT_DIR"

# 5. Sube recursivamente el contenido de src/ a la raíz de la placa
if [ -d src ]; then
    printf "📤 Subiendo archivos desde src/ a la placa ESP8266...\n\n"
    
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
        printf "📄 Subiendo: %s → %s\n" "$file" "$remote_file"
        ampy put "$file" "$remote_file" || {
            printf "⚠️  Error al subir %s\n" "$file"
        }
    done
    
    printf "\n✨ ¡Carga exitosa de src/ en la placa ESP8266! ✅\n\n"
    printf "🔄 Recuerda resetear la plaquita !!\n"
    printf "\n📊 Iniciando monitor serie (python serial.tools.miniterm 115200 baudios)\n"
    printf "Para salir: presiona Ctrl-]\n\n"
    
    python -m serial.tools.miniterm "${AMPY_PORT}" 115200
else
    printf "⛔ No se encontró el directorio src/ ⚠️\n"
    exit 1
fi


