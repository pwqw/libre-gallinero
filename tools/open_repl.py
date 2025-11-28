#!/usr/bin/env python3
"""
Script interactivo para abrir WebREPL del ESP8266.
Usa IPs cacheadas por app y solicita password si falla.
"""

import sys
import os
from pathlib import Path

# Agregar tools/common al path
script_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(script_dir))

from common.webrepl_client import WebREPLClient, GREEN, YELLOW, BLUE, RED, NC, load_config
from common.ip_cache import get_cached_ip


def select_app():
    """Permite al usuario seleccionar qué app usar (para obtener IP cacheada)"""
    print(f"{BLUE}📱 Selecciona la app para obtener IP cacheada:{NC}")
    print(f"  1. Blink")
    print(f"  2. Gallinero")
    print(f"  3. Heladera")
    print(f"  4. Usar IP del .env")
    print(f"  5. Ingresar IP manualmente")
    print()

    try:
        choice = input(f"{YELLOW}Selección (1-5): {NC}").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)

    app_map = {
        '1': 'blink',
        '2': 'gallinero',
        '3': 'heladera',
    }

    if choice in app_map:
        return app_map[choice], None
    elif choice == '4':
        return None, None  # Usar .env
    elif choice == '5':
        try:
            ip = input(f"{YELLOW}Ingresa IP: {NC}").strip()
            return None, ip
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)
    else:
        print(f"{RED}❌ Opción inválida{NC}")
        sys.exit(1)


def get_password(config, retry=False):
    """Obtiene password del .env o solicita al usuario"""
    if not retry:
        # Primer intento: usar password del .env
        password = config.get('WEBREPL_PASSWORD')
        if password:
            return password

    # Solicitar password al usuario
    try:
        import getpass
        print(f"{YELLOW}⚠️  Password del .env falló o no está configurado{NC}")
        password = getpass.getpass(f"{YELLOW}Ingresa WebREPL password: {NC}")
        return password.strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)
    except ImportError:
        # getpass no disponible, usar input normal
        print(f"{YELLOW}⚠️  Password del .env falló o no está configurado{NC}")
        try:
            password = input(f"{YELLOW}Ingresa WebREPL password: {NC}").strip()
            return password
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)


def open_repl_session(client):
    """Abre sesión interactiva de REPL"""
    print()
    print(f"{GREEN}{'━' * 60}{NC}")
    print(f"{GREEN}🐍 MicroPython WebREPL - Sesión Interactiva{NC}")
    print(f"{GREEN}{'━' * 60}{NC}")
    print()
    print(f"{BLUE}Comandos útiles:{NC}")
    print(f"  help()              - Ayuda de MicroPython")
    print(f"  import machine      - Módulo de hardware")
    print(f"  machine.reset()     - Reiniciar ESP8266")
    print(f"  import os           - Sistema de archivos")
    print(f"  os.listdir()        - Listar archivos")
    print(f"  Ctrl-C              - Interrumpir ejecución")
    print(f"  Ctrl-D o 'exit()'   - Salir del REPL")
    print()
    print(f"{YELLOW}Escribe tus comandos a continuación:{NC}")
    print(f"{GREEN}{'━' * 60}{NC}")
    print()

    # Limpiar buffer inicial
    try:
        client.ws.settimeout(0.5)
        while True:
            try:
                data = client.ws.recv()
                if isinstance(data, bytes):
                    output = data.decode('utf-8', errors='ignore')
                else:
                    output = data
                # Mostrar prompt inicial si existe
                if '>>>' in output:
                    sys.stdout.write(output)
                    sys.stdout.flush()
                    break
            except:
                break
    except:
        pass

    # Loop interactivo
    try:
        while True:
            try:
                # Leer comando del usuario
                try:
                    command = input()
                except EOFError:
                    # Ctrl-D
                    print()
                    print(f"{GREEN}👋 Saliendo del REPL...{NC}")
                    break

                # Comandos especiales
                if command.strip().lower() in ['exit()', 'exit', 'quit()', 'quit']:
                    print(f"{GREEN}👋 Saliendo del REPL...{NC}")
                    break

                # Enviar comando al ESP8266
                try:
                    client.ws.send(command + '\r\n')
                except (ConnectionResetError, BrokenPipeError):
                    print(f"{RED}❌ Conexión perdida con ESP8266{NC}")
                    break

                # Recibir y mostrar respuesta
                import time
                time.sleep(0.1)  # Dar tiempo al ESP8266 a procesar

                response = ""
                start_time = time.time()
                timeout = 5

                while time.time() - start_time < timeout:
                    try:
                        client.ws.settimeout(0.5)
                        data = client.ws.recv()
                        if isinstance(data, bytes):
                            response += data.decode('utf-8', errors='ignore')
                        else:
                            response += data

                        # Si vemos el prompt, terminamos
                        if '>>>' in response:
                            break
                    except:
                        # Timeout o fin de datos
                        if response:
                            break
                        continue

                # Mostrar respuesta
                if response:
                    sys.stdout.write(response)
                    sys.stdout.flush()

            except KeyboardInterrupt:
                # Ctrl-C: enviar interrupción al ESP8266
                print()
                try:
                    client.ws.send('\x03')  # Ctrl-C
                    time.sleep(0.2)
                    # Recibir respuesta
                    try:
                        client.ws.settimeout(0.5)
                        data = client.ws.recv()
                        if isinstance(data, bytes):
                            output = data.decode('utf-8', errors='ignore')
                        else:
                            output = data
                        sys.stdout.write(output)
                        sys.stdout.flush()
                    except:
                        pass
                except:
                    print(f"{RED}❌ Error enviando Ctrl-C{NC}")
                continue

    except Exception as e:
        print()
        print(f"{RED}❌ Error en sesión REPL: {e}{NC}")

    print()
    print(f"{GREEN}{'━' * 60}{NC}")
    print(f"{GREEN}Sesión REPL terminada{NC}")
    print(f"{GREEN}{'━' * 60}{NC}")


def main():
    print(f"{BLUE}🐔 Libre-Gallinero WebREPL{NC}\n")

    # Detectar directorio del proyecto
    project_dir = script_dir.parent
    config = load_config(project_dir)

    # Seleccionar app / IP
    app_name, manual_ip = select_app()
    print()

    # Obtener IP (prioridad: manual > caché > .env)
    ip = None
    if manual_ip:
        ip = manual_ip
        print(f"{BLUE}🌐 Usando IP manual: {ip}{NC}")
    elif app_name:
        cached_ip = get_cached_ip(app_name, verbose=True)
        if cached_ip:
            ip = cached_ip
        else:
            print(f"{YELLOW}⚠️  No hay IP cacheada para '{app_name}', usando .env{NC}")
            ip = config.get('WEBREPL_IP')
    else:
        # Usar IP del .env
        ip = config.get('WEBREPL_IP')
        if ip:
            print(f"{BLUE}🌐 Usando IP del .env: {ip}{NC}")

    if not ip:
        print(f"{RED}❌ No se pudo obtener IP del ESP8266{NC}")
        print(f"   Configura WEBREPL_IP en .env o usa una IP cacheada")
        sys.exit(1)

    print()

    # Obtener password
    password = get_password(config, retry=False)

    # Intentar conectar
    max_retries = 3
    for attempt in range(max_retries):
        if attempt > 0:
            print()
            print(f"{YELLOW}Intento {attempt + 1}/{max_retries}...{NC}")
            password = get_password(config, retry=True)

        client = WebREPLClient(
            ip=ip,
            password=password,
            project_dir=project_dir,
            verbose=True,
            auto_discover=False
        )

        if client.connect():
            # Conexión exitosa
            open_repl_session(client)
            client.close()
            sys.exit(0)
        else:
            # Falló
            if attempt < max_retries - 1:
                print(f"{YELLOW}⚠️  Conexión fallida{NC}")
            else:
                print()
                print(f"{RED}❌ No se pudo conectar después de {max_retries} intentos{NC}")
                print(f"{YELLOW}Verifica:{NC}")
                print(f"  1. ESP8266 está encendido")
                print(f"  2. ESP8266 está conectado a WiFi")
                print(f"  3. WebREPL está activo")
                print(f"  4. IP es correcta: {ip}")
                sys.exit(1)


if __name__ == '__main__':
    main()
