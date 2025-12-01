#!/usr/bin/env python3
"""
reset_esp8266.py - Resetea el ESP8266 vía WebREPL y muestra logs después del reinicio

Uso:
    python3 tools/reset_esp8266.py              # Usa IP del .env
    python3 tools/reset_esp8266.py 192.168.1.50 # IP específica
    python3 tools/reset_esp8266.py heladera      # App específica (opcional)

Funcionamiento:
    1. Se conecta al ESP8266 vía WebREPL
    2. Ejecuta machine.reset() (soft reset, equivalente a botón RESET)
    3. Espera a que el ESP8266 se reinicie
    4. Se reconecta automáticamente
    5. Muestra logs en tiempo real del boot
"""

import sys
import time
from pathlib import Path

# Agregar directorio de herramientas al path
script_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(script_dir / 'common'))

from webrepl_client import WebREPLClient

# ANSI colors
RED = '\033[31m'
GREEN = '\033[32m'
YELLOW = '\033[33m'
BLUE = '\033[34m'
MAGENTA = '\033[35m'
CYAN = '\033[36m'
NC = '\033[0m'  # No Color


def wait_for_reboot(ip, password, project_dir, max_attempts=5, initial_wait=5):
    """
    Espera a que el ESP8266 se reinicie y reconecte a WebREPL.
    
    Args:
        ip: IP del ESP8266
        password: Password de WebREPL
        project_dir: Directorio raíz del proyecto
        max_attempts: Número máximo de intentos de reconexión (default: 5)
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
            # Conectar SIN interrumpir el programa (queremos leer logs del boot)
            if client.connect(interrupt_program=False):
                print(f"{GREEN}✅ Conectado{NC}")
                return client
            else:
                print(f"{YELLOW}✗{NC}")
        except Exception as e:
            print(f"{YELLOW}✗ ({e}){NC}")
        
        if attempt < max_attempts:
            wait_time = 3
            print(f"   Esperando {wait_time} segundos antes del siguiente intento...")
            time.sleep(wait_time)
    
    print(f"{RED}❌ No se pudo reconectar después de {max_attempts} intentos{NC}")
    return None


def stream_logs(client):
    """
    Lee logs en tiempo real desde el ESP8266 vía WebREPL (modo pasivo).
    
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
                    elif '[blink]' in text:
                        print(f"{MAGENTA}{text}{NC}", end='')
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
        print(f"{BLUE}💡 No se interrumpió el proceso{NC}")


def main():
    print(f"{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}")
    print(f"{CYAN}🔄 ESP8266 Soft Reset{NC}")
    print(f"{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}\n")

    # Parsear argumentos
    app_name = None
    ip_arg = None

    for arg in sys.argv[1:]:
        if '.' in arg and any(c.isdigit() for c in arg):
            ip_arg = arg
            print(f"{BLUE}🌐 IP especificada: {ip_arg}{NC}\n")
        else:
            app_name = arg
            print(f"{BLUE}📦 App: {app_name}{NC}\n")

    # Detectar directorio del proyecto
    project_dir = script_dir.parent

    # Conectar a WebREPL (usa .env o IP manual)
    auto_discover = not bool(ip_arg)
    client = WebREPLClient(project_dir=project_dir, verbose=True, auto_discover=auto_discover)

    # Configurar IP si se especificó manualmente
    if ip_arg:
        client.ip = ip_arg

    if not client.connect():
        print(f"{RED}❌ No se pudo conectar al ESP8266{NC}")
        sys.exit(1)

    # Guardar IP y password para reconexión después del reset
    target_ip = client.ip
    target_password = client.password

    print(f"\n{GREEN}✅ Conectado al ESP8266{NC}")
    print(f"{YELLOW}🔄 Ejecutando soft reset (machine.reset())...{NC}\n")

    try:
        # Ejecutar reset (esto desconectará el WebSocket)
        if client.reset():
            print(f"{GREEN}✅ Comando de reset enviado exitosamente{NC}")
            print(f"{BLUE}💡 El ESP8266 se está reiniciando...{NC}")
        else:
            print(f"{RED}❌ Error al enviar comando de reset{NC}")
            client.close()
            sys.exit(1)
    except Exception as e:
        print(f"{RED}❌ Error durante reset: {e}{NC}")
        client.close()
        sys.exit(1)
    finally:
        # Cerrar conexión actual (se perderá de todas formas por el reset)
        try:
            client.close()
        except:
            pass

    # Esperar reinicio y reconectar
    rebooted_client = wait_for_reboot(
        ip=target_ip,
        password=target_password,
        project_dir=project_dir,
        max_attempts=5,
        initial_wait=5
    )

    if not rebooted_client:
        print(f"{RED}❌ No se pudo reconectar después del reinicio{NC}")
        print(f"{YELLOW}   Verifica que el ESP8266 esté encendido y conectado a WiFi{NC}\n")
        sys.exit(1)

    # Mostrar logs del boot
    try:
        stream_logs(rebooted_client)
    finally:
        rebooted_client.close()
        print(f"{GREEN}👋 Desconectado{NC}\n")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{GREEN}👋 Cancelado por usuario{NC}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{RED}❌ Error: {e}{NC}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

