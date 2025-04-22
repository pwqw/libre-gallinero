#!/data/data/com.termux/files/usr/bin/bash

echo "
╔════════════════════════════════════════╗
║       🐔  LIBRE GALLINERO  🐔          ║
║            CONFIGURACIÓN               ║
╚════════════════════════════════════════╝
"

set -e  # Hacer que el script falle si hay un error
set -u  # Hacer que el script falle si se usa una variable no definida

# 0. Iniciar
cd $HOME

# 1. Instalar las dependencias necesarias
echo "\n📦 [1] Instalando dependencias necesarias... 🔧"
pkg update -y
pkg install -y root-repo
pkg upgrade -y
pkg install -y git python python-pip termux-api termux-tools 

# 2. Clonar el repositorio libre-gallinero (si no existe)
echo "\n\n📥 [2] Clonando el repositorio libre-gallinero (si no existe)... 🔄"
if [ ! -d "libre-gallinero" ]; then
  git clone https://github.com/pwqw/libre-gallinero.git
fi

# 3. Navegar al directorio del repositorio
echo "\n\n📂 [3] Navegando al directorio del repositorio... 🚀"
cd libre-gallinero

# 4. Actualizar el repositorio (forzado)
echo "\n\n🔄 [4] Actualizando el repositorio (forzado)... ⚡"
git fetch --all
git reset --hard origin/$(git rev-parse --abbrev-ref HEAD)

# 5. Crear el entorno virtual (si no existe)
echo "\n\n🏗️  [5] Creando el entorno virtual (si no existe)... 🔨"
if [ ! -d "env" ]; then
  python -m venv env
fi

# 6. Activar el entorno virtual
echo "\n\n🚀 [6] Activando el entorno virtual... ⚡"
source env/bin/activate

# 7. Instalar las dependencias del proyecto
echo "\n\n📦 [7] Instalando dependencias del proyecto... 🔧"
pip install --upgrade pip
pip install -r requirements.txt

# 8. Crear el acceso directo del script grabar-placa.sh para Termux-Widget
echo "\n\n[8] Creando acceso directo para Termux-Widget..."
if [ ! -d "$HOME/.shortcuts" ]; then
  mkdir -p "$HOME/.shortcuts"
fi
cp -f $HOME/libre-gallinero/grabar-placa.sh "$HOME/.shortcuts/Grabar placa"
chmod +x "$HOME/.shortcuts/Grabar placa"
echo "\n\n🐔  ¡Listo! Puedes usar el widget 'Grabar placa' en Termux-Widget. 🐔\n"

