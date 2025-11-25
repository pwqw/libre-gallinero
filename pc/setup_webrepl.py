#!/usr/bin/env python3
"""
Setup WebREPL simplificado para ESP8266
Copia boot.py completo, webrepl_cfg.py y .env al ESP8266.
Luego abre monitor serial para observar el proceso de bootstrapping.
"""

import sys
import os
import subprocess
import tempfile
from pathlib import Path
from serial_monitor import SerialMonitor, find_port, GREEN, YELLOW, BLUE, RED, NC

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


def run_ampy(cmd):
    """Ejecuta comando ampy"""
    result = subprocess.run(['ampy'] + cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"{RED}Error: {result.stderr}{NC}")
        return False
    return True

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

    # Abrir monitor serial (BLOCKING) usando el módulo reutilizable
    monitor = SerialMonitor(port=port, baudrate=115200, max_reconnect_attempts=5)
    monitor.start()

if __name__ == '__main__':
    main()
