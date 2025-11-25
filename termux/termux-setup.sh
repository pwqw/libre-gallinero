#!/data/data/com.termux/files/usr/bin/bash
# -*- coding: utf-8 -*-
printf "
╔════════════════════════════════════════╗
║       🐔  LIBRE GALLINERO  🐔          ║
║            CONFIGURACIÓN               ║
╚════════════════════════════════════════╝
\n"

set -e  # Hacer que el script falle si hay un error
set -u  # Hacer que el script falle si se usa una variable no definida

# 0. Iniciar
cd "$HOME"

# 1. Instalar las dependencias necesarias
printf "\n📦 [1] Instalando dependencias necesarias... 🔧\n"
pkg update -y
pkg upgrade -y
pkg install -y \
  git \
  python \
  termux-api termux-tools

# 2. Clonar el repositorio libre-gallinero (si no existe)
printf "\n\n📥 [2] Clonando el repositorio libre-gallinero (si no existe)... 🔄\n"
if [ ! -d "$HOME/libre-gallinero" ]; then
  git clone https://github.com/pwqw/libre-gallinero.git "$HOME/libre-gallinero"
fi

# 3. Navegar al directorio del repositorio
printf "\n\n📂 [3] Navegando al directorio del repositorio... 🚀\n"
cd "$HOME/libre-gallinero"

# 4. Actualizar el repositorio (forzado)
printf "\n\n🔄 [4] Actualizando el repositorio (forzado)... ⚡\n"
git fetch --all
git reset --hard origin/$(git rev-parse --abbrev-ref HEAD)

# 5. Verificar que Python3 esté disponible
printf "\n\n🐍 [5] Verificando Python3...\n"
if ! command -v python3 >/dev/null 2>&1; then
  echo "❌ Error: python3 no encontrado"
  exit 1
fi
echo "✅ Python3 encontrado: $(python3 --version)"

# 6. Instalar dependencias Python para WebREPL
printf "\n\n📦 [6] Instalando dependencias Python (websocket-client)...\n"
pip install websocket-client

# 7. Crear los accesos directos para Termux-Widget
printf "\n\n🔗 [7] Creando accesos directos para Termux-Widget...\n"
if [ ! -d "$HOME/.shortcuts" ]; then
  mkdir -p "$HOME/.shortcuts"
fi
cp -f "$HOME/libre-gallinero/termux/shortcuts/deploy.sh" "$HOME/.shortcuts/Deploy ESP8266"
chmod +x "$HOME/.shortcuts/Deploy ESP8266"
cp -f "$HOME/libre-gallinero/termux/shortcuts/setup.sh" "$HOME/.shortcuts/Update Setup"
chmod +x "$HOME/.shortcuts/Update Setup"
cp -f "$HOME/libre-gallinero/termux/shortcuts/deploy-test.sh" "$HOME/.shortcuts/Desplegar Prueba"
chmod +x "$HOME/.shortcuts/Desplegar Prueba"

printf "\n\n✅ ¡Setup completo!\n\n"
printf "📋 Próximos pasos:\n"
printf "  1. En PC/Mac: Flashear MicroPython en ESP8266 (solo primera vez)\n"
printf "  2. En PC/Mac: Configurar WebREPL y conectar ESP8266 a WiFi\n"
printf "  3. Configurar .env con WEBREPL_IP y WEBREPL_PASSWORD\n"
printf "  4. Ejecutar: python3 tools/deploy_wifi.py\n"
printf "     o usar el shortcut 'Deploy ESP8266' en Termux Widget\n\n"
printf "📖 Ver guía completa: docs/INSTALLATION.md\n\n"
