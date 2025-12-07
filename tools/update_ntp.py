#!/usr/bin/env python3
"""
update_ntp.py - Actualiza la sincronización NTP del ESP8266 vía WebREPL

Uso:
    python3 tools/update_ntp.py              # Usa IP del .env
    python3 tools/update_ntp.py 192.168.1.50  # IP específica
    python3 tools/update_ntp.py heladera      # App específica (opcional)

Funcionamiento:
    1. Se conecta al ESP8266 vía WebREPL
    2. Carga configuración TIMEZONE desde .env
    3. Ejecuta ntp.sync_ntp(tz_offset) en el ESP8266
    4. Muestra el resultado de la sincronización
"""

import sys
import time
import websocket
import logging
from pathlib import Path

# Agregar directorio de herramientas al path
script_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(script_dir / 'common'))

from webrepl_client import WebREPLClient, RED, GREEN, YELLOW, BLUE, CYAN, NC, load_config

# Configurar logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def main():
    print(f"{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}")
    print(f"{CYAN}🕐 Actualizar NTP{NC}")
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

    # Cargar configuración para obtener TIMEZONE
    config = load_config(project_dir)
    tz_offset_str = config.get('TIMEZONE', '-3')
    try:
        tz_offset = int(tz_offset_str)
    except:
        tz_offset = -3
        print(f"{YELLOW}⚠️  TIMEZONE inválido en .env, usando default: -3{NC}\n")

    print(f"{BLUE}🌍 Zona horaria: UTC{tz_offset:+d}{NC}\n")

    # Conectar a WebREPL (usa .env o IP manual)
    auto_discover = not bool(ip_arg)
    client = WebREPLClient(project_dir=project_dir, verbose=True, auto_discover=auto_discover)

    # Configurar IP si se especificó manualmente
    if ip_arg:
        client.ip = ip_arg

    if not client.connect():
        print(f"{RED}❌ No se pudo conectar al ESP8266{NC}")
        sys.exit(1)

    print(f"\n{GREEN}✅ Conectado al ESP8266{NC}")
    print(f"{YELLOW}🕐 Sincronizando NTP...{NC}\n")

    try:
        # Ejecutar sincronización NTP en el ESP8266 usando paste mode
        # MicroPython 1.19 requiere paste mode (Ctrl+E ... código ... Ctrl+D) para código multilínea
        # Importar módulos necesarios y ejecutar sync_ntp
        ntp_code = f"""import ntp
import config
cfg = config.load_config()
tz_str = cfg.get('TIMEZONE', '{tz_offset}')
try:
    tz_offset = int(tz_str)
except:
    tz_offset = {tz_offset}
result = ntp.sync_ntp(tz_offset=tz_offset)
if result[0]:
    print("✅ NTP sincronizado exitosamente")
    print("Timestamp UTC: " + str(result[1]))
else:
    print("❌ NTP falló después de 5 intentos")
"""
        
        # Usar paste mode para código multilínea (compatible MicroPython 1.19)
        # MicroPython 1.19 WebREPL requiere paste mode (Ctrl+E ... código ... Ctrl+D) para código multilínea
        # Esto evita problemas con auto-indent y asegura ejecución correcta
        if not client.ws:
            print(f"{RED}❌ No hay conexión WebREPL activa{NC}")
            sys.exit(1)
        
        if client.verbose:
            print(f"{BLUE}📋 Ejecutando código en paste mode (MicroPython 1.19)...{NC}")
        
        try:
            # Entrar en paste mode (Ctrl+E = 0x05)
            client.ws.send('\x05')
            time.sleep(0.3)  # Dar tiempo al REPL para entrar en paste mode
            
            # Enviar código completo (el string ya tiene \n implícitos)
            # Paste mode acepta el código tal cual, con saltos de línea normales
            client.ws.send(ntp_code)
            time.sleep(0.3)
            
            # Ejecutar código (Ctrl+D = 0x04)
            client.ws.send('\x04')
            time.sleep(0.5)  # Dar tiempo para que comience la ejecución
            
            # Leer respuesta con timeout más largo (NTP puede tardar hasta 10s)
            response = ""
            start_time = time.time()
            timeout = 15
            while time.time() - start_time < timeout:
                try:
                    client.ws.settimeout(1.0)
                    data = client.ws.recv()
                    if isinstance(data, bytes):
                        response += data.decode('utf-8', errors='ignore')
                    else:
                        response += data
                    
                    # Exit on completion (prompt de vuelta) or error
                    if ">>>" in response:
                        break
                    if any(err in response for err in ["Traceback", "Error:", "SyntaxError"]):
                        if client.verbose:
                            logger.warning(f"Error detectado en respuesta: {response[:200]}")
                        break
                except websocket.WebSocketTimeoutException:
                    # Timeout es normal, continuar esperando
                    continue
                except Exception as e:
                    logger.debug(f"Excepción durante lectura: {e}")
                    break
        except Exception as e:
            print(f"{RED}❌ Error ejecutando código en paste mode: {e}{NC}")
            raise
        
        # Mostrar respuesta
        if response:
            # Filtrar prompts de MicroPython y mostrar solo el contenido relevante
            lines = response.split('\n')
            for line in lines:
                line = line.strip()
                # Filtrar prompts y líneas vacías
                if line and not line.startswith('>>>') and not line.startswith('...'):
                    # Colorear según el contenido
                    if '✅' in line or 'OK' in line or 'exitosamente' in line:
                        print(f"{GREEN}{line}{NC}")
                    elif '❌' in line or 'FAIL' in line or 'falló' in line:
                        print(f"{RED}{line}{NC}")
                    elif 'NTP' in line or 'Timestamp' in line:
                        print(f"{CYAN}{line}{NC}")
                    else:
                        print(line)
        
        print(f"\n{GREEN}✅ Comando NTP ejecutado{NC}")
        
    except Exception as e:
        print(f"{RED}❌ Error durante sincronización NTP: {e}{NC}")
        import traceback
        traceback.print_exc()
        client.close()
        sys.exit(1)
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
