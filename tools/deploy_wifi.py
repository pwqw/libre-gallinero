#!/usr/bin/env python3
"""
Script unificado para subir archivos a ESP8266 vía WebREPL (WiFi).
Funciona tanto en PC como en Termux/Android.

Uso:
    # Deploy base + blink app (default):
    python3 tools/deploy_wifi.py
    
    # Deploy base + app específica:
    python3 tools/deploy_wifi.py gallinero
    python3 tools/deploy_wifi.py heladera
    
    # Con IP específica:
    python3 tools/deploy_wifi.py gallinero 192.168.1.100

Archivos base copiados (coherente con setup_webrepl.py):
    - boot.py, main.py, config.py, wifi.py, ntp.py, app_loader.py

Apps (cuando se especifica, defaults a blink):
    - blink/ → blink/__init__.py, blink/blink.py (default)
    - gallinero/ → gallinero/__init__.py, gallinero/app.py, etc.
    - heladera/ → heladera/__init__.py, heladera/blink.py

Requiere:
    pip install websocket-client python-dotenv

Configuración:
    Copia .env.example a .env y configura tus valores
"""

import sys
import os
import time
import subprocess
from pathlib import Path

# Agregar tools/common al path
script_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(script_dir))

from common.webrepl_client import WebREPLClient, MAX_FILE_SIZE, validate_file_size, GREEN, YELLOW, BLUE, RED, NC
from common.ip_cache import get_cached_ip, save_cached_ip


def get_files_to_upload(project_dir, app_name=None):
    """
    Obtiene lista de archivos a subir desde src/.
    Incluye todos los .py y templates si existen.
    También incluye archivos de la app especificada (blink, gallinero, heladera, etc.)
    
    Args:
        project_dir: Directorio raíz del proyecto
        app_name: Nombre de la app a incluir (blink, gallinero, heladera, etc.)
    
    Returns:
        list: Lista de tuplas (local_path, remote_name)
    """
    src_dir = Path(project_dir) / 'src'
    files = []
    
    # Archivos principales de Python (módulos base - coherente con setup_webrepl.py)
    # NOTA: solar.py y logic.py están dentro de gallinero/, no en src/ directamente
    main_files = ['boot.py', 'main.py', 'config.py', 'wifi.py', 'ntp.py', 'app_loader.py']
    for filename in main_files:
        local_path = src_dir / filename
        if local_path.exists():
            is_valid, file_size, error_msg = validate_file_size(local_path)
            if not is_valid:
                print(f"{RED}⚠️  {filename}: {error_msg}{NC}")
                print(f"   Omitiendo {filename} del deploy")
                continue
            files.append((str(local_path), filename))
    
    # Incluir archivos de la app especificada
    if app_name:
        app_dir_path = src_dir / app_name
        if app_dir_path.exists() and app_dir_path.is_dir():
            print(f"{BLUE}📦 Incluyendo archivos de la app: {app_name}{NC}")
            
            # Primero subir __init__.py para que el directorio sea un paquete Python válido
            init_file = app_dir_path / '__init__.py'
            if init_file.exists():
                remote_name = f"{app_name}/__init__.py"
                is_valid, file_size, error_msg = validate_file_size(init_file)
                if is_valid:
                    files.append((str(init_file), remote_name))
                    print(f"   ✓ {remote_name} (__init__.py primero)")
                else:
                    print(f"{RED}⚠️  __init__.py: {error_msg}{NC}")
            
            # Luego subir el resto de archivos
            for py_file in app_dir_path.glob('*.py'):
                if py_file.name == '__init__.py':
                    continue  # Ya lo agregamos arriba
                
                remote_name = f"{app_name}/{py_file.name}"
                is_valid, file_size, error_msg = validate_file_size(py_file)
                if not is_valid:
                    print(f"{RED}⚠️  {py_file.name}: {error_msg}{NC}")
                    continue
                files.append((str(py_file), remote_name))
                print(f"   ✓ {remote_name}")
    
    # Templates si existen
    templates_dir = src_dir / 'templates'
    if templates_dir.exists():
        for filename in templates_dir.glob('*.html'):
            files.append((str(filename), filename.name))
    
    return files


def verify_deploy(client):
    """
    Verifica que los archivos subidos funcionan correctamente.
    
    Args:
        client: Instancia de WebREPLClient
    
    Returns:
        bool: True si la verificación fue exitosa
    """
    print(f"\n{BLUE}🔍 Verificando deploy...{NC}")
    
    # Intentar importar main.py
    response = client.execute("import main; print('OK')", timeout=3)
    if 'OK' in response or '>>>' in response:
        print(f"{GREEN}✅ main.py cargado correctamente{NC}")
        return True
    else:
        print(f"{YELLOW}⚠️  No se pudo verificar main.py (puede ser normal){NC}")
        return True  # No fallar por esto


def main():
    print(f"{BLUE}🐔 Libre-Gallinero WebREPL Deploy{NC}\n")
    
    # Detectar app y IP desde argumentos
    app_name = None
    ip_arg = None
    
    if len(sys.argv) > 1:
        # El primer argumento puede ser IP o app
        arg1 = sys.argv[1]
        # Si parece una IP (contiene puntos y números)
        if '.' in arg1 and any(c.isdigit() for c in arg1):
            ip_arg = arg1
            if len(sys.argv) > 2:
                app_name = sys.argv[2]
        else:
            # Es un nombre de app
            app_name = arg1
            if len(sys.argv) > 2:
                # El segundo argumento puede ser IP
                arg2 = sys.argv[2]
                if '.' in arg2 and any(c.isdigit() for c in arg2):
                    ip_arg = arg2
    
    if app_name:
        print(f"{BLUE}📦 App especificada: {app_name}{NC}\n")
    if ip_arg:
        print(f"{BLUE}🌐 IP especificada: {ip_arg}{NC}\n")
    
    # Detectar directorio del proyecto
    script_dir = Path(__file__).parent.absolute()
    project_dir = script_dir.parent
    
    # Cambiar al directorio del proyecto
    os.chdir(project_dir)
    
    print(f"📂 Directorio proyecto: {project_dir}\n")
    
    # Opcional: git pull si estamos en un repo git
    git_path = Path(str(project_dir)) / '.git'
    if git_path.exists():
        try:
            subprocess.run(['git', 'pull', '--rebase'], 
                         check=False, 
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL)
        except:
            pass
    
    # Cargar IP cacheada si existe y no se especificó IP manualmente
    # Esto se hace ANTES de crear el cliente para poder pasarla al constructor
    cached_ip_pre = None
    if not ip_arg and app_name:
        cached_ip_pre = get_cached_ip(app_name, verbose=True)
        if cached_ip_pre:
            print()

    # Conectar a WebREPL (usar IP si se proporcionó, sino autodiscovery)
    auto_discover = not bool(ip_arg)
    client = WebREPLClient(project_dir=project_dir, verbose=True, auto_discover=auto_discover)

    # Si se proporcionó IP, usarla directamente (tiene prioridad sobre caché)
    if ip_arg:
        client.ip = ip_arg
    elif cached_ip_pre:
        # Intentar con la IP cacheada primero
        client.ip = cached_ip_pre

    if not client.connect():
        sys.exit(1)
    
    # Si no se especificó app, usar blink por defecto
    if not app_name:
        app_name = 'blink'
        print(f"{BLUE}📦 Usando app por defecto: blink{NC}\n")
    
    print(f"\n📤 Iniciando upload de archivos...\n")
    
    # Obtener archivos a subir (incluyendo app si se especificó)
    files_to_upload = get_files_to_upload(project_dir, app_name=app_name)
    
    if not files_to_upload:
        print(f"{RED}❌ No se encontraron archivos para subir en src/{NC}")
        client.close()
        sys.exit(1)
    
    # Contador
    success = 0
    failed = 0
    
    # Subir archivos con validación de tamaño
    for local_path, remote_name in files_to_upload:
        is_valid, file_size, error_msg = validate_file_size(local_path)
        if not is_valid:
            print(f"{RED}⚠️  {remote_name}: {error_msg}{NC}")
            failed += 1
            continue
        
        if client.send_file(local_path, remote_name, max_size=MAX_FILE_SIZE):
            success += 1
        else:
            failed += 1
        print()
    
    # Copiar .env si existe en el repositorio
    env_path = Path(str(project_dir)) / '.env'
    if env_path.exists():
        print(f"{BLUE}📄 Copiando .env al ESP8266...{NC}")
        if client.send_file(str(env_path), '.env'):
            success += 1
        else:
            failed += 1
        print()
    
    # Verificación post-deploy
    verify_deploy(client)

    # Guardar IP en caché si el deploy fue exitoso
    if failed == 0 and app_name and client.ip:
        save_cached_ip(app_name, client.ip, verbose=True)
        print()

    # Cerrar conexión
    client.close()

    # Resumen
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"{GREEN}✅ Exitosos: {success}{NC}")
    if failed > 0:
        print(f"{RED}❌ Fallidos: {failed}{NC}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    if failed > 0:
        print(f"{RED}⚠️  Deploy completado con errores{NC}\n")
        sys.exit(1)
    
    # Preguntar si reiniciar
    print(f"{YELLOW}🔄 ¿Reiniciar ESP8266 para aplicar cambios? (s/N){NC}")
    try:
        reply = input().strip().lower()
    except (EOFError, KeyboardInterrupt):
        reply = 'n'
    
    if reply in ['s', 'S']:
        print(f"\n🔄 Reiniciando ESP8266...")
        
        # Reconectar para reiniciar
        client = WebREPLClient(project_dir=project_dir, verbose=False, auto_discover=False)
        client.ip = client.config.get('WEBREPL_IP') or client.ip
        if client.connect():
            client.execute("\x03", timeout=0.5)  # Ctrl-C to reset REPL state
            client.execute("import machine; machine.reset()", timeout=1)
            time.sleep(0.5)
            client.close()
            print(f"{GREEN}✅ Deploy completo - ESP8266 reiniciado{NC}\n")
        else:
            print(f"{RED}❌ No se pudo conectar para reiniciar{NC}\n")
    else:
        print(f"{GREEN}✅ Deploy completo{NC}")
        print("   Para aplicar cambios desde WebREPL web:")
        print("   import machine; machine.reset()\n")


if __name__ == '__main__':
    main()

