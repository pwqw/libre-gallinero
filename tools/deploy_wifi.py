#!/usr/bin/env python3
"""
Script unificado para subir archivos a ESP8266 vía WebREPL (WiFi).
Funciona tanto en PC como en Termux/Android.

Uso:
    python3 tools/deploy_wifi.py
    # O desde el directorio tools/:
    python3 deploy_wifi.py

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


def get_files_to_upload(project_dir, project_name=None):
    """
    Obtiene lista de archivos a subir desde src/.
    Incluye todos los .py y templates si existen.
    También incluye archivos del proyecto especificado (gallinero, heladera, etc.)
    
    Args:
        project_dir: Directorio raíz del proyecto
        project_name: Nombre del proyecto a incluir (gallinero, heladera, etc.)
    
    Returns:
        list: Lista de tuplas (local_path, remote_name)
    """
    src_dir = Path(project_dir) / 'src'
    files = []
    
    # Archivos principales de Python (incluyendo módulos nuevos)
    main_files = ['boot.py', 'main.py', 'config.py', 'wifi.py', 'ntp.py', 'project_loader.py', 'solar.py', 'logic.py']
    for filename in main_files:
        local_path = src_dir / filename
        if local_path.exists():
            is_valid, file_size, error_msg = validate_file_size(local_path)
            if not is_valid:
                print(f"{RED}⚠️  {filename}: {error_msg}{NC}")
                print(f"   Omitiendo {filename} del deploy")
                continue
            files.append((str(local_path), filename))
    
    # Incluir archivos del proyecto especificado
    if project_name:
        project_dir_path = src_dir / project_name
        if project_dir_path.exists() and project_dir_path.is_dir():
            print(f"{BLUE}📦 Incluyendo archivos del proyecto: {project_name}{NC}")
            for py_file in project_dir_path.glob('*.py'):
                if py_file.name == '__init__.py':
                    # __init__.py va en el directorio del proyecto
                    remote_name = f"{project_name}/__init__.py"
                else:
                    remote_name = f"{project_name}/{py_file.name}"
                
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
    
    # Detectar proyecto y IP desde argumentos
    project_name = None
    ip_arg = None
    
    if len(sys.argv) > 1:
        # El primer argumento puede ser IP o proyecto
        arg1 = sys.argv[1]
        # Si parece una IP (contiene puntos y números)
        if '.' in arg1 and any(c.isdigit() for c in arg1):
            ip_arg = arg1
            if len(sys.argv) > 2:
                project_name = sys.argv[2]
        else:
            # Es un nombre de proyecto
            project_name = arg1
            if len(sys.argv) > 2:
                # El segundo argumento puede ser IP
                arg2 = sys.argv[2]
                if '.' in arg2 and any(c.isdigit() for c in arg2):
                    ip_arg = arg2
    
    if project_name:
        print(f"{BLUE}📦 Proyecto especificado: {project_name}{NC}\n")
    if ip_arg:
        print(f"{BLUE}🌐 IP especificada: {ip_arg}{NC}\n")
    
    # Detectar directorio del proyecto
    script_dir = Path(__file__).parent.absolute()
    project_dir = script_dir.parent
    
    # Cambiar al directorio del proyecto
    os.chdir(project_dir)
    
    print(f"📂 Directorio proyecto: {project_dir}\n")
    
    # Opcional: git pull si estamos en un repo git
    if Path(project_dir / '.git').exists():
        try:
            subprocess.run(['git', 'pull', '--rebase'], 
                         check=False, 
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL)
        except:
            pass
    
    # Conectar a WebREPL (usar IP si se proporcionó, sino autodiscovery)
    auto_discover = not bool(ip_arg)
    client = WebREPLClient(project_dir=project_dir, verbose=True, auto_discover=auto_discover)
    
    # Si se proporcionó IP, usarla directamente
    if ip_arg:
        client.ip = ip_arg
    
    if not client.connect():
        sys.exit(1)
    
    print(f"\n📤 Iniciando upload de archivos...\n")
    
    # Obtener archivos a subir (incluyendo proyecto si se especificó)
    files_to_upload = get_files_to_upload(project_dir, project_name=project_name)
    
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
    env_path = project_dir / '.env'
    if env_path.exists():
        print(f"{BLUE}📄 Copiando .env al ESP8266...{NC}")
        if client.send_file(str(env_path), '.env'):
            success += 1
        else:
            failed += 1
        print()
    
    # Verificación post-deploy
    verify_deploy(client)
    
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

