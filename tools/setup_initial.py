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

# Agregar tools/common al path para funciones compartidas
sys.path.insert(0, str(script_dir / 'common'))

from serial_monitor import SerialMonitor
from port_detection import find_serial_ports
from ampy_utils import (
    run_ampy,
    ensure_directory_exists,
    get_files_to_upload,
    verify_app_directory,
    check_ampy_installed,
    install_ampy,
    check_port_permissions,
    auto_reset_esp8266,
    GREEN, YELLOW, BLUE, RED, NC
)


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
    if not check_ampy_installed():
        if not install_ampy():
            sys.exit(1)

    # Directorios del proyecto
    project_dir = Path(__file__).parent.parent

    # Cargar configuración
    env = load_env(project_dir)

    # Obtener puerto
    port = env.get('SERIAL_PORT')
    if not port:
        ports = find_serial_ports()
        if len(ports) == 1:
            port = ports[0]
            print(f"{GREEN}🔍 Puerto detectado automáticamente: {port}{NC}")
        elif len(ports) > 1:
            print(f"{BLUE}Puertos serie detectados:{NC}")
            for i, p in enumerate(ports, 1):
                print(f"  {i}. {p}")
            try:
                choice = input(f"\n{YELLOW}Elige el puerto a usar (1-{len(ports)}): {NC}").strip()
                idx = int(choice) - 1
                if 0 <= idx < len(ports):
                    port = ports[idx]
                else:
                    print(f"{RED}❌ Selección inválida{NC}")
                    sys.exit(1)
            except (ValueError, KeyboardInterrupt, EOFError):
                print(f"{RED}❌ Puerto requerido{NC}")
                sys.exit(1)
        else:
            port = input(f"{YELLOW}Puerto serie: {NC}").strip()
    
    if not port:
        print(f"{RED}❌ Puerto requerido{NC}")
        sys.exit(1)

    print(f"{BLUE}[1/5] Puerto: {port}{NC}")

    # Verificar permisos del puerto ANTES de empezar
    if not check_port_permissions(port):
        sys.exit(1)
    
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

    base_files = get_files_to_upload(project_dir, app_name='blink', include_base=True)

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
            if ensure_directory_exists(port, dir_name, verbose=False):
                print(f"   📁 {dir_name}/")
            else:
                print(f"{YELLOW}   ⚠️  No se pudo crear/verificar directorio {dir_name}{NC}")
                error_count += 1
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
    
    # Verificar que el directorio blink existe y contiene archivos
    print(f"\n{BLUE}🔍 Verificando directorio blink/...{NC}")
    if verify_app_directory(port, 'blink', verbose=False):
        print(f"{GREEN}✅ Directorio blink/ verificado correctamente{NC}")
    else:
        print(f"{RED}❌ Directorio blink/ NO encontrado después del deploy{NC}")
        print(f"{YELLOW}   Esto indica un problema con la creación del directorio{NC}")

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

    # Opciones de reinicio
    print(f"{YELLOW}{'='*60}{NC}")
    print(f"{YELLOW}Opciones de reinicio:{NC}")
    print(f"  {GREEN}1{NC}. Automático (CTRL-D soft reset) {BLUE}← Recomendado{NC}")
    print(f"  {GREEN}2{NC}. Automático (DTR/RTS hard reset)")
    print(f"  {GREEN}3{NC}. Manual (desconecta/reconecta USB)")
    print(f"{YELLOW}{'='*60}{NC}\n")

    try:
        choice = input(f"{BLUE}Selecciona opción [1-3] (default=1): {NC}").strip() or '1'
    except (EOFError, KeyboardInterrupt):
        print(f"\n{YELLOW}Setup completado. Reinicia el ESP8266 manualmente.{NC}")
        return

    reset_success = False

    if choice == '1':
        reset_success = auto_reset_esp8266(port, method='soft')
    elif choice == '2':
        reset_success = auto_reset_esp8266(port, method='hard')
    elif choice == '3':
        try:
            input(f"{BLUE}Presiona Enter cuando hayas reiniciado manualmente...{NC}")
            reset_success = True
        except (EOFError, KeyboardInterrupt):
            print(f"\n{YELLOW}Setup completado. Reinicia el ESP8266 manualmente.{NC}")
            return
    else:
        print(f"{YELLOW}⚠️  Opción inválida, usando reset manual{NC}")
        try:
            input(f"{BLUE}Presiona Enter cuando hayas reiniciado manualmente...{NC}")
            reset_success = True
        except (EOFError, KeyboardInterrupt):
            print(f"\n{YELLOW}Setup completado. Reinicia el ESP8266 manualmente.{NC}")
            return

    if not reset_success:
        print(f"\n{YELLOW}Monitor serial NO se abrirá automáticamente{NC}")
        print(f"   Reinicia manualmente y ejecuta: python3 tools/open_repl.py")
        return

    print(f"\n{BLUE}📡 Abriendo monitor serial...{NC}\n")

    # Abrir monitor serial (BLOCKING)
    monitor = SerialMonitor(port=port, baudrate=115200, max_reconnect_attempts=5)
    monitor.start()


if __name__ == '__main__':
    main()

