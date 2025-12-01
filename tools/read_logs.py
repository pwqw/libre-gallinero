#!/usr/bin/env python3
"""
read_logs.py - Lee logs del ESP8266 en tiempo real via WebREPL (NO INVASIVO)

Uso:
    python3 tools/read_logs.py              # Usa IP del .env, modo pasivo
    python3 tools/read_logs.py 192.168.1.50 # IP específica
    python3 tools/read_logs.py --restart    # Reinicia main.py (invasivo)
    python3 tools/read_logs.py --history    # Muestra buffer histórico

Modo por defecto (NO INVASIVO):
    - NO reinicia el programa
    - Solo lee stdout actual sin interrumpir
    - Mantiene conexión WiFi estable
"""

import sys
import time
from pathlib import Path
import websocket

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

def main():
    print(f"{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}")
    print(f"{CYAN}📡 ESP8266 Log Reader (NO INVASIVO){NC}")
    print(f"{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}\n")

    # Parsear argumentos
    app_name = None
    ip_arg = None
    restart_mode = False
    history_mode = False

    for arg in sys.argv[1:]:
        if arg == '--restart':
            restart_mode = True
            print(f"{YELLOW}⚠️  MODO INVASIVO: Reiniciará main.py{NC}\n")
        elif arg == '--history':
            history_mode = True
            print(f"{BLUE}📜 MODO HISTÓRICO: Leyendo buffer{NC}\n")
        elif '.' in arg and any(c.isdigit() for c in arg):
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

    # En modo pasivo (no restart), NO interrumpir el programa
    # En modo restart, SÍ interrumpir para reiniciar
    interrupt_on_connect = restart_mode
    if not client.connect(interrupt_program=interrupt_on_connect):
        sys.exit(1)

    # Modo histórico: leer buffer y salir
    if history_mode:
        print(f"\n{GREEN}✅ Conectado - Leyendo buffer histórico{NC}\n")
        print(f"{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}\n")
        try:
            # Limpiar buffer primero
            client.ws.settimeout(0.2)
            try:
                while True:
                    client.ws.recv()
            except:
                pass

            # Obtener buffer histórico
            client.ws.settimeout(5.0)
            client.ws.send("import logger\r\n")
            time.sleep(0.3)
            client.ws.send("print(logger.get())\r\n")
            time.sleep(1.0)

            # Leer respuesta
            history_output = ""
            try:
                for _ in range(10):
                    data = client.ws.recv()
                    if isinstance(data, bytes):
                        history_output += data.decode('utf-8', errors='replace')
                    else:
                        history_output += data
            except:
                pass

            # Mostrar historial
            if history_output:
                print(f"{GREEN}{history_output}{NC}")
            else:
                print(f"{YELLOW}⚠️  No hay logs en buffer (o logger no inicializado){NC}")

            print(f"\n{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}")
        finally:
            client.close()
            print(f"{GREEN}👋 Desconectado{NC}\n")
        return

    # Modo normal o restart
    mode_desc = "Leyendo logs en tiempo real (PASIVO)" if not restart_mode else "Reiniciando y leyendo logs (INVASIVO)"
    print(f"\n{GREEN}✅ Conectado - {mode_desc}{NC}")
    print(f"{YELLOW}   Presiona Ctrl-C para salir{NC}\n")
    print(f"{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}\n")

    try:
        if restart_mode:
            # MODO INVASIVO: Interrumpir y reiniciar
            client.ws.send("\x03")  # Ctrl-C
            time.sleep(0.3)

            # Limpiar buffer
            try:
                client.ws.settimeout(0.2)
                while True:
                    client.ws.recv()
            except:
                pass

            # Reiniciar programa
            print(f"{YELLOW}🔄 Reiniciando main.py...{NC}\n")
            client.ws.settimeout(1.0)
            client.ws.send("import main\r\n")
            time.sleep(0.5)
            client.ws.send("main.main()\r\n")
            time.sleep(0.3)
        else:
            # MODO PASIVO: Solo leer stdout actual sin interrumpir
            print(f"{GREEN}📖 Modo pasivo: leyendo stdout sin interrumpir programa{NC}\n")
            print(f"{BLUE}💡 Esperando logs... (heartbeat cada ~15s){NC}\n")
            # Limpiar buffer antiguo
            try:
                client.ws.settimeout(0.1)
                while True:
                    client.ws.recv()
            except:
                pass
            # Timeout más corto para lectura más reactiva
            client.ws.settimeout(0.5)

        # Leer logs continuamente
        last_log_time = time.time()
        no_data_warning_shown = False
        while True:
            try:
                data = client.ws.recv()
                last_log_time = time.time()
                no_data_warning_shown = False
                
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

            except websocket.WebSocketTimeoutException:
                # Timeout es normal, verificar si hay datos recientes
                elapsed = time.time() - last_log_time
                if elapsed > 30 and not no_data_warning_shown:
                    print(f"{YELLOW}⏳ Sin logs por {int(elapsed)}s (normal si app no genera output){NC}")
                    no_data_warning_shown = True
                time.sleep(0.1)
            except Exception as e:
                # Otros errores: continuar
                time.sleep(0.1)

    except KeyboardInterrupt:
        print(f"\n\n{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}")
        print(f"{YELLOW}🛑 Deteniendo lectura de logs...{NC}")

        if restart_mode:
            # Solo interrumpir si estábamos en modo restart
            try:
                client.ws.send("\x03")  # Ctrl-C
                time.sleep(0.3)
                print(f"{GREEN}✅ Programa detenido en ESP8266{NC}")
                print(f"{BLUE}💡 El ESP8266 está ahora en el REPL{NC}")
            except:
                pass
        else:
            print(f"{GREEN}✅ Programa continúa corriendo en ESP8266{NC}")
            print(f"{BLUE}💡 No se interrumpió el proceso{NC}")

    finally:
        client.close()
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
