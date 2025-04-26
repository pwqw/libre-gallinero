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
pkg install -y root-repo
pkg upgrade -y
pkg install -y \
  git \
  python python-pip \
  termux-api termux-tools \
  pkg-config rust clang make \
  screen

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

# 5. Crear el entorno virtual (si no existe)
printf "\n\n🏗️  [5] Creando el entorno virtual (si no existe)... 🔨\n"
if [ ! -d "env" ]; then
  python -m venv env
fi

# 6. Activar el entorno virtual
printf "\n\n🚀 [6] Activando el entorno virtual... ⚡\n"
. "$HOME/libre-gallinero/env/bin/activate"

# 7. Asegurarnos de que rustc y cargo estén en el PATH
printf "\n\n🔍 [7] Verificando rustc y cargo en el PATH...\n"
export PATH="$PATH:$PREFIX/bin:$HOME/.cargo/bin"
if ! command -v rustc >/dev/null 2>&1; then
  echo "Error: rustc no encontrado en PATH"
  exit 1
fi
if ! command -v cargo >/dev/null 2>&1; then
  echo "Error: cargo no encontrado en PATH"
  exit 1
fi
echo "✅ rustc y cargo encontrados"

# 8. Instalar las dependencias del proyecto
printf "\n\n📦 [8] Instalando dependencias del proyecto... 🔧\n"
pip install --upgrade pip
pip install -r requirements.txt

# 9. Crear el acceso directo del script shortcut.sh para Termux-Widget
printf "\n\n[9] Creando acceso directo para Termux-Widget...\n"
if [ ! -d "$HOME/.shortcuts" ]; then
  mkdir -p "$HOME/.shortcuts"
fi
cp -f "$HOME/libre-gallinero/termux/shortcut.sh" "$HOME/.shortcuts/Grabar placa"
chmod +x "$HOME/.shortcuts/Grabar placa"
printf "\n\n🐔  ¡Listo! Puedes usar el widget 'Grabar placa' en Termux-Widget. 🐔\n"

