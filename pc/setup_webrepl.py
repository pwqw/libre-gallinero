#!/usr/bin/env python3
"""
Setup WebREPL simplificado para ESP8266
Copia boot.py completo, webrepl_cfg.py y .env al ESP8266.
Luego abre monitor serial para observar el proceso de bootstrapping.
"""

import sys
import os
import subprocess
import glob
import tempfile
import time
from pathlib import Path

# Colores
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
RED = '\033[0;31m'
NC = '\033[0m'

def load_env():
    """Carga variables desde archivo .env del repositorio"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    env_path = os.path.join(project_dir, '.env')

    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip().strip('"').strip("'")
    return env_vars

def find_port():
    """Detecta puerto serie automáticamente"""
    ports = []
    for pattern in ['/dev/tty.usbserial-*', '/dev/tty.wchusbserial*', '/dev/ttyUSB*', '/dev/ttyACM*', '/dev/cu.*']:
        ports.extend(glob.glob(pattern))
    if sys.platform == 'win32':
        try:
            import serial.tools.list_ports
            ports = [p.device for p in serial.tools.list_ports.comports()]
        except:
            pass
    return sorted(set(ports))[0] if ports else None

def run_ampy(cmd):
    """Ejecuta comando ampy"""
    result = subprocess.run(['ampy'] + cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"{RED}Error: {result.stderr}{NC}")
        return False
    return True

def open_serial_monitor(port, baudrate=115200):
    """
    Abre conexión serial y muestra output en tiempo real.
    BLOCKING hasta Ctrl+C.
    """
    try:
        import serial
    except ImportError:
        print(f"{YELLOW}Instalando pyserial...{NC}")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyserial'])
        import serial

    try:
        print(f"{BLUE}Intentando conectar a {port} @ {baudrate}...{NC}")
        ser = serial.Serial(port, baudrate, timeout=1)
        print(f"{GREEN}🔌 Conectado a {port} @ {baudrate}{NC}\n")
        print(f"{BLUE}{'='*50}{NC}")
        print(f"{BLUE}📡 Monitor Serial Activo{NC}")
        print(f"{BLUE}{'='*50}{NC}\n")
        print(f"{YELLOW}Esperando datos del ESP8266...{NC}")
        print(f"{YELLOW}Si no ves nada, puede ser:{NC}")
        print(f"  1. Problema de memoria en boot.py (no puede imprimir)")
        print(f"  2. ESP8266 no está reiniciado")
        print(f"  3. Baudrate incorrecto (debe ser 115200)")
        print(f"  4. boot.py tiene errores y no se ejecuta")
        print(f"\n{YELLOW}Nota: Si boot.py tiene problemas de memoria,")
        print(f"      puede funcionar pero no imprimir nada al serial.{NC}")
        print(f"{BLUE}{'='*50}{NC}\n")

        last_data_time = time.time()
        warning_shown = False
        initial_wait = True
        initial_wait_time = 3  # Esperar 3 segundos antes de mostrar primer warning

        while True:
            if ser.in_waiting:
                line = ser.readline()
                last_data_time = time.time()
                warning_shown = False  # Reset warning cuando hay datos
                initial_wait = False  # Ya recibimos datos
                try:
                    print(line.decode('utf-8'), end='')
                except:
                    print(line.decode('latin-1', errors='ignore'), end='')
            else:
                # FIX: Agregar sleep para evitar CPU al 100%
                time.sleep(0.01)
                
                elapsed = time.time() - last_data_time
                
                # Mostrar advertencia inicial después de espera inicial
                if initial_wait and elapsed > initial_wait_time:
                    print(f"\n{YELLOW}⚠️  Esperando datos iniciales...{NC}")
                    print(f"{YELLOW}   Si no aparece nada, el ESP8266 puede tener problemas de memoria.{NC}")
                    print(f"{YELLOW}   Intenta reiniciar el dispositivo (desconecta y reconecta USB).{NC}\n")
                    initial_wait = False
                    warning_shown = True
                
                # Mostrar advertencia periódica si no hay datos
                elif not warning_shown and elapsed > 5:
                    print(f"\n{YELLOW}⚠️  Sin datos desde hace {int(elapsed)}s{NC}")
                    print(f"{YELLOW}   Posibles causas:{NC}")
                    print(f"   - boot.py agotó memoria y no puede imprimir")
                    print(f"   - ESP8266 necesita reinicio (desconecta/reconecta USB)")
                    print(f"   - boot.py tiene errores")
                    print(f"\n{YELLOW}   Si el dispositivo funciona pero no imprime,")
                    print(f"   prueba conectar vía WebREPL en lugar del serial.{NC}\n")
                    warning_shown = True

    except serial.SerialException as e:
        print(f"\n{RED}Error de conexión serial: {e}{NC}")
        print(f"{YELLOW}Verifica que el puerto {port} esté disponible{NC}")
        print(f"{YELLOW}  - Desconecta y reconecta el ESP8266{NC}")
        print(f"{YELLOW}  - Verifica que no esté en uso por otro programa{NC}")
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}❌ Monitor serial cerrado{NC}")
    except Exception as e:
        print(f"\n{RED}Error en monitor serial: {e}{NC}")
        import traceback
        print(f"{YELLOW}Traceback:{NC}")
        traceback.print_exc()
    finally:
        if 'ser' in locals() and ser:
            ser.close()
            print(f"{GREEN}Puerto serial cerrado{NC}")

def main():
    print(f"{BLUE}🔧 Setup WebREPL simplificado para ESP8266{NC}\n")

    # Verificar/instalar ampy
    try:
        import ampy.cli
    except ImportError:
        print(f"{YELLOW}Instalando adafruit-ampy...{NC}")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'adafruit-ampy', 'pyserial'])

    # Directorios del proyecto
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)

    # Cargar configuración
    env = load_env()

    # Obtener puerto
    port = env.get('SERIAL_PORT') or find_port()
    if not port:
        port = input(f"{YELLOW}Puerto serie: {NC}").strip()
    if not port:
        print(f"{RED}❌ Puerto requerido{NC}")
        sys.exit(1)

    print(f"{BLUE}[1/4] Puerto: {port}{NC}")

    # Obtener password WebREPL
    webrepl_pass = env.get('WEBREPL_PASSWORD') or input(f"{YELLOW}Password WebREPL (default: admin): {NC}").strip() or "admin"

    # 1. Configurar webrepl_cfg.py
    print(f"\n{BLUE}[2/4] Configurando WebREPL...{NC}")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(f"PASS = '{webrepl_pass}'\n")
        webrepl_cfg = f.name

    if not run_ampy(['--port', port, 'put', webrepl_cfg, 'webrepl_cfg.py']):
        os.unlink(webrepl_cfg)
        sys.exit(1)
    os.unlink(webrepl_cfg)
    print(f"{GREEN}✅ webrepl_cfg.py configurado{NC}")

    # 2. Copiar boot.py COMPLETO desde src/
    print(f"\n{BLUE}[3/4] Copiando boot.py completo...{NC}")
    boot_path = os.path.join(project_dir, 'src', 'boot.py')

    if not os.path.exists(boot_path):
        print(f"{RED}❌ No se encontró {boot_path}{NC}")
        sys.exit(1)

    if not run_ampy(['--port', port, 'put', boot_path, 'boot.py']):
        sys.exit(1)
    print(f"{GREEN}✅ boot.py instalado{NC}")

    # 3. Copiar .env si existe
    env_path = os.path.join(project_dir, '.env')

    if os.path.exists(env_path):
        print(f"\n{BLUE}[4/4] Copiando .env al ESP8266...{NC}")
        if run_ampy(['--port', port, 'put', env_path, '.env']):
            print(f"{GREEN}✅ .env copiado{NC}")
        else:
            print(f"{YELLOW}⚠️  No se pudo copiar .env{NC}")
    else:
        print(f"\n{BLUE}[4/4] .env no encontrado en repositorio{NC}")
        print(f"{YELLOW}⚠️  boot.py usará .env.example o valores por defecto{NC}")

    # 4. Abrir monitor serial
    print(f"\n{GREEN}{'='*50}{NC}")
    print(f"{GREEN}✅ Setup completado!{NC}")
    print(f"{GREEN}{'='*50}{NC}\n")

    print(f"{YELLOW}Próximos pasos:{NC}")
    print(f"  1. Reinicia el ESP8266 (desconecta y reconecta)")
    print(f"  2. Observa el proceso de bootstrapping abajo")
    print(f"  3. Si WiFi conecta → anota la IP")
    print(f"  4. Si WiFi falla → conecta al hotspot y configura")
    print(f"  5. Presiona Ctrl+C para salir del monitor\n")

    input(f"{BLUE}Presiona Enter cuando hayas reiniciado el ESP8266...{NC}")

    print(f"\n{BLUE}📡 Abriendo monitor serial...{NC}\n")

    # Abrir monitor serial (BLOCKING)
    open_serial_monitor(port, baudrate=115200)

if __name__ == '__main__':
    main()
