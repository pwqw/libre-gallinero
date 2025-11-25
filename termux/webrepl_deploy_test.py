#!/usr/bin/env python3
"""
Script para subir test.py a ESP8266 vía WebREPL (WiFi)

Uso:
    python3 webrepl_deploy_test.py

Requiere:
    pip install websocket-client

Configuración:
    Copia .env.example a .env y configura tus valores
"""

import sys
import os
import websocket
import time

# ========================================
# Cargar configuración desde .env
# ========================================
def load_env():
    """Carga variables desde archivo .env"""
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(project_dir, '.env')
    env_example_path = os.path.join(project_dir, '.env.example')
    env_vars = {}

    if not os.path.exists(env_path):
        print(f"⚠️  Archivo .env no encontrado en: {env_path}")
        
        # Verificar si existe .env.example
        if os.path.exists(env_example_path):
            print("   Copia .env.example a .env y configura tus valores:")
            print(f"   cp {env_example_path} {env_path}")
        else:
            print("   Crea el archivo .env con las siguientes variables:")
            print("   WEBREPL_IP=192.168.1.123")
            print("   WEBREPL_PASSWORD=admin")
            print("   WEBREPL_PORT=8266")
            print(f"\n   O crea el archivo manualmente en: {env_path}")
        return None

    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()

    return env_vars

# Cargar configuración
env = load_env()
if not env:
    sys.exit(1)

WEBREPL_IP = env.get('WEBREPL_IP', '192.168.1.123')
WEBREPL_PASSWORD = env.get('WEBREPL_PASSWORD', 'admin')
WEBREPL_PORT = int(env.get('WEBREPL_PORT', '8266'))
# ========================================

# Colores
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'

def send_file(ws, local_path, remote_name):
    """
    Sube un archivo al ESP8266 usando WebREPL
    """
    # Leer archivo local
    if not os.path.exists(local_path):
        print(f"{RED}❌ Archivo no encontrado: {local_path}{NC}")
        return False

    print(f"{BLUE}📄 {local_path} → {remote_name}{NC}")

    try:
        with open(local_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Escapar contenido para Python
        content_escaped = content.replace('\\', '\\\\').replace("'", "\\'")

        # Código para escribir archivo en ESP8266
        upload_code = f"""
with open('{remote_name}', 'w') as f:
    f.write('''{content_escaped}''')
print('✅ Uploaded: {remote_name} ({len(content)} bytes)')
"""

        # Enviar comando
        ws.send(upload_code + '\r\n')
        time.sleep(0.5)

        # Leer respuesta
        response = ""
        try:
            while True:
                data = ws.recv()
                if isinstance(data, bytes):
                    response += data.decode('utf-8', errors='ignore')
                else:
                    response += data

                # Verificar si ya tenemos la confirmación
                if "Uploaded" in response or ">>>" in response:
                    break

                time.sleep(0.1)
        except websocket.WebSocketTimeoutException:
            pass

        if "Uploaded" in response or remote_name in response:
            print(f"{GREEN}   ✅ OK{NC}")
            return True
        else:
            print(f"{YELLOW}   ⚠️  Completado (sin confirmación clara){NC}")
            return True

    except Exception as e:
        print(f"{RED}   ❌ Error: {e}{NC}")
        return False

def connect_webrepl():
    """
    Conecta al WebREPL del ESP8266
    """
    url = f"ws://{WEBREPL_IP}:{WEBREPL_PORT}"
    print(f"{BLUE}🔌 Conectando a {url}...{NC}")

    try:
        ws = websocket.create_connection(url, timeout=10)

        # Esperar prompt de password
        time.sleep(0.5)
        data = ws.recv()

        # Enviar password
        ws.send(WEBREPL_PASSWORD + '\r\n')
        time.sleep(0.5)

        # Verificar login
        response = ws.recv()
        if "WebREPL connected" in response or ">>>" in response:
            print(f"{GREEN}✅ Conectado a WebREPL{NC}")
            return ws
        else:
            print(f"{RED}❌ Error de autenticación{NC}")
            print(f"   Verifica el password en WEBREPL_PASSWORD")
            return None

    except ConnectionRefusedError:
        print(f"{RED}❌ No se pudo conectar a {url}{NC}")
        print("   Verifica:")
        print("   1. ESP8266 está encendido")
        print("   2. ESP8266 está conectado a WiFi")
        print("   3. WebREPL está activo (import webrepl; webrepl.start())")
        print("   4. IP es correcta en WEBREPL_IP")
        return None
    except Exception as e:
        print(f"{RED}❌ Error de conexión: {e}{NC}")
        return None

def main():
    print(f"{BLUE}🐔 Libre-Gallinero WebREPL Deploy Test{NC}\n")

    # Cambiar al directorio del proyecto
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    os.chdir(project_dir)

    print(f"📂 Directorio proyecto: {project_dir}\n")

    # Conectar a WebREPL
    ws = connect_webrepl()
    if not ws:
        sys.exit(1)

    print(f"\n📤 Subiendo test.py...\n")

    # Subir test.py
    if not send_file(ws, "src/test.py", "test.py"):
        print(f"\n{RED}❌ Error al subir test.py{NC}\n")
        ws.close()
        sys.exit(1)

    print()
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"{GREEN}✅ Deploy de prueba completado{NC}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    # Preguntar si ejecutar test.py
    print(f"{YELLOW}▶️  ¿Ejecutar test.py ahora? (s/N){NC}")
    reply = input().strip().lower()

    if reply in ['s', 'S']:
        print(f"\n▶️  Ejecutando test.py...")
        ws.send("exec(open('test.py').read())\r\n")
        time.sleep(1)

        # Leer respuesta
        try:
            response = ws.recv()
            print(response)
        except:
            pass

        print(f"{GREEN}✅ test.py ejecutado{NC}\n")
    else:
        print("\nPara ejecutar test.py desde WebREPL web:")
        print("  exec(open('test.py').read())\n")

    ws.close()

if __name__ == '__main__':
    main()
