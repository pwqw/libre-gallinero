#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para subir archivos a ESP8266 vía USB Serial (ampy)
Compatible con Windows, Mac y Linux

Uso:
    python3 pc/deploy.py
    # O desde el directorio pc/:
    python3 deploy.py

Requiere:
    pip install adafruit-ampy pyserial
"""

import sys
import os
import platform
import subprocess
import glob
from pathlib import Path

# Colores para terminal
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color

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
        # Mac: /dev/tty.usbserial-*, /dev/tty.wchusbserial*, /dev/cu.*
        patterns = [
            '/dev/tty.usbserial-*',
            '/dev/tty.wchusbserial*',
            '/dev/cu.usbserial-*',
            '/dev/cu.wchusbserial*',
        ]
    elif os_type == 'linux':
        # Linux: /dev/ttyUSB*, /dev/ttyACM*
        patterns = [
            '/dev/ttyUSB*',
            '/dev/ttyACM*',
        ]
    elif os_type == 'windows':
        # Windows: COM1-COM256
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

def activate_virtualenv():
    """Intenta activar el entorno virtual (solo informativo en Python)"""
    # En Python, el entorno virtual debería estar activado manualmente
    # o el script debería ejecutarse con el Python del venv
    venv_paths = ['env', '../env']
    for venv_path in venv_paths:
        if os.path.exists(venv_path):
            python_exe = os.path.join(venv_path, 'bin', 'python')
            if os.path.exists(python_exe):
                return python_exe
            # Windows
            python_exe = os.path.join(venv_path, 'Scripts', 'python.exe')
            if os.path.exists(python_exe):
                return python_exe
    return None

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
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'adafruit-ampy'])
        print(f"{GREEN}✅ ampy instalado correctamente{NC}\n")
        return True
    except subprocess.CalledProcessError:
        print(f"{RED}❌ Error al instalar ampy{NC}")
        return False

def find_project_root():
    """Encuentra la raíz del proyecto (donde está src/)"""
    current = Path.cwd()
    
    # Buscar src/ en el directorio actual o padre
    for path in [current, current.parent]:
        if (path / 'src').exists():
            return path
    
    return None

def upload_files(port, project_root):
    """Sube archivos desde src/ a la placa ESP8266 usando ampy CLI"""
    src_dir = project_root / 'src'
    
    if not src_dir.exists():
        print(f"{RED}⛔ No se encontró el directorio src/{NC}")
        return False
    
    print(f"{BLUE}📤 Subiendo archivos desde src/ a la placa ESP8266...{NC}\n")
    
    success_count = 0
    error_count = 0
    
    try:
        # Subir directorios primero (excluyendo __pycache__)
        for dir_path in src_dir.rglob('*'):
            if dir_path.is_dir() and '__pycache__' not in str(dir_path):
                remote_dir = str(dir_path.relative_to(src_dir))
                if remote_dir:
                    try:
                        # Intentar crear directorio (puede fallar si ya existe, eso está bien)
                        subprocess.run(
                            ['ampy', '--port', port, 'mkdir', remote_dir],
                            check=False,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
                    except Exception:
                        pass
        
        # Subir archivos
        for file_path in src_dir.rglob('*'):
            if file_path.is_file() and '__pycache__' not in str(file_path) and not file_path.name.endswith('.pyc'):
                remote_file = str(file_path.relative_to(src_dir))
                try:
                    print(f"📄 Subiendo: {file_path.name} → {remote_file}")
                    result = subprocess.run(
                        ['ampy', '--port', port, 'put', str(file_path), remote_file],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        success_count += 1
                    else:
                        print(f"{RED}⚠️  Error al subir {file_path.name}: {result.stderr}{NC}")
                        error_count += 1
                except Exception as e:
                    print(f"{RED}⚠️  Error al subir {file_path.name}: {e}{NC}")
                    error_count += 1
        
        print(f"\n{GREEN}✨ ¡Carga exitosa! ✅{NC}")
        print(f"   Exitosos: {success_count}")
        if error_count > 0:
            print(f"   {RED}Errores: {error_count}{NC}")
        
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
    if upload_files(selected_port, project_root):
        # Preguntar si abrir monitor serie
        print()
        response = input(f"{YELLOW}¿Abrir monitor serie? (s/N): {NC}").strip().lower()
        if response in ['s', 'S', 'y', 'Y']:
            open_serial_monitor(selected_port)
    else:
        sys.exit(1)

if __name__ == '__main__':
    main()

