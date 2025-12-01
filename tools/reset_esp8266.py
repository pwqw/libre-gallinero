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

from webrepl_client import WebREPLClient, wait_for_reboot, stream_logs, RED, GREEN, YELLOW, BLUE, CYAN, NC


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

