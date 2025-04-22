# Script para ejecutar en android

# 0. Iniciar
cd $HOME

# 1. Instalar las dependencias necesarias
pkg update -y
pkg install -y root-repo
pkg upgrade -y
pkg install -y git python python-pip termux-api termux-tools 

# 2. Clonar el repositorio libre-gallinero (si no existe)
if [ ! -d "libre-gallinero" ]; then
  git clone https://github.com/pwqw/libre-gallinero.git
fi

# 3. Navegar al directorio del repositorio
cd libre-gallinero

# 4. Actualizar el repositorio (forzado)
git fetch --all
git reset --hard origin/$(git rev-parse --abbrev-ref HEAD)

# 5. Crear el entorno virtual (si no existe)
if [ ! -d "env" ]; then
  python -m venv env
fi

# 6. Activar el entorno virtual
source env/bin/activate

# 7. Instalar las dependencias del proyecto
pip install --upgrade pip
pip install -r requirements.txt

# 8. Notificación de éxito
termux-toast "Entorno listo para libre-gallinero"

# 9. Crear el acceso directo del script grabar-placa.sh para Termux-Widget
if [ ! -d "$HOME/.shortcuts" ]; then
  mkdir -p "$HOME/.shortcuts"
fi
cp -f $HOME/libre-gallinero/grabar-placa.sh "$HOME/.shortcuts/Grabar placa"
chmod +x "$HOME/.shortcuts/Grabar placa"

