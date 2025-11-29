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

# 1. Clonar el repositorio libre-gallinero (si no existe)
printf "\n📥 [1] Clonando el repositorio libre-gallinero (si no existe)... 🔄\n"
if [ ! -d "$HOME/libre-gallinero" ]; then
  git clone https://github.com/pwqw/libre-gallinero.git "$HOME/libre-gallinero"
fi

# 2. Navegar al directorio del repositorio y actualizar (forzado)
printf "\n\n🔄 [2] Actualizando el repositorio (forzado)... ⚡\n"
cd "$HOME/libre-gallinero"
git fetch --all
git reset --hard origin/$(git rev-parse --abbrev-ref HEAD)

# 3. Crear los accesos directos para Termux-Widget
printf "\n\n🔗 [3] Creando accesos directos para Termux-Widget...\n"
if [ ! -d "$HOME/.shortcuts" ]; then
  mkdir -p "$HOME/.shortcuts"
fi

# Copiar TODOS los shortcuts del directorio (los nombres ya están correctos)
cp -f "$HOME/libre-gallinero/termux/shortcuts/"* "$HOME/.shortcuts/"
chmod +x "$HOME/.shortcuts/"*

printf "   ✓ Todos los shortcuts copiados a ~/.shortcuts/\n"

# 4. Instalar las dependencias necesarias
printf "\n\n📦 [4] Instalando dependencias necesarias... 🔧\n"
pkg update -y
pkg upgrade -y
pkg install -y \
  git \
  python \
  termux-api termux-tools

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

printf "\n\n✅ ¡Setup completo!\n\n"
printf "📋 Shortcuts instalados en Termux Widget:\n"
printf "  • Update Setup       - Actualiza el repositorio y dependencias\n"
printf "  • Abrir REPL         - Abre REPL interactivo del ESP8266\n"
printf "  • Ver Logs           - Lee logs en tiempo real (NUEVO)\n"
printf "  • Limpiar ESP8266    - Limpia archivos del ESP8266\n"
printf "  • Deploy Blink       - Despliega app Blink (LED test)\n"
printf "  • Deploy Gallinero   - Despliega app Gallinero (producción)\n"
printf "  • Deploy Heladera    - Despliega app Heladera (experimental)\n\n"
printf "💡 Los shortcuts de deploy usan caché de IPs para conexión rápida.\n"
printf "   Primera ejecución: escanea red (~10-30s)\n"
printf "   Siguientes: usa IP cacheada (~2s)\n\n"
printf "📋 Próximos pasos:\n"
printf "  1. En PC/Mac: Flashear MicroPython en ESP8266 (solo primera vez)\n"
printf "  2. En PC/Mac: Configurar WebREPL y conectar ESP8266 a WiFi\n"
printf "  3. Configurar .env con WEBREPL_IP y WEBREPL_PASSWORD\n"
printf "  4. Usar shortcuts de Termux Widget para deployar apps\n\n"
printf "📖 Ver guía completa: docs/INSTALLATION.md\n\n"
