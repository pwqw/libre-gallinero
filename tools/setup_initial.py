#!/usr/bin/env python3
"""
Setup inicial WebREPL para ESP8266 (solo primera vez, requiere USB).
Copia boot.py completo, webrepl_cfg.py y .env al ESP8266.
Luego abre monitor serial para observar el proceso de bootstrapping.

Uso:
    python3 tools/setup_initial.py
"""

import sys
import os
import subprocess
import tempfile
from pathlib import Path

# Agregar pc/ al path para importar serial_monitor
script_dir = Path(__file__).parent.absolute()
project_dir = script_dir.parent
sys.path.insert(0, str(project_dir / 'pc'))

from serial_monitor import SerialMonitor, find_port, GREEN, YELLOW, BLUE, RED, NC


def load_env(project_dir):
    """Carga variables desde archivo .env del repositorio"""
    env_path = project_dir / '.env'
    env_vars = {}
    
    if env_path.exists():
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


def verify_webrepl_config(port, password):
    """Verifica que webrepl_cfg.py se copió correctamente"""
    print(f"\n{BLUE}🔍 Verificando configuración...{NC}")
    
    result = subprocess.run(
        ['ampy', '--port', port, 'get', 'webrepl_cfg.py'],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        if f"PASS = '{password}'" in result.stdout:
            print(f"{GREEN}✅ webrepl_cfg.py verificado correctamente{NC}")
            return True
        else:
            print(f"{YELLOW}⚠️  webrepl_cfg.py existe pero password no coincide{NC}")
            return False
    else:
        print(f"{YELLOW}⚠️  No se pudo verificar webrepl_cfg.py (puede ser normal){NC}")
        return False


def main():
    print(f"{BLUE}🔧 Setup inicial WebREPL para ESP8266{NC}\n")
    
    # Verificar/instalar ampy
    try:
        import ampy.cli
    except ImportError:
        print(f"{YELLOW}Instalando adafruit-ampy...{NC}")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'adafruit-ampy', 'pyserial'])
    
    # Directorios del proyecto
    project_dir = Path(__file__).parent.parent
    
    # Cargar configuración
    env = load_env(project_dir)
    
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
    
    # Validar password
    if len(webrepl_pass) < 4:
        print(f"{YELLOW}⚠️  Advertencia: Password muy corto (mínimo 4 caracteres recomendado){NC}")
        confirm = input(f"{YELLOW}¿Continuar de todas formas? (s/N): {NC}").strip().lower()
        if confirm != 's':
            print(f"{RED}❌ Setup cancelado{NC}")
            sys.exit(1)
    
    # Asegurar que .env tenga el password si existe
    env_path = project_dir / '.env'
    if env_path.exists():
        env_lines = []
        password_found = False
        with open(env_path, 'r') as f:
            for line in f:
                if line.strip().startswith('WEBREPL_PASSWORD='):
                    env_lines.append(f'WEBREPL_PASSWORD={webrepl_pass}\n')
                    password_found = True
                else:
                    env_lines.append(line)
        
        if not password_found:
            env_lines.append(f'\n# WebREPL Configuration\nWEBREPL_PASSWORD={webrepl_pass}\n')
        
        with open(env_path, 'w') as f:
            f.writelines(env_lines)
        print(f"{GREEN}✅ .env actualizado con WEBREPL_PASSWORD{NC}")
    
    # 1. Configurar webrepl_cfg.py
    print(f"\n{BLUE}[2/4] Configurando WebREPL...{NC}")
    print(f"   Password: {'*' * len(webrepl_pass)}")
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(f"PASS = '{webrepl_pass}'\n")
        webrepl_cfg = f.name
    
    if not run_ampy(['--port', port, 'put', webrepl_cfg, 'webrepl_cfg.py']):
        os.unlink(webrepl_cfg)
        sys.exit(1)
    os.unlink(webrepl_cfg)
    print(f"{GREEN}✅ webrepl_cfg.py configurado{NC}")
    
    verify_webrepl_config(port, webrepl_pass)
    
    # 2. Copiar boot.py desde src/
    print(f"\n{BLUE}[3/4] Copiando boot.py...{NC}")
    boot_path = project_dir / 'src' / 'boot.py'
    
    if not boot_path.exists():
        print(f"{RED}❌ No se encontró {boot_path}{NC}")
        sys.exit(1)
    
    if not run_ampy(['--port', port, 'put', str(boot_path), 'boot.py']):
        sys.exit(1)
    print(f"{GREEN}✅ boot.py instalado{NC}")
    
    # 3. Copiar .env
    print(f"\n{BLUE}[4/4] Copiando .env al ESP8266...{NC}")
    if env_path.exists():
        if run_ampy(['--port', port, 'put', str(env_path), '.env']):
            print(f"{GREEN}✅ .env copiado{NC}")
        else:
            print(f"{YELLOW}⚠️  No se pudo copiar .env{NC}")
            print(f"{YELLOW}   boot.py usará webrepl_cfg.py como fallback{NC}")
    else:
        print(f"{YELLOW}⚠️  .env no encontrado{NC}")
        print(f"{YELLOW}   boot.py usará webrepl_cfg.py o valores por defecto{NC}")
    
    # Resumen
    print(f"\n{GREEN}{'='*50}{NC}")
    print(f"{GREEN}✅ Setup completado!{NC}")
    print(f"{GREEN}{'='*50}{NC}\n")
    
    print(f"{BLUE}📋 Resumen:{NC}")
    print(f"   • webrepl_cfg.py: Password configurado")
    print(f"   • boot.py: Instalado")
    print(f"   • .env: {'Copiado' if env_path.exists() else 'No disponible'}")
    print(f"   • Password WebREPL: {'*' * len(webrepl_pass)}")
    print(f"\n{YELLOW}Próximos pasos:{NC}")
    print(f"  1. Reinicia el ESP8266 (desconecta y reconecta USB)")
    print(f"  2. Observa el proceso de bootstrapping abajo")
    print(f"  3. Si WiFi conecta → anota la IP (aparecerá en el monitor)")
    print(f"  4. Si WiFi falla → conecta al hotspot 'libre gallinero'")
    print(f"  5. WebREPL estará disponible en:")
    print(f"     • WiFi OK: ws://<IP>:8266")
    print(f"     • Hotspot: ws://192.168.4.1:8266")
    print(f"  6. Presiona Ctrl+C para salir del monitor\n")
    
    print(f"{BLUE}💡 Tip: Después del reinicio, puedes usar:{NC}")
    print(f"   python3 tools/deploy_wifi.py  # Deploy sin cables\n")
    
    try:
        input(f"{BLUE}Presiona Enter cuando hayas reiniciado el ESP8266...{NC}")
    except (EOFError, KeyboardInterrupt):
        print(f"\n{YELLOW}Setup completado. Reinicia el ESP8266 manualmente.{NC}")
        return
    
    print(f"\n{BLUE}📡 Abriendo monitor serial...{NC}\n")
    
    # Abrir monitor serial (BLOCKING)
    monitor = SerialMonitor(port=port, baudrate=115200, max_reconnect_attempts=5)
    monitor.start()


if __name__ == '__main__':
    main()

