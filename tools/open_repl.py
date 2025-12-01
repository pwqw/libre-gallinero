#!/usr/bin/env python3
"""
Script interactivo para abrir WebREPL del ESP8266.
Usa IP del .env o permite ingresar una IP manual.
"""

import sys
import os
from pathlib import Path

# Agregar tools/common al path
script_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(script_dir))

from common.webrepl_client import WebREPLClient, GREEN, YELLOW, BLUE, RED, NC, load_config


def select_ip_mode():
    """Permite al usuario seleccionar el modo de IP"""
    print(f"{BLUE}🌐 Selecciona el origen de la IP:{NC}")
    print(f"  1. Usar IP del .env")
    print(f"  2. Ingresar IP manualmente")
    print()

    try:
        choice = input(f"{YELLOW}Selección (1-2): {NC}").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)

    if choice == '1':
        return None  # Usar .env
    elif choice == '2':
        try:
            ip = input(f"{YELLOW}Ingresa IP: {NC}").strip()
            return ip
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
            except Exception:
                break
    except Exception:
        pass

    # Loop interactivo
    connection_lost = False
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
                except OSError as e:
                    # Termux puede generar OSError cuando stdin se cierra
                    print()
                    print(f"{YELLOW}⚠️  Error de entrada (Termux): {e}{NC}")
                    print(f"{YELLOW}   Presiona Enter para continuar o Ctrl-C para salir{NC}")
                    import time
                    time.sleep(2)
                    continue

                # Comandos especiales
                if command.strip().lower() in ['exit()', 'exit', 'quit()', 'quit']:
                    print(f"{GREEN}👋 Saliendo del REPL...{NC}")
                    break

                # Enviar comando al ESP8266
                try:
                    client.ws.send(command + '\r\n')
                except (ConnectionResetError, BrokenPipeError) as e:
                    print(f"{RED}❌ Conexión perdida con ESP8266: {e}{NC}")
                    connection_lost = True
                    break
                except Exception as e:
                    print(f"{RED}❌ Error enviando comando: {e}{NC}")
                    connection_lost = True
                    break

                # Recibir y mostrar respuesta
                import time
                time.sleep(0.2)  # Aumentado para Termux/WiFi

                response = ""
                start_time = time.time()
                timeout = 10  # Aumentado de 5 a 10 segundos para redes lentas

                while time.time() - start_time < timeout:
                    try:
                        client.ws.settimeout(1.0)  # Aumentado de 0.5 a 1.0
                        data = client.ws.recv()
                        if isinstance(data, bytes):
                            response += data.decode('utf-8', errors='ignore')
                        else:
                            response += data

                        # Si vemos el prompt, terminamos
                        if '>>>' in response:
                            break
                    except Exception as recv_err:
                        # Timeout o fin de datos
                        if response:
                            break
                        # Solo mostrar error si es algo crítico (no timeout normal)
                        if not isinstance(recv_err, Exception) or 'timed out' not in str(recv_err).lower():
                            # Error inesperado
                            pass
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
                    time.sleep(0.3)
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
                    except Exception:
                        pass
                except Exception as ctrl_c_err:
                    print(f"{RED}❌ Error enviando Ctrl-C: {ctrl_c_err}{NC}")
                continue

    except Exception as e:
        print()
        print(f"{RED}❌ Error crítico en sesión REPL: {e}{NC}")
        import traceback
        traceback.print_exc()
        connection_lost = True

    print()
    print(f"{GREEN}{'━' * 60}{NC}")
    if connection_lost:
        print(f"{YELLOW}⚠️  Sesión REPL terminada (conexión perdida){NC}")
    else:
        print(f"{GREEN}Sesión REPL terminada{NC}")
    print(f"{GREEN}{'━' * 60}{NC}")


def wait_before_exit(error_occurred=False):
    """
    Espera antes de salir para que el usuario pueda leer el mensaje.
    Crítico para Termux shortcuts que se cierran automáticamente.

    Args:
        error_occurred: Si True, muestra mensaje de error y espera más tiempo
    """
    import time

    if error_occurred:
        print()
        print(f"{YELLOW}{'━' * 60}{NC}")
        print(f"{YELLOW}⚠️  OCURRIÓ UN ERROR{NC}")
        print(f"{YELLOW}   Presiona Ctrl-C para salir o espera 30 segundos{NC}")
        print(f"{YELLOW}{'━' * 60}{NC}")
        print()

        try:
            # Esperar 30 segundos o hasta Ctrl-C
            for i in range(30, 0, -1):
                print(f"   Cerrando en {i} segundos...", end='\r')
                sys.stdout.flush()
                time.sleep(1)
            print()
        except KeyboardInterrupt:
            print()
            print(f"{GREEN}👋 Saliendo...{NC}")
    else:
        # Salida normal, solo un pequeño delay
        time.sleep(0.5)


def main():
    error_occurred = False

    try:
        print(f"{BLUE}🐔 Libre-Gallinero WebREPL{NC}\n")

        # Detectar directorio del proyecto
        project_dir = script_dir.parent
        config = load_config(project_dir)

        # Seleccionar IP
        try:
            manual_ip = select_ip_mode()
        except Exception as e:
            print(f"{RED}❌ Error seleccionando IP: {e}{NC}")
            error_occurred = True
            wait_before_exit(error_occurred)
            sys.exit(1)

        print()

        # Obtener IP (prioridad: manual > .env)
        ip = None
        if manual_ip:
            ip = manual_ip
            print(f"{BLUE}🌐 Usando IP manual: {ip}{NC}")
        else:
            # Usar IP del .env
            ip = config.get('WEBREPL_IP')
            if ip:
                print(f"{BLUE}🌐 Usando IP del .env: {ip}{NC}")

        if not ip:
            print(f"{RED}❌ No se pudo obtener IP del ESP8266{NC}")
            print(f"   Configura WEBREPL_IP en .env o ingresa una IP manualmente")
            error_occurred = True
            wait_before_exit(error_occurred)
            sys.exit(1)

        print()

        # Obtener password
        try:
            password = get_password(config, retry=False)
        except Exception as e:
            print(f"{RED}❌ Error obteniendo password: {e}{NC}")
            error_occurred = True
            wait_before_exit(error_occurred)
            sys.exit(1)

        # Intentar conectar
        max_retries = 3
        connected = False

        for attempt in range(max_retries):
            if attempt > 0:
                print()
                print(f"{YELLOW}Intento {attempt + 1}/{max_retries}...{NC}")
                try:
                    password = get_password(config, retry=True)
                except Exception as e:
                    print(f"{RED}❌ Error obteniendo password: {e}{NC}")
                    error_occurred = True
                    break

            try:
                client = WebREPLClient(
                    ip=ip,
                    password=password,
                    project_dir=project_dir,
                    verbose=True,
                    auto_discover=False
                )

                if client.connect():
                    # Conexión exitosa
                    connected = True
                    open_repl_session(client)
                    client.close()
                    break
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
                        error_occurred = True

            except Exception as e:
                print()
                print(f"{RED}❌ Error crítico durante conexión: {e}{NC}")
                import traceback
                traceback.print_exc()
                error_occurred = True
                break

        # Si hubo error, esperar antes de salir
        if error_occurred:
            wait_before_exit(error_occurred)
            sys.exit(1)
        else:
            # Salida exitosa
            wait_before_exit(error_occurred=False)
            sys.exit(0)

    except KeyboardInterrupt:
        print()
        print(f"{GREEN}👋 Cancelado por usuario{NC}")
        sys.exit(0)
    except Exception as e:
        print()
        print(f"{RED}❌ Error inesperado: {e}{NC}")
        import traceback
        traceback.print_exc()
        wait_before_exit(error_occurred=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
