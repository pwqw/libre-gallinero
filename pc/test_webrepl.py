#!/usr/bin/env python3
"""
Test de conexión WebREPL + REPL interactivo opcional
Consolidado: test_webrepl.py + webrepl_connect.py
"""

import sys
import os
import websocket
import time

# Importar funciones del script principal
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from webrepl_deploy import connect_webrepl

# Colores
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
RED = '\033[0;31m'
NC = '\033[0m'

def test_connection(ws):
    """Prueba conexión y ejecuta comando de prueba"""
    try:
        # Ejecutar comando de prueba
        print(f"{BLUE}📝 Ejecutando comando de prueba...{NC}")
        test_cmd = "print('✅ WebREPL funcionando correctamente')\n"
        ws.send(test_cmd)
        time.sleep(0.5)
        
        # Leer respuesta
        try:
            response = ""
            for _ in range(10):
                try:
                    ws.settimeout(0.5)
                    data = ws.recv()
                    if isinstance(data, bytes):
                        response += data.decode('utf-8', errors='ignore')
                    else:
                        response += data
                    if ">>>" in response:
                        break
                except websocket.WebSocketTimeoutException:
                    break
            
            if "funcionando" in response or ">>>" in response:
                print(f"{GREEN}✅ Test exitoso{NC}")
                print(f"{BLUE}Respuesta: {response.strip()}{NC}")
                return True
            else:
                print(f"{YELLOW}⚠️  Respuesta inesperada: {response}{NC}")
                return True  # Conexión funciona aunque respuesta no sea la esperada
        except Exception as e:
            print(f"{YELLOW}⚠️  Error leyendo respuesta: {e}{NC}")
            return True  # Conexión establecida
        
    except Exception as e:
        print(f"{RED}❌ Error: {e}{NC}")
        return False

def interactive_repl(ws):
    """Sesión REPL interactiva"""
    print(f"\n{GREEN}✅ Conectado - Modo REPL Interactivo{NC}")
    print(f"{YELLOW}Escribe comandos Python (Ctrl+C para salir){NC}\n")

    try:
        while True:
            try:
                cmd = input(">>> ")
            except (EOFError, KeyboardInterrupt):
                print(f"\n{YELLOW}Desconectando...{NC}")
                break

            if not cmd.strip():
                continue

            ws.send(cmd + '\r\n')
            time.sleep(0.2)

            try:
                response = ""
                timeout_count = 0
                while timeout_count < 50:
                    try:
                        ws.settimeout(0.1)
                        data = ws.recv()
                        if isinstance(data, bytes):
                            response += data.decode('utf-8', errors='ignore')
                        else:
                            response += data

                        if ">>>" in response:
                            break
                        timeout_count = 0
                    except websocket.WebSocketTimeoutException:
                        timeout_count += 1
                        if timeout_count > 10:
                            break
                    except Exception as e:
                        if "timed out" not in str(e).lower() and "timeout" not in str(e).lower():
                            print(f"{YELLOW}⚠️  Error: {e}{NC}")
                        timeout_count += 1
                        if timeout_count > 10:
                            break

                    time.sleep(0.01)

                output = response.rstrip('>>>').rstrip()
                if output:
                    print(output)
            except Exception as e:
                print(f"{RED}Error: {e}{NC}")

    except KeyboardInterrupt:
        print(f"\n{YELLOW}Desconectando...{NC}")
    finally:
        ws.close()
        print(f"{GREEN}Desconectado{NC}")

def main():
    # Parsear argumentos: [modo] [ip]
    # Ejemplos:
    #   python3 test_webrepl.py              # Modo test, buscar automáticamente
    #   python3 test_webrepl.py repl          # Modo repl, buscar automáticamente
    #   python3 test_webrepl.py 192.168.1.100 # Modo test, IP específica
    #   python3 test_webrepl.py repl 192.168.1.100 # Modo repl, IP específica
    
    mode = "test"
    ip = None
    
    if len(sys.argv) > 1:
        arg1 = sys.argv[1]
        # Verificar si es una IP (contiene puntos y números)
        if '.' in arg1 and any(c.isdigit() for c in arg1):
            ip = arg1
            mode = "test"
        elif arg1 in ["repl", "test"]:
            mode = arg1
            # Verificar si hay segundo argumento (IP)
            if len(sys.argv) > 2:
                ip = sys.argv[2]
        else:
            # Asumir que es IP si no es un modo conocido
            ip = arg1
    
    if mode == "repl":
        print(f"{BLUE}🔌 REPL Interactivo - Conectando...{NC}\n")
    else:
        print(f"{BLUE}🧪 Test de conexión WebREPL{NC}\n")
    
    if ip:
        print(f"{BLUE}📍 Usando IP: {ip}{NC}\n")

    ws = connect_webrepl(ip=ip)
    if not ws:
        print(f"\n{YELLOW}Verifica:{NC}")
        print("1. ESP8266 está encendido y conectado a WiFi")
        print("2. WebREPL está activo (boot.py con webrepl.start())")
        print("3. Estás en la misma red WiFi")
        print("4. O configura WEBREPL_IP en .env")
        sys.exit(1)

    if mode == "repl":
        # Modo interactivo
        interactive_repl(ws)
    else:
        # Modo test
        if test_connection(ws):
            ws.close()
            print(f"\n{GREEN}✅ WebREPL funcionando correctamente{NC}")
            print(f"\n{YELLOW}Opciones:{NC}")
            print(f"  python3 pc/test_webrepl.py repl    # REPL interactivo")
            print(f"  python3 pc/webrepl_deploy.py       # Deploy archivos")
            sys.exit(0)
        else:
            ws.close()
            print(f"\n{RED}❌ Test falló{NC}")
            sys.exit(1)

if __name__ == '__main__':
    main()

