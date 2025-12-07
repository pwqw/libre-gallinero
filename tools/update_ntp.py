#!/usr/bin/env python3
"""
update_ntp.py - Actualiza la sincronización NTP del ESP8266 vía WebREPL

Uso:
    python3 tools/update_ntp.py              # Usa IP del .env (escrita por el scanner)

Funcionamiento:
    1. Se conecta al ESP8266 vía WebREPL
    2. Obtiene y muestra la hora actual (si está disponible)
    3. Muestra logs históricos
    4. Carga configuración TIMEZONE desde .env
    5. Ejecuta ntp.sync_ntp(tz_offset) en el ESP8266
    6. Muestra el resultado de la sincronización
    7. Obtiene y muestra la hora actualizada
    8. Muestra logs actualizados
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

    # No aceptar argumentos - siempre usar IP del .env
    if len(sys.argv) > 1:
        print(f"{YELLOW}⚠️  Este script no acepta argumentos{NC}")
        print(f"{BLUE}💡 Usa la IP del .env (escrita por el scanner){NC}\n")

    # Detectar directorio del proyecto
    project_dir = script_dir.parent

    # Cargar configuración para obtener TIMEZONE y WEBREPL_IP
    config = load_config(project_dir)
    
    # Verificar que existe WEBREPL_IP en .env
    webrepl_ip = config.get('WEBREPL_IP', '').strip()
    if not webrepl_ip or webrepl_ip == '192.168.4.1':
        print(f"{RED}❌ No hay IP configurada en .env (WEBREPL_IP){NC}")
        print(f"{YELLOW}💡 Ejecuta primero el scanner para encontrar el ESP8266:{NC}")
        print(f"   python3 tools/find_esp8266.py{NC}\n")
        sys.exit(1)
    
    print(f"{BLUE}🌐 IP del .env: {webrepl_ip}{NC}\n")
    
    tz_offset_str = config.get('TIMEZONE', '-3')
    try:
        tz_offset = int(tz_offset_str)
    except:
        tz_offset = -3
        print(f"{YELLOW}⚠️  TIMEZONE inválido en .env, usando default: -3{NC}\n")

    print(f"{BLUE}🌍 Zona horaria: UTC{tz_offset:+d}{NC}\n")

    # Conectar a WebREPL usando IP del .env (sin auto-discover)
    client = WebREPLClient(project_dir=project_dir, verbose=True, auto_discover=False)
    client.ip = webrepl_ip

    if not client.connect():
        print(f"{RED}❌ No se pudo conectar al ESP8266{NC}")
        sys.exit(1)

    print(f"\n{GREEN}✅ Conectado al ESP8266{NC}\n")

    try:
        # Obtener hora actual antes de sincronizar (si está disponible)
        print(f"{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}")
        print(f"{BLUE}🕐 Hora actual (antes de sincronizar){NC}")
        print(f"{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}\n")
        
        try:
            get_time_code = """import time
tm = time.localtime()
if tm[0] > 2000:
    print("Hora local: {:02d}:{:02d}:{:02d} {:02d}/{:02d}/{}".format(tm[3], tm[4], tm[5], tm[2], tm[1], tm[0]))
    print("Timestamp: {}".format(time.time()))
else:
    print("⚠️  Hora no sincronizada (año < 2000)")
"""
            client.ws.send('\x05')
            time.sleep(0.3)
            client.ws.send(get_time_code)
            time.sleep(0.3)
            client.ws.send('\x04')
            time.sleep(1.0)
            
            time_response = ""
            try:
                for _ in range(5):
                    client.ws.settimeout(1.0)
                    data = client.ws.recv()
                    if isinstance(data, bytes):
                        time_response += data.decode('utf-8', errors='ignore')
                    else:
                        time_response += data
                    if ">>>" in time_response:
                        break
            except:
                pass
            
            if time_response:
                lines = time_response.split('\n')
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('>>>') and not line.startswith('...'):
                        if '⚠️' in line:
                            print(f"{YELLOW}{line}{NC}")
                        else:
                            print(f"{CYAN}{line}{NC}")
        except Exception as e:
            print(f"{YELLOW}⚠️  No se pudo obtener hora actual: {e}{NC}")
        
        print()
        
        # Mostrar logs históricos
        print(f"{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}")
        print(f"{BLUE}📜 Logs históricos{NC}")
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
            
            if history_output:
                # Filtrar prompts
                lines = history_output.split('\n')
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('>>>') and not line.startswith('...'):
                        print(line)
            else:
                print(f"{YELLOW}⚠️  No hay logs en buffer{NC}")
        except Exception as e:
            print(f"{YELLOW}⚠️  No se pudieron leer logs: {e}{NC}")
        
        print()
        print(f"{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}")
        print(f"{YELLOW}🕐 Sincronizando NTP...{NC}")
        print(f"{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}\n")
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
        
        print()
        
        # Obtener hora actualizada después de sincronizar
        print(f"{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}")
        print(f"{BLUE}🕐 Hora actualizada (después de sincronizar){NC}")
        print(f"{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}\n")
        
        try:
            # Limpiar buffer
            client.ws.settimeout(0.2)
            try:
                while True:
                    client.ws.recv()
            except:
                pass
            
            get_time_code = """import time
tm = time.localtime()
if tm[0] > 2000:
    print("Hora local: {:02d}:{:02d}:{:02d} {:02d}/{:02d}/{}".format(tm[3], tm[4], tm[5], tm[2], tm[1], tm[0]))
    print("Timestamp: {}".format(time.time()))
else:
    print("⚠️  Hora no sincronizada (año < 2000)")
"""
            client.ws.send('\x05')
            time.sleep(0.3)
            client.ws.send(get_time_code)
            time.sleep(0.3)
            client.ws.send('\x04')
            time.sleep(1.0)
            
            time_response = ""
            try:
                for _ in range(5):
                    client.ws.settimeout(1.0)
                    data = client.ws.recv()
                    if isinstance(data, bytes):
                        time_response += data.decode('utf-8', errors='ignore')
                    else:
                        time_response += data
                    if ">>>" in time_response:
                        break
            except:
                pass
            
            if time_response:
                lines = time_response.split('\n')
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('>>>') and not line.startswith('...'):
                        if '⚠️' in line:
                            print(f"{YELLOW}{line}{NC}")
                        else:
                            print(f"{GREEN}{line}{NC}")
        except Exception as e:
            print(f"{YELLOW}⚠️  No se pudo obtener hora actualizada: {e}{NC}")
        
        print()
        
        # Mostrar logs actualizados
        print(f"{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}")
        print(f"{BLUE}📜 Logs actualizados{NC}")
        print(f"{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}\n")
        
        try:
            # Limpiar buffer
            client.ws.settimeout(0.2)
            try:
                while True:
                    client.ws.recv()
            except:
                pass
            
            # Obtener buffer histórico actualizado
            client.ws.settimeout(5.0)
            client.ws.send("import logger\r\n")
            time.sleep(0.3)
            client.ws.send("print(logger.get())\r\n")
            time.sleep(1.0)
            
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
            
            if history_output:
                # Filtrar prompts
                lines = history_output.split('\n')
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('>>>') and not line.startswith('...'):
                        print(line)
            else:
                print(f"{YELLOW}⚠️  No hay logs en buffer{NC}")
        except Exception as e:
            print(f"{YELLOW}⚠️  No se pudieron leer logs: {e}{NC}")
        
        print()
        print(f"{GREEN}✅ Sincronización NTP completada{NC}")
        
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
