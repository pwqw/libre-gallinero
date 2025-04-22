# Script para ejecutar en android

# 0. Iniciar
cd $HOME

# 1. Instalar las dependencias necesarias
pkg update -y
pkg install -y root-repo
pkg upgrade -y
pkg install -y git python3 python3-pip termux-api termux-widget termux-tools termux-toast

# 2. Clonar el repositorio libre-gallina (si no existe)
if [ ! -d "libre-gallina" ]; then
  git clone https://github.com/pwqw/libre-gallina
fi

# 3. Navegar al directorio del repositorio
cd libre-gallina

# 4. Actualizar el repositorio
git pull --rebase

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
termux-toast "Entorno listo para libre-gallina"

# 9. Crear el acceso directo del script grabar-placa.sh para Termux-Widget
if [ ! -d "$HOME/.shortcuts" ]; then
  mkdir -p "$HOME/.shortcuts"
fi
cp -f $HOME/libre-gallina/grabar-placa.sh "$HOME/.shortcuts/Grabar placa"
chmod +x "$HOME/.shortcuts/Grabar placa"

