#!/usr/bin/env python3
"""
Setup WebREPL simplificado para ESP8266
Copia boot.py, webrepl_cfg.py y .env al ESP8266.
Luego abre monitor serial para observar el proceso de bootstrapping.
"""

import sys
import os
import subprocess
import tempfile
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

    # Obtener password WebREPL
    webrepl_pass = env.get('WEBREPL_PASSWORD') or input(f"{YELLOW}Password WebREPL (default: admin): {NC}").strip() or "admin"
    
    # Actualizar .env con todas las configuraciones
    env_path = os.path.join(project_dir, '.env')
    env_lines = []
    wifi_ssid_found = False
    wifi_password_found = False
    password_found = False
    
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if line.strip().startswith('WIFI_SSID='):
                    env_lines.append(f'WIFI_SSID={wifi_ssid}\n')
                    wifi_ssid_found = True
                elif line.strip().startswith('WIFI_PASSWORD='):
                    env_lines.append(f'WIFI_PASSWORD={wifi_password}\n')
                    wifi_password_found = True
                elif line.strip().startswith('WEBREPL_PASSWORD='):
                    env_lines.append(f'WEBREPL_PASSWORD={webrepl_pass}\n')
                    password_found = True
                else:
                    env_lines.append(line)
    
    # Agregar configuraciones faltantes
    if not wifi_ssid_found:
        env_lines.append(f'\n# WiFi Configuration (REQUERIDO)\nWIFI_SSID={wifi_ssid}\n')
    if not wifi_password_found:
        env_lines.append(f'WIFI_PASSWORD={wifi_password}\n')
    if not password_found:
        env_lines.append(f'\n# WebREPL Configuration\nWEBREPL_PASSWORD={webrepl_pass}\n')
    
    with open(env_path, 'w') as f:
        f.writelines(env_lines)
    
    print(f"{GREEN}✅ Credenciales guardadas en .env{NC}")

    # 1. Configurar webrepl_cfg.py
    print(f"\n{BLUE}[2/4] Configurando WebREPL...{NC}")
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
    print(f"\n{BLUE}[3/4] Copiando boot.py...{NC}")
    boot_path = os.path.join(project_dir, 'src', 'boot.py')

    if not os.path.exists(boot_path):
        print(f"{RED}❌ No se encontró {boot_path}{NC}")
        sys.exit(1)

    if not run_ampy(['--port', port, 'put', boot_path, 'boot.py']):
        sys.exit(1)
    print(f"{GREEN}✅ boot.py instalado{NC}")

    # 3. Copiar .env (REQUERIDO - contiene credenciales WiFi)
    print(f"\n{BLUE}[4/4] Copiando .env (WiFi + WebREPL)...{NC}")
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
    print(f"   • .env: Copiado (WiFi: {wifi_ssid})")
    print(f"\n{YELLOW}Próximos pasos:{NC}")
    print(f"  1. Reinicia el ESP8266")
    print(f"  2. El ESP intentará conectar a WiFi: {wifi_ssid}")
    print(f"  3. Si falla, creará hotspot con mismo SSID/password")
    print(f"  4. WebREPL estará disponible en ws://<IP>:8266")
    print(f"  5. Usa: python3 pc/webrepl_deploy.py para subir archivos\n")

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
