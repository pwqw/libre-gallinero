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
import subprocess
from pathlib import Path

# Agregar tools/common al path
script_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(script_dir))

# Agregar pc/ al path para importar serial_monitor
project_dir = script_dir.parent
sys.path.insert(0, str(project_dir / 'pc'))

from common.env_updater import update_env_for_app, cleanup_temp_env
from common.port_detection import find_serial_ports, detect_os
from common.ampy_utils import (
    run_ampy,
    ensure_directory_exists,
    get_files_to_upload,
    check_ampy_installed,
    install_ampy,
    check_port_permissions,
    RED, GREEN, YELLOW, BLUE, NC
)
from serial_monitor import SerialMonitor


def print_banner():
    """Imprime el banner del script"""
    print("╔════════════════════════════════════════╗")
    print("║       🐔  LIBRE GALLINERO  🐔          ║")
    print("║         GRABADOR DE PLACA              ║")
    print("║      (Windows/Mac/Linux - USB Serial)  ║")
    print("╚════════════════════════════════════════╝")
    print()


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
    files_to_upload = get_files_to_upload(project_root, app_name=app_name, include_base=True)
    
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
                if ensure_directory_exists(port, dir_name, verbose=False):
                    print(f"   📁 {dir_name}/")
                else:
                    error_count += 1
                continue
            
            # Upload file
            if local_path and Path(local_path).exists():
                print(f"📄 Subiendo: {Path(local_path).name} → {remote_name}")
                if run_ampy(['--port', port, 'put', local_path, remote_name]):
                    success_count += 1
                else:
                    error_count += 1
                    print(f"{RED}   ⚠️  Error al subir {remote_name}{NC}")
        
        print(f"\n{GREEN}✨ ¡Carga exitosa! ✅{NC}")
        print(f"   Exitosos: {success_count}")
        if error_count > 0:
            print(f"   {RED}Errores: {error_count}{NC}")

        # Copiar y actualizar .env con la app correcta
        print(f"\n{BLUE}📄 Actualizando .env en ESP8266...{NC}")
        try:
            temp_env = update_env_for_app(project_root, app_name)
            if run_ampy(['--port', port, 'put', str(temp_env), '.env']):
                print(f"{GREEN}   ✅ .env actualizado con APP={app_name}{NC}")
            else:
                print(f"{RED}   ⚠️  Error al subir .env{NC}")
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
    """Abre el monitor serie usando SerialMonitor"""
    print(f"\n{GREEN}🔄 Recuerda resetear la plaquita !!{NC}")
    print(f"\n{BLUE}📊 Iniciando monitor serie (115200 baudios){NC}")
    print(f"Para salir: presiona Ctrl+C\n")
    
    try:
        monitor = SerialMonitor(port=port, baudrate=115200, max_reconnect_attempts=5)
        monitor.start()
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
    
    # Verificar permisos del puerto
    if not check_port_permissions(selected_port):
        sys.exit(1)
    
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

