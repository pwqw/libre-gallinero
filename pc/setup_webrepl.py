#!/usr/bin/env python3
"""
Setup WebREPL simplificado para ESP8266
Copia boot.py, main.py, webrepl_cfg.py y .env al ESP8266.
Luego abre monitor serial para observar el proceso de bootstrapping.
"""

import sys
import os
import subprocess
import tempfile
from pathlib import Path

# Ajustar path para imports locales
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from serial_monitor import SerialMonitor, find_port
from colors import GREEN, YELLOW, BLUE, RED, NC
from validate_config import validate

# Agregar tools/common al path para importar funciones comunes
project_dir = os.path.dirname(script_dir)
tools_common_path = os.path.join(project_dir, 'tools', 'common')
if tools_common_path not in sys.path:
    sys.path.insert(0, tools_common_path)

# Importar módulo común (path agregado dinámicamente arriba)
from webrepl_client import MAX_FILE_SIZE, validate_file_size  # type: ignore

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

def escape_env_value(value):
    """
    Escapa un valor para escribir en .env
    Agrega comillas si el valor contiene espacios o caracteres especiales
    """
    if not value:
        return '""'
    
    # Si el valor ya está entre comillas, removerlas primero
    value = value.strip().strip('"').strip("'")
    
    # Valores que necesitan comillas:
    # - Contienen espacios
    # - Contienen caracteres especiales que pueden causar problemas
    # - Empiezan o terminan con espacios (aunque ya los removimos)
    needs_quotes = (
        ' ' in value or
        '\t' in value or
        '\n' in value or
        value.startswith('#') or
        any(char in value for char in ['~', '(', ')', '[', ']', '{', '}', '$', '`', '\\'])
    )
    
    if needs_quotes:
        # Escapar comillas dobles dentro del valor
        value_escaped = value.replace('"', '\\"')
        return f'"{value_escaped}"'
    else:
        return value

def run_ampy(cmd):
    """Ejecuta comando ampy"""
    result = subprocess.run(['ampy'] + cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"{RED}Error: {result.stderr}{NC}")
        return False
    return True

def main():
    print(f"{BLUE}🔧 Setup WebREPL para ESP8266{NC}\n")

    # Verificar/instalar ampy
    try:
        import ampy.cli
    except ImportError:
        print(f"{YELLOW}Instalando adafruit-ampy...{NC}")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'adafruit-ampy', 'pyserial'])

    # Directorios del proyecto
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)

    # Validar configuración antes de continuar
    print(f"{BLUE}Validando configuración...{NC}\n")
    is_valid, errors = validate(verbose=True)
    if not is_valid:
        print(f"\n{RED}❌ Configuración inválida. Corrige los errores antes de continuar.{NC}")
        sys.exit(1)
    print()

    # Cargar configuración
    env = load_env()

    # Obtener puerto
    port = env.get('SERIAL_PORT') or find_port()
    if not port:
        port = input(f"{YELLOW}Puerto serie: {NC}").strip()
    if not port:
        print(f"{RED}❌ Puerto requerido{NC}")
        sys.exit(1)

    print(f"{BLUE}[1/6] Puerto: {port}{NC}")

    # Obtener credenciales WiFi (REQUERIDAS - mínimo indispensable)
    print(f"\n{YELLOW}⚠️  WiFi es REQUERIDO para el setup mínimo{NC}")
    wifi_ssid = env.get('WIFI_SSID') or input(f"{YELLOW}WiFi SSID: {NC}").strip()
    if not wifi_ssid:
        print(f"{RED}❌ WiFi SSID es requerido{NC}")
        sys.exit(1)
    
    wifi_password = env.get('WIFI_PASSWORD') or input(f"{YELLOW}WiFi Password: {NC}").strip()
    if not wifi_password:
        print(f"{RED}❌ WiFi Password es requerido{NC}")
        sys.exit(1)
    
    # Obtener si la red es oculta
    wifi_hidden = env.get('WIFI_HIDDEN', '').lower()
    if not wifi_hidden:
        hidden_input = input(f"{YELLOW}¿Red WiFi oculta? (s/n, default: n): {NC}").strip().lower()
        wifi_hidden = 'true' if hidden_input in ['s', 'si', 'sí', 'y', 'yes'] else 'false'
    else:
        wifi_hidden = 'true' if wifi_hidden == 'true' else 'false'

    # Obtener password WebREPL
    webrepl_pass = env.get('WEBREPL_PASSWORD') or input(f"{YELLOW}Password WebREPL (default: admin): {NC}").strip() or "admin"
    
    # Actualizar .env con todas las configuraciones
    env_path = os.path.join(project_dir, '.env')
    env_lines = []
    wifi_ssid_found = False
    wifi_password_found = False
    wifi_hidden_found = False
    password_found = False
    
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if line.strip().startswith('WIFI_SSID='):
                    env_lines.append(f'WIFI_SSID={escape_env_value(wifi_ssid)}\n')
                    wifi_ssid_found = True
                elif line.strip().startswith('WIFI_PASSWORD='):
                    env_lines.append(f'WIFI_PASSWORD={escape_env_value(wifi_password)}\n')
                    wifi_password_found = True
                elif line.strip().startswith('WIFI_HIDDEN='):
                    env_lines.append(f'WIFI_HIDDEN={escape_env_value(wifi_hidden)}\n')
                    wifi_hidden_found = True
                elif line.strip().startswith('WEBREPL_PASSWORD='):
                    env_lines.append(f'WEBREPL_PASSWORD={escape_env_value(webrepl_pass)}\n')
                    password_found = True
                else:
                    env_lines.append(line)
    
    # Agregar configuraciones faltantes
    if not wifi_ssid_found:
        env_lines.append(f'\n# WiFi Configuration (REQUERIDO)\nWIFI_SSID={escape_env_value(wifi_ssid)}\n')
    if not wifi_password_found:
        env_lines.append(f'WIFI_PASSWORD={escape_env_value(wifi_password)}\n')
    if not wifi_hidden_found:
        env_lines.append(f'WIFI_HIDDEN={escape_env_value(wifi_hidden)}\n')
    if not password_found:
        env_lines.append(f'\n# WebREPL Configuration\nWEBREPL_PASSWORD={escape_env_value(webrepl_pass)}\n')
    
    with open(env_path, 'w') as f:
        f.writelines(env_lines)
    
    print(f"{GREEN}✅ Credenciales guardadas en .env{NC}")

    # 1. Configurar webrepl_cfg.py
    print(f"\n{BLUE}[2/6] Configurando WebREPL...{NC}")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        # Usar repr() para escapar correctamente comillas y caracteres especiales
        f.write(f"PASS = {repr(webrepl_pass)}\n")
        webrepl_cfg = f.name

    if not run_ampy(['--port', port, 'put', webrepl_cfg, 'webrepl_cfg.py']):
        try:
            os.unlink(webrepl_cfg)
        except:
            pass
        sys.exit(1)
    try:
        os.unlink(webrepl_cfg)
    except:
        pass
    print(f"{GREEN}✅ webrepl_cfg.py configurado{NC}")

    # 2. Copiar boot.py
    print(f"\n{BLUE}[3/6] Copiando boot.py...{NC}")
    boot_path = os.path.join(project_dir, 'src', 'boot.py')

    if not os.path.exists(boot_path):
        print(f"{RED}❌ No se encontró {boot_path}{NC}")
        sys.exit(1)

    if not run_ampy(['--port', port, 'put', boot_path, 'boot.py']):
        sys.exit(1)
    print(f"{GREEN}✅ boot.py instalado{NC}")

    # 3. Copiar módulos principales (REQUERIDO - lógica modularizada)
    print(f"\n{BLUE}[4/6] Copiando módulos principales...{NC}")
    modules = ['main.py', 'config.py', 'wifi.py', 'ntp.py', 'app_loader.py']
    for module in modules:
        module_path = os.path.join(project_dir, 'src', module)
        if not os.path.exists(module_path):
            print(f"{RED}❌ No se encontró {module_path}{NC}")
            sys.exit(1)
        
        # Validar tamaño de archivo usando función común
        is_valid, file_size, error_msg = validate_file_size(module_path)
        if not is_valid:
            print(f"{RED}❌ {module}: {error_msg}{NC}")
            sys.exit(1)
        
        print(f"  Copiando {module} ({file_size} bytes)...")
        if not run_ampy(['--port', port, 'put', module_path, module]):
            sys.exit(1)
    print(f"{GREEN}✅ Módulos principales instalados{NC}")

    # 4. Copiar .env (REQUERIDO - contiene credenciales WiFi)
    print(f"\n{BLUE}[5/6] Copiando .env (WiFi + WebREPL)...{NC}")
    if not os.path.exists(env_path):
        print(f"{RED}❌ Error: .env no existe después de guardar credenciales{NC}")
        sys.exit(1)
    
    if not run_ampy(['--port', port, 'put', env_path, '.env']):
        print(f"{RED}❌ Error copiando .env al ESP8266{NC}")
        sys.exit(1)
    print(f"{GREEN}✅ .env copiado (WiFi configurado){NC}")

    # Resumen
    print(f"\n{GREEN}{'='*50}{NC}")
    print(f"{GREEN}✅ Setup completado!{NC}")
    print(f"{GREEN}{'='*50}{NC}\n")
    
    print(f"{BLUE}📋 Resumen:{NC}")
    print(f"   • webrepl_cfg.py: Configurado")
    print(f"   • boot.py: Instalado")
    print(f"   • Módulos base: main.py, config.py, wifi.py, ntp.py, app_loader.py")
    print(f"   • .env: Copiado (WiFi: {wifi_ssid})")
    print(f"\n{YELLOW}⚠️  NOTA: Este setup NO incluye proyectos (gallinero/heladera){NC}")
    print(f"   Los proyectos se instalan después vía deploy WiFi:\n")
    print(f"   python3 tools/deploy_wifi.py <proyecto>\n")
    print(f"\n{YELLOW}Próximos pasos:{NC}")
    print(f"  1. Reinicia el ESP8266")
    print(f"  2. El ESP intentará conectar a WiFi: {wifi_ssid}")
    print(f"  3. WebREPL estará disponible en ws://<IP>:8266")
    print(f"  4. Usa: python3 tools/deploy_wifi.py <proyecto> para subir proyecto\n")

    input(f"{BLUE}Presiona Enter cuando hayas reiniciado el ESP8266...{NC}")

    print(f"\n{BLUE}📡 Abriendo monitor serial (DEBUGGING)...{NC}")
    print(f"{YELLOW}   El monitor serial es tu herramienta principal para debugging.{NC}")
    print(f"{YELLOW}   Aquí verás todos los logs del ESP8266, incluyendo:{NC}")
    print(f"      • Estado de conexión WiFi")
    print(f"      • Intentos de conexión a red")
    print(f"      • Creación de hotspot (si WiFi falla)")
    print(f"      • Errores y mensajes del sistema\n")
    monitor = SerialMonitor(port=port, baudrate=115200, max_reconnect_attempts=5)
    monitor.start()

if __name__ == '__main__':
    main()
