#!/usr/bin/env python3
"""
Script consolidado para subir archivos a ESP8266 vía USB Serial (ampy).

Uso:
    # Deploy base + app por defecto (blink):
    python3 tools/deploy_usb.py

    # Deploy base + app específica:
    python3 tools/deploy_usb.py gallinero
    python3 tools/deploy_usb.py heladera

Requiere:
    pip install adafruit-ampy pyserial
"""

import sys
import os
import platform
import subprocess
import glob
from pathlib import Path

# Agregar tools/common al path
script_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(script_dir))

from common.env_updater import update_env_for_app, cleanup_temp_env

# Colores para terminal
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'


def print_banner():
    """Imprime el banner del script"""
    print("╔════════════════════════════════════════╗")
    print("║       🐔  LIBRE GALLINERO  🐔          ║")
    print("║         GRABADOR DE PLACA              ║")
    print("║      (Windows/Mac/Linux - USB Serial)  ║")
    print("╚════════════════════════════════════════╝")
    print()


def detect_os():
    """Detecta el sistema operativo"""
    system = platform.system().lower()
    if system == 'darwin':
        return 'macos'
    elif system == 'linux':
        return 'linux'
    elif system == 'windows':
        return 'windows'
    return 'unknown'


def find_serial_ports():
    """Encuentra puertos serie disponibles según el sistema operativo"""
    os_type = detect_os()
    ports = []
    
    if os_type == 'macos':
        patterns = [
            '/dev/tty.usbserial-*',
            '/dev/tty.wchusbserial*',
            '/dev/cu.usbserial-*',
            '/dev/cu.wchusbserial*',
        ]
    elif os_type == 'linux':
        patterns = [
            '/dev/ttyUSB*',
            '/dev/ttyACM*',
        ]
    elif os_type == 'windows':
        try:
            import serial.tools.list_ports
            ports_list = serial.tools.list_ports.comports()
            ports = [port.device for port in ports_list]
            return ports
        except ImportError:
            print(f"{YELLOW}⚠️  pyserial no instalado. Instalando...{NC}")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyserial'])
            import serial.tools.list_ports
            ports_list = serial.tools.list_ports.comports()
            ports = [port.device for port in ports_list]
            return ports
    else:
        print(f"{RED}⚠️  Sistema operativo no soportado: {os_type}{NC}")
        return []
    
    # Buscar puertos usando glob
    for pattern in patterns:
        found = glob.glob(pattern)
        ports.extend(found)
    
    # Eliminar duplicados y ordenar
    ports = sorted(list(set(ports)))
    return ports


def check_ampy_installed():
    """Verifica si ampy está instalado"""
    try:
        import ampy.cli
        return True
    except ImportError:
        return False


def install_ampy():
    """Instala ampy si no está disponible"""
    print(f"{YELLOW}⚠️  ampy no está instalado. Instalando...{NC}")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'adafruit-ampy', 'pyserial'])
        print(f"{GREEN}✅ ampy instalado correctamente{NC}\n")
        return True
    except subprocess.CalledProcessError:
        print(f"{RED}❌ Error al instalar ampy{NC}")
        return False


def find_project_root():
    """Encuentra la raíz del proyecto (donde está src/)"""
    script_dir = Path(__file__).parent.absolute()
    project_dir = script_dir.parent
    
    if (project_dir / 'src').exists():
        return project_dir
    
    # Fallback: buscar desde directorio actual
    current = Path.cwd()
    for path in [current, current.parent]:
        if (path / 'src').exists():
            return path
    
    return None


def get_files_to_upload_usb(project_root, app_name=None):
    """
    Obtiene lista de archivos a subir desde src/.
    Similar a deploy_wifi.py pero para USB/ampy.
    
    Args:
        project_root: Directorio raíz del proyecto
        app_name: Nombre de la app a incluir (blink, gallinero, heladera, etc.)
    
    Returns:
        list: Lista de tuplas (local_path, remote_name) o (None, "mkdir:dirname") para directorios
    """
    src_dir = project_root / 'src'
    files = []
    
    # Base modules
    main_files = ['boot.py', 'main.py', 'config.py', 'wifi.py', 'ntp.py', 'app_loader.py']
    for filename in main_files:
        local_path = src_dir / filename
        if local_path.exists():
            files.append((str(local_path), filename))
    
    # App-specific files
    if app_name:
        app_dir_path = src_dir / app_name
        if app_dir_path.exists() and app_dir_path.is_dir():
            print(f"{BLUE}📦 Incluyendo archivos de la app: {app_name}{NC}")
            
            # Create app directory
            files.append((None, f"mkdir:{app_name}"))
            
            # Upload __init__.py first
            init_file = app_dir_path / '__init__.py'
            if init_file.exists():
                remote_name = f"{app_name}/__init__.py"
                files.append((str(init_file), remote_name))
            
            # Upload other .py files
            for py_file in app_dir_path.glob('*.py'):
                if py_file.name != '__init__.py':
                    remote_name = f"{app_name}/{py_file.name}"
                    files.append((str(py_file), remote_name))
    
    # Templates if exist
    templates_dir = src_dir / 'templates'
    if templates_dir.exists():
        files.append((None, "mkdir:templates"))
        for html_file in templates_dir.glob('*.html'):
            files.append((str(html_file), f"templates/{html_file.name}"))
    
    return files


def upload_files(port, project_root, app_name=None):
    """Sube archivos desde src/ a la placa ESP8266 usando ampy CLI"""
    src_dir = project_root / 'src'

    if not src_dir.exists():
        print(f"{RED}⛔ No se encontró el directorio src/{NC}")
        return False

    # Si no se especificó app, usar blink por defecto
    if not app_name:
        app_name = 'blink'
        print(f"{BLUE}📦 Usando app por defecto: blink{NC}\n")
    else:
        print(f"{BLUE}📦 Desplegando app: {app_name}{NC}\n")

    print(f"{BLUE}📤 Subiendo archivos desde src/ a la placa ESP8266...{NC}\n")
    
    # Obtener lista de archivos a subir
    files_to_upload = get_files_to_upload_usb(project_root, app_name=app_name)
    
    if not files_to_upload:
        print(f"{RED}❌ No se encontraron archivos para subir{NC}")
        return False
    
    success_count = 0
    error_count = 0
    
    try:
        # Procesar archivos y directorios
        for item in files_to_upload:
            local_path, remote_name = item
            
            # Handle directory creation
            if local_path is None and remote_name.startswith('mkdir:'):
                dir_name = remote_name.replace('mkdir:', '')
                try:
                    subprocess.run(
                        ['ampy', '--port', port, 'mkdir', dir_name],
                        check=False,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                except Exception:
                    pass
                continue
            
            # Upload file
            if local_path and Path(local_path).exists():
                try:
                    print(f"📄 Subiendo: {Path(local_path).name} → {remote_name}")
                    result = subprocess.run(
                        ['ampy', '--port', port, 'put', local_path, remote_name],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        success_count += 1
                    else:
                        print(f"{RED}⚠️  Error al subir {remote_name}: {result.stderr}{NC}")
                        error_count += 1
                except Exception as e:
                    print(f"{RED}⚠️  Error al subir {remote_name}: {e}{NC}")
                    error_count += 1
        
        print(f"\n{GREEN}✨ ¡Carga exitosa! ✅{NC}")
        print(f"   Exitosos: {success_count}")
        if error_count > 0:
            print(f"   {RED}Errores: {error_count}{NC}")

        # Copiar y actualizar .env con la app correcta
        print(f"\n{BLUE}📄 Actualizando .env en ESP8266...{NC}")
        try:
            temp_env = update_env_for_app(project_root, app_name)
            result = subprocess.run(
                ['ampy', '--port', port, 'put', str(temp_env), '.env'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print(f"{GREEN}   ✅ .env actualizado con APP={app_name}{NC}")
            else:
                print(f"{RED}   ⚠️  Error al subir .env: {result.stderr}{NC}")
                error_count += 1
        except Exception as e:
            print(f"{RED}   ⚠️  Error al subir .env: {e}{NC}")
            error_count += 1
        finally:
            cleanup_temp_env(project_root)

        return error_count == 0
        
    except Exception as e:
        print(f"{RED}❌ Error al conectar con la placa: {e}{NC}")
        print(f"   Verifica que:")
        print(f"   1. La placa esté conectada por USB")
        print(f"   2. El puerto {port} sea correcto")
        print(f"   3. La placa tenga MicroPython instalado")
        return False


def open_serial_monitor(port):
    """Abre el monitor serie"""
    print(f"\n{GREEN}🔄 Recuerda resetear la plaquita !!{NC}")
    print(f"\n{BLUE}📊 Iniciando monitor serie (115200 baudios){NC}")
    print(f"Para salir: presiona Ctrl-] o Ctrl+C\n")
    
    try:
        subprocess.run([
            sys.executable, '-m', 'serial.tools.miniterm',
            port, '115200'
        ])
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Monitor serie cerrado{NC}")
    except Exception as e:
        print(f"{RED}Error al abrir monitor serie: {e}{NC}")


def main():
    print_banner()
    
    # Parse app argument (filter out pytest arguments)
    app_name = None
    # Filter out pytest arguments (--rootdir, --verbose, etc.)
    args = [arg for arg in sys.argv[1:] if not arg.startswith('--')]
    if args:
        app_name = args[0]
        print(f"{BLUE}📦 App especificada: {app_name}{NC}\n")
    
    # Verificar ampy
    if not check_ampy_installed():
        if not install_ampy():
            sys.exit(1)
    
    # Encontrar raíz del proyecto
    project_root = find_project_root()
    if not project_root:
        print(f"{RED}⛔ No se encontró el directorio src/{NC}")
        print(f"   Asegúrate de ejecutar el script desde la raíz del proyecto")
        sys.exit(1)
    
    # Detectar puertos serie
    ports = find_serial_ports()
    
    if not ports:
        print(f"{RED}🚫 No se encontraron puertos serie.{NC}")
        print(f"   Asegúrate de que la placa esté conectada 🔌")
        os_type = detect_os()
        if os_type == 'macos':
            print(f"   En Mac, busca puertos en: /dev/tty.usbserial-* o /dev/tty.wchusbserial*")
        elif os_type == 'linux':
            print(f"   En Linux, busca puertos en: /dev/ttyUSB* o /dev/ttyACM*")
        elif os_type == 'windows':
            print(f"   En Windows, verifica el Administrador de dispositivos para el puerto COM")
        sys.exit(1)
    
    # Seleccionar puerto
    if len(ports) == 1:
        selected_port = ports[0]
        print(f"{GREEN}🔍 Puerto detectado automáticamente: {selected_port} ✅{NC}\n")
    else:
        print(f"{BLUE}Puertos serie detectados:{NC}")
        for i, port in enumerate(ports, 1):
            print(f"  {i}. {port}")
        
        while True:
            try:
                choice = input(f"\nElige el puerto a usar (1-{len(ports)}): ").strip()
                idx = int(choice) - 1
                if 0 <= idx < len(ports):
                    selected_port = ports[idx]
                    break
                else:
                    print(f"{RED}Selección inválida.{NC}")
            except ValueError:
                print(f"{RED}Por favor ingresa un número.{NC}")
            except KeyboardInterrupt:
                print(f"\n{YELLOW}Operación cancelada{NC}")
                sys.exit(0)
    
    # Cambiar al directorio del proyecto
    os.chdir(project_root)
    
    # Subir archivos
    if upload_files(selected_port, project_root, app_name=app_name):
        # Preguntar si abrir monitor serie
        print()
        try:
            response = input(f"{YELLOW}¿Abrir monitor serie? (s/N): {NC}").strip().lower()
            if response in ['s', 'S', 'y', 'Y']:
                open_serial_monitor(selected_port)
        except (EOFError, KeyboardInterrupt):
            print(f"\n{GREEN}✅ Deploy completado{NC}")
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()

