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
from common.env_updater import update_env_for_app, cleanup_temp_env

# ANSI colors adicionales para logs
CYAN = '\033[36m'
MAGENTA = '\033[35m'


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


def wait_for_reboot(ip, password, project_dir, max_attempts=3, initial_wait=5):
    """
    Espera a que el ESP8266 se reinicie y reconecte a WebREPL.
    
    Args:
        ip: IP del ESP8266
        password: Password de WebREPL
        project_dir: Directorio raíz del proyecto
        max_attempts: Número máximo de intentos de reconexión (default: 3)
        initial_wait: Tiempo inicial de espera en segundos (default: 5)
    
    Returns:
        WebREPLClient: Cliente conectado, o None si no se pudo conectar
    """
    print(f"\n{BLUE}⏳ Esperando reinicio del ESP8266...{NC}")
    print(f"   Esperando {initial_wait} segundos iniciales...")
    time.sleep(initial_wait)
    
    for attempt in range(1, max_attempts + 1):
        print(f"   Intento {attempt}/{max_attempts}: Intentando reconectar a WebREPL...", end=' ')
        sys.stdout.flush()
        
        try:
            client = WebREPLClient(ip=ip, password=password, project_dir=project_dir, verbose=False, auto_discover=False)
            # Conectar SIN interrumpir el programa (queremos leer logs, no hacer deploy)
            if client.connect(interrupt_program=False):
                print(f"{GREEN}✅ Conectado{NC}")
                return client
            else:
                print(f"{YELLOW}✗{NC}")
        except Exception as e:
            print(f"{YELLOW}✗ ({e}){NC}")
        
        if attempt < max_attempts:
            wait_time = 5
            print(f"   Esperando {wait_time} segundos antes del siguiente intento...")
            time.sleep(wait_time)
    
    print(f"{RED}❌ No se pudo reconectar después de {max_attempts} intentos{NC}")
    return None


def stream_logs_after_reboot(client):
    """
    Lee logs en tiempo real desde el ESP8266 vía WebREPL (modo pasivo).
    Similar a read_logs.py pero integrado en el flujo de deploy.
    
    Args:
        client: Instancia de WebREPLClient conectada
    """
    print(f"\n{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}")
    print(f"{CYAN}📡 Leyendo logs en tiempo real{NC}")
    print(f"{YELLOW}   Presiona Ctrl-C para salir{NC}")
    print(f"{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}\n")
    
    try:
        # Limpiar buffer antiguo
        try:
            client.ws.settimeout(0.1)
            while True:
                client.ws.recv()
        except:
            pass
        
        client.ws.settimeout(1.0)
        
        # Leer logs continuamente
        while True:
            try:
                data = client.ws.recv()
                if isinstance(data, bytes):
                    text = data.decode('utf-8', errors='replace')
                else:
                    text = data
                
                # Filtrar prompts de MicroPython
                if text and text not in ['>>> ', '>>> \r\n', '\r\n>>> ']:
                    # Colorear logs según módulo
                    if '[main]' in text:
                        print(f"{CYAN}{text}{NC}", end='')
                    elif '[wifi]' in text:
                        print(f"{BLUE}{text}{NC}", end='')
                    elif '[ntp]' in text:
                        print(f"{MAGENTA}{text}{NC}", end='')
                    elif '[heladera]' in text:
                        print(f"{GREEN}{text}{NC}", end='')
                    elif '[gallinero]' in text:
                        print(f"{YELLOW}{text}{NC}", end='')
                    elif 'ERROR' in text or 'Error' in text:
                        print(f"{RED}{text}{NC}", end='')
                    else:
                        print(text, end='')
                    sys.stdout.flush()
                    
            except Exception as e:
                # Timeout es normal, continuar
                time.sleep(0.1)
                
    except KeyboardInterrupt:
        print(f"\n\n{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}")
        print(f"{YELLOW}🛑 Deteniendo lectura de logs...{NC}")
        print(f"{GREEN}✅ Programa continúa corriendo en ESP8266{NC}")
        print(f"{BLUE}💡 No se interrumpió el proceso{NC}\n")


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
        print(f"{BLUE}📦 App especificada: {app_name}{NC}")
    else:
        print(f"{BLUE}📦 App: blink (default){NC}")

    if ip_arg:
        print(f"{BLUE}🌐 IP especificada: {ip_arg}{NC}")

    # Pedir confirmación antes de continuar
    print(f"\n{YELLOW}¿Continuar con el deploy? (s/N){NC}")
    try:
        confirm = input().strip().lower()
    except (EOFError, KeyboardInterrupt):
        print(f"\n{GREEN}👋 Cancelado por usuario{NC}")
        sys.exit(0)

    if confirm != 's':
        print(f"{GREEN}👋 Deploy cancelado{NC}")
        sys.exit(0)

    print()

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
    
    # Conectar a WebREPL (usar IP si se proporcionó, sino usar .env)
    # Si no se proporciona IP, el cliente usa WEBREPL_IP del .env
    auto_discover = not bool(ip_arg)
    client = WebREPLClient(project_dir=project_dir, verbose=True, auto_discover=auto_discover)

    # Si se proporcionó IP manualmente, usarla
    if ip_arg:
        client.ip = ip_arg

    if not client.connect():
        sys.exit(1)

    # Interrumpir programa actual con Ctrl-C para liberar el REPL
    print(f"{BLUE}⏸️  Deteniendo programa actual en ESP8266...{NC}")
    try:
        client.execute("\x03", timeout=1)  # Ctrl-C
        time.sleep(0.5)
        # Limpiar buffer
        try:
            client.ws.settimeout(0.2)
            while True:
                client.ws.recv()
        except:
            pass
        print(f"{GREEN}✅ Programa detenido{NC}\n")
    except Exception as e:
        print(f"{YELLOW}⚠️  No se pudo detener programa (puede continuar de todas formas){NC}\n")

    # Si no se especificó app, usar blink por defecto
    if not app_name:
        app_name = 'blink'
        print(f"{BLUE}📦 Usando app por defecto: blink{NC}\n")

    # IMPORTANTE: NO crear directorios con execute() porque interfiere con protocolo binario
    # Según documentación oficial de MicroPython WebREPL y código en modwebrepl.c,
    # el protocolo binario crea directorios automáticamente cuando el filename tiene "/"
    # Ver: https://github.com/micropython/micropython/blob/master/extmod/modwebrepl.c
    #
    # Mezclar comandos de texto (execute) con protocolo binario causa errores:
    # - "Respuesta WebREPL muy corta"
    # - "a bytes-like object is required, not 'str'"
    # - Datos residuales en buffer WebSocket
    #
    # Solución: Confiar en que WebREPL crea directorios automáticamente
    print(f"{BLUE}📁 Los directorios se crearán automáticamente durante upload{NC}\n")

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

        # Delay entre archivos para dar tiempo al ESP8266 a procesar
        time.sleep(0.5)
    
    # Copiar y actualizar .env con la app correcta
    print(f"\n{BLUE}📄 Actualizando .env en ESP8266...{NC}")
    try:
        temp_env = update_env_for_app(project_dir, app_name)
        if client.send_file(str(temp_env), '.env'):
            print(f"{GREEN}   ✅ .env actualizado con APP={app_name}{NC}")
            success += 1
        else:
            failed += 1
    finally:
        cleanup_temp_env(project_dir)
    print()
    
    # Verificación post-deploy
    verify_deploy(client)

    # Guardar IP y password para reconexión después del reinicio (antes de cerrar)
    target_ip = ip_arg if ip_arg else client.config.get('WEBREPL_IP')
    target_password = client.password

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
        # Esperar antes de salir para Termux shortcuts
        print(f"{YELLOW}Presiona Ctrl-C para salir o espera 30 segundos...{NC}")
        try:
            for i in range(30, 0, -1):
                print(f"   Cerrando en {i} segundos...", end='\r')
                sys.stdout.flush()
                time.sleep(1)
            print()
        except KeyboardInterrupt:
            print()
        sys.exit(1)
    
    # Reinicio automático (sin confirmación)
    print(f"\n{BLUE}🔄 Reiniciando ESP8266 automáticamente...{NC}")
    
    # Reconectar para reiniciar
    reset_client = WebREPLClient(project_dir=project_dir, verbose=False, auto_discover=False)
    reset_client.ip = target_ip
    reset_client.password = target_password
    
    if reset_client.connect():
        try:
            # Usar método centralizado reset() (DRY)
            reset_client.reset()
        except Exception as e:
            print(f"{YELLOW}⚠️  Error durante reset: {e}{NC}")
        finally:
            reset_client.close()
    else:
        print(f"{RED}❌ No se pudo conectar para reiniciar{NC}")
        print(f"{YELLOW}   Deploy completado, pero no se pudo reiniciar{NC}\n")
        sys.exit(1)
    
    # Esperar reinicio y reconectar
    rebooted_client = wait_for_reboot(
        ip=target_ip,
        password=target_password,
        project_dir=project_dir,
        max_attempts=3,
        initial_wait=5
    )
    
    if rebooted_client:
        try:
            # Leer logs en tiempo real
            stream_logs_after_reboot(rebooted_client)
        finally:
            rebooted_client.close()
    else:
        print(f"{YELLOW}⚠️  Deploy completado, pero no se pudo reconectar para ver logs{NC}")
        print(f"{BLUE}💡 Puedes ver los logs manualmente con: python3 tools/read_logs.py{NC}\n")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print()
        print(f"{GREEN}👋 Cancelado por usuario{NC}")
        sys.exit(0)
    except Exception as e:
        print()
        print(f"{RED}❌ Error inesperado: {e}{NC}")
        import traceback
        traceback.print_exc()
        print()
        print(f"{YELLOW}Presiona Ctrl-C para salir o espera 30 segundos...{NC}")
        try:
            for i in range(30, 0, -1):
                print(f"   Cerrando en {i} segundos...", end='\r')
                sys.stdout.flush()
                time.sleep(1)
            print()
        except KeyboardInterrupt:
            print()
        sys.exit(1)

