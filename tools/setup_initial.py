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


def get_base_files_to_upload(project_dir):
    """
    Get list of base system files + blink app for initial setup.
    This ensures the ESP8266 works immediately after setup.

    Returns:
        list: List of tuples (local_path, remote_name) or (None, "mkdir:dirname")
    """
    src_dir = Path(project_dir) / 'src'
    files = []

    # Base modules (required for boot sequence)
    base_modules = ['boot.py', 'main.py', 'config.py', 'wifi.py', 'ntp.py', 'app_loader.py']
    for filename in base_modules:
        local_path = src_dir / filename
        if local_path.exists():
            files.append((str(local_path), filename))
        else:
            print(f"{RED}⚠️  {filename} no encontrado en src/{NC}")

    # Blink app (minimal default app for testing)
    blink_dir = src_dir / 'blink'
    if blink_dir.exists():
        # Create blink directory on ESP8266
        files.append((None, 'mkdir:blink'))

        # Upload __init__.py first (makes it a valid Python package)
        init_file = blink_dir / '__init__.py'
        if init_file.exists():
            files.append((str(init_file), 'blink/__init__.py'))

        # Upload other .py files in blink/
        for py_file in blink_dir.glob('*.py'):
            if py_file.name != '__init__.py':
                files.append((str(py_file), f'blink/{py_file.name}'))
    else:
        print(f"{YELLOW}⚠️  blink/ no encontrado - sistema puede no funcionar{NC}")

    return files


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
    
    print(f"{BLUE}[1/5] Puerto: {port}{NC}")
    
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
                    env_lines.append(f'WEBREPL_PASSWORD={escape_env_value(webrepl_pass)}\n')
                    password_found = True
                else:
                    env_lines.append(line)
        
        if not password_found:
            env_lines.append(f'\n# WebREPL Configuration\nWEBREPL_PASSWORD={escape_env_value(webrepl_pass)}\n')
        
        with open(env_path, 'w') as f:
            f.writelines(env_lines)
        print(f"{GREEN}✅ .env actualizado con WEBREPL_PASSWORD{NC}")
    
    # 1. Configurar webrepl_cfg.py
    print(f"\n{BLUE}[2/5] Configurando WebREPL...{NC}")
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
    print(f"\n{BLUE}[3/5] Copiando boot.py...{NC}")
    boot_path = project_dir / 'src' / 'boot.py'
    
    if not boot_path.exists():
        print(f"{RED}❌ No se encontró {boot_path}{NC}")
        sys.exit(1)
    
    if not run_ampy(['--port', port, 'put', str(boot_path), 'boot.py']):
        sys.exit(1)
    print(f"{GREEN}✅ boot.py instalado{NC}")
    
    # 3. Copiar .env
    print(f"\n{BLUE}[4/5] Copiando .env al ESP8266...{NC}")
    if env_path.exists():
        if run_ampy(['--port', port, 'put', str(env_path), '.env']):
            print(f"{GREEN}✅ .env copiado{NC}")
        else:
            print(f"{YELLOW}⚠️  No se pudo copiar .env{NC}")
            print(f"{YELLOW}   boot.py usará webrepl_cfg.py como fallback{NC}")
    else:
        print(f"{YELLOW}⚠️  .env no encontrado{NC}")
        print(f"{YELLOW}   boot.py usará webrepl_cfg.py o valores por defecto{NC}")

    # 5. Deploy complete system (base + blink app)
    print(f"\n{BLUE}[5/5] Desplegando sistema completo...{NC}")
    print(f"   Módulos base + app blink (sistema mínimo funcional)")

    base_files = get_base_files_to_upload(project_dir)

    if not base_files:
        print(f"{RED}❌ No se encontraron archivos del sistema{NC}")
        sys.exit(1)

    success_count = 0
    error_count = 0

    for item in base_files:
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
                print(f"   📁 {dir_name}/")
            except Exception:
                pass  # Directory might already exist, that's OK
            continue

        # Upload file
        if local_path and Path(local_path).exists():
            display_name = Path(local_path).name
            print(f"   📄 {remote_name}")

            if run_ampy(['--port', port, 'put', local_path, remote_name]):
                success_count += 1
            else:
                error_count += 1
                print(f"{RED}   ⚠️  Error al subir {remote_name}{NC}")

    print(f"\n{GREEN}✅ Sistema desplegado: {success_count} archivos{NC}")
    if error_count > 0:
        print(f"{YELLOW}⚠️  Advertencias: {error_count} archivos{NC}")

    # Resumen final
    print(f"\n{GREEN}{'='*60}{NC}")
    print(f"{GREEN}✅ Setup completado - Sistema listo para usar!{NC}")
    print(f"{GREEN}{'='*60}{NC}\n")

    print(f"{BLUE}📋 Resumen:{NC}")
    print(f"   • WebREPL: Configurado (password: {'*' * len(webrepl_pass)})")
    print(f"   • Archivos base: {success_count} módulos")
    print(f"   • App instalada: blink (LED test)")
    print(f"   • Config: .env {'copiado' if env_path.exists() else 'usando defaults'}")

    print(f"\n{GREEN}✨ Tu ESP8266 está listo para funcionar!{NC}")
    print(f"\n{YELLOW}Próximos pasos:{NC}")
    print(f"  1. Reinicia el ESP8266 (desconecta y reconecta USB)")
    print(f"  2. 💡 El LED debe comenzar a parpadear automáticamente")
    print(f"  3. Observa el proceso de boot abajo:")
    print(f"     - [main] Iniciando")
    print(f"     - [wifi] Conectando...")
    print(f"     - [ntp] Sincronizando...")
    print(f"     - [blink] Loop principal")
    print(f"  4. Anota la IP que aparece en el monitor")
    print(f"  5. WebREPL: ws://<IP>:8266")

    print(f"\n{BLUE}💡 Para cambiar de app (después del primer boot):{NC}")
    print(f"   python3 tools/deploy_wifi.py gallinero  # App gallinero")
    print(f"   python3 tools/deploy_wifi.py heladera   # App heladera")
    print(f"   python3 tools/deploy_wifi.py blink      # Volver a blink\n")
    
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

