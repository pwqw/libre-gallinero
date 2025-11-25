#!/usr/bin/env python3
"""
Script para subir archivos a ESP8266 vía WebREPL (WiFi)
Compatible con Windows, Mac y Linux

Uso:
    python3 pc/webrepl_deploy.py
    # O desde el directorio pc/:
    python3 webrepl_deploy.py

Requiere:
    pip install websocket-client python-dotenv

Configuración:
    Copia .env.example a .env y configura tus valores
"""

import sys
import os
import websocket
import time
import socket
import ipaddress
import threading

# Colores
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'

# ========================================
# Cargar configuración desde .env
# ========================================
def load_env():
    """Carga variables desde archivo .env"""
    # Buscar .env en el directorio raíz del proyecto
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    env_path = os.path.join(project_dir, '.env')
    env_example_path = os.path.join(project_dir, '.env.example')
    
    env_vars = {}

    if not os.path.exists(env_path):
        # .env no es obligatorio, podemos buscar automáticamente
        print(f"{YELLOW}⚠️  Archivo .env no encontrado en: {env_path}{NC}")
        print("   Se intentará buscar el ESP8266 automáticamente en la red local")
        
        # Verificar si existe .env.example
        if os.path.exists(env_example_path):
            print("   (Opcional) Copia .env.example a .env para configurar valores:")
            print(f"   cp {env_example_path} {env_path}")
        return {}

    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()

    return env_vars

# Cargar configuración (puede estar vacío si no hay .env)
env = load_env() or {}

WEBREPL_IP = env.get('WEBREPL_IP')
WEBREPL_PASSWORD = env.get('WEBREPL_PASSWORD', 'admin')
WEBREPL_PORT = int(env.get('WEBREPL_PORT', '8266'))
# ========================================

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

def get_local_ip():
    """Obtiene la IP local de la máquina"""
    try:
        # Conectar a un servidor externo para obtener la IP local
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None

def get_network_range(ip):
    """Obtiene el rango de red basado en la IP local"""
    try:
        # Obtener la interfaz de red
        if '/' in ip:
            network = ipaddress.ip_network(ip, strict=False)
        else:
            # Asumir /24 (255.255.255.0)
            ip_obj = ipaddress.IPv4Address(ip)
            network = ipaddress.ip_network(f"{ip_obj}/24", strict=False)
        return network
    except Exception:
        return None

def test_webrepl_connection(ip, password, port=8266, timeout=2):
    """Prueba si un IP tiene WebREPL activo"""
    url = f"ws://{ip}:{port}"
    try:
        ws = websocket.create_connection(url, timeout=timeout)
        time.sleep(0.3)
        
        # Leer prompt de password
        try:
            data = ws.recv(timeout=1)
        except:
            data = ""
        
        # Enviar password
        ws.send(password + '\r\n')
        time.sleep(0.3)
        
        # Verificar login
        try:
            response = ws.recv(timeout=1)
            if "WebREPL connected" in response or ">>>" in response:
                ws.close()
                return True
        except:
            pass
        
        ws.close()
        return False
    except Exception:
        return False

def find_esp8266_in_network(password, port=8266):
    """
    Escanea la red local buscando un ESP8266 con WebREPL activo
    """
    print(f"{BLUE}🔍 Escaneando red local en busca de ESP8266...{NC}")
    
    local_ip = get_local_ip()
    if not local_ip:
        print(f"{RED}❌ No se pudo obtener la IP local{NC}")
        return None
    
    print(f"   IP local: {local_ip}")
    
    network = get_network_range(local_ip)
    if not network:
        print(f"{RED}❌ No se pudo determinar el rango de red{NC}")
        return None
    
    print(f"   Escaneando: {network.network_address} - {network.broadcast_address}")
    print(f"   Probando puerto {port} con password '{password}'...\n")
    
    found_ip = None
    total_hosts = len(list(network.hosts()))
    checked = 0
    
    # Escanear en paralelo usando threads
    lock = threading.Lock()
    
    def check_host(host_ip):
        nonlocal found_ip
        if found_ip:  # Si ya encontramos uno, no seguir
            return
        
        host_str = str(host_ip)
        if test_webrepl_connection(host_str, password, port, timeout=1):
            with lock:
                if not found_ip:
                    found_ip = host_str
                    print(f"\n{GREEN}✅ ESP8266 encontrado en: {host_str}{NC}\n")
    
    # Crear threads para escanear
    threads = []
    for host in network.hosts():
        if found_ip:
            break
        t = threading.Thread(target=check_host, args=(host,))
        t.daemon = True
        t.start()
        threads.append(t)
        checked += 1
        
        # Mostrar progreso cada 10 hosts
        if checked % 10 == 0:
            print(f"   Escaneados {checked}/{total_hosts} hosts...", end='\r')
        
        # Limitar número de threads simultáneos
        if len(threads) >= 50:
            for t in threads:
                t.join(timeout=0.1)
            threads = [t for t in threads if t.is_alive()]
    
    # Esperar a que terminen todos los threads
    for t in threads:
        t.join(timeout=0.5)
    
    if found_ip:
        return found_ip
    else:
        print(f"\n{YELLOW}⚠️  No se encontró ESP8266 en la red local{NC}")
        return None

def find_esp8266_smart(password, port=8266):
    """
    Busca ESP8266 con WebREPL usando estrategia inteligente:
    1. Intenta IP del .env (si existe y no es 192.168.4.1)
    2. Obtiene IP local y escanea ese rango
    3. Usa 192.168.4.1 como fallback hardcodeado (hotspot)
    """
    # 1. Intentar IP del .env si existe y no es 192.168.4.1
    env_ip = WEBREPL_IP
    if env_ip and env_ip != '192.168.4.1':
        print(f"{BLUE}[1/3] Probando IP del .env: {env_ip}{NC}")
        if test_webrepl_connection(env_ip, password, port, timeout=2):
            print(f"{GREEN}✅ ESP8266 encontrado en: {env_ip} (desde .env){NC}\n")
            return env_ip
        else:
            print(f"{YELLOW}⚠️  IP del .env no responde, continuando búsqueda...{NC}\n")
    
    # 2. Obtener IP local y escanear ese rango
    local_ip = get_local_ip()
    if local_ip:
        print(f"{BLUE}[2/3] IP local detectada: {local_ip}{NC}")
        print(f"{BLUE}🔍 Escaneando rango basado en IP local...{NC}\n")
        found_ip = find_esp8266_in_network(password, port)
        if found_ip:
            return found_ip
    else:
        print(f"{YELLOW}⚠️  No se pudo obtener IP local, saltando escaneo de red{NC}\n")
    
    # 3. Fallback: 192.168.4.1 (hotspot)
    print(f"{BLUE}[3/3] Probando fallback: 192.168.4.1 (hotspot){NC}")
    if test_webrepl_connection('192.168.4.1', password, port, timeout=2):
        print(f"{GREEN}✅ ESP8266 encontrado en: 192.168.4.1 (hotspot){NC}\n")
        return '192.168.4.1'
    else:
        print(f"{RED}❌ No se encontró ESP8266 en ninguna ubicación{NC}\n")
        return None

def connect_webrepl(ip=None, password=None, port=None):
    """
    Conecta al WebREPL del ESP8266
    Si no se proporciona IP, usa find_esp8266_smart() para encontrarla
    """
    # Usar valores por defecto si no se proporcionan
    target_password = password or WEBREPL_PASSWORD
    target_port = port or WEBREPL_PORT
    
    # Si se proporciona IP explícitamente, usarla directamente
    if ip:
        target_ip = ip
    else:
        # Usar estrategia inteligente para encontrar IP
        target_ip = find_esp8266_smart(target_password, target_port)
        if not target_ip:
            print(f"{RED}❌ No se pudo encontrar el ESP8266{NC}")
            print("   Opciones:")
            print("   1. Configura WEBREPL_IP en .env")
            print("   2. Asegúrate de que el ESP8266 esté conectado a WiFi")
            print("   3. Verifica que WebREPL esté activo")
            return None
    
    url = f"ws://{target_ip}:{target_port}"
    print(f"{BLUE}🔌 Conectando a {url}...{NC}")

    try:
        ws = websocket.create_connection(url, timeout=10)

        # Esperar prompt de password
        time.sleep(0.5)
        try:
            data = ws.recv(timeout=1)
        except:
            data = ""

        # Enviar password
        ws.send(target_password + '\r\n')
        time.sleep(0.5)

        # Verificar login
        try:
            response = ws.recv(timeout=1)
            if isinstance(response, bytes):
                response = response.decode('utf-8', errors='ignore')
            if "WebREPL connected" in response or ">>>" in response:
                print(f"{GREEN}✅ Conectado a WebREPL{NC}")
                return ws
            else:
                print(f"{RED}❌ Error de autenticación{NC}")
                print(f"   Verifica el password en WEBREPL_PASSWORD")
                ws.close()
                return None
        except:
            # Si no hay respuesta inmediata, asumir que está conectado
            print(f"{GREEN}✅ Conectado a WebREPL{NC}")
            return ws

    except ConnectionRefusedError:
        print(f"{RED}❌ No se pudo conectar a {url}{NC}")
        print("   Verifica:")
        print("   1. ESP8266 está encendido")
        print("   2. ESP8266 está conectado a WiFi")
        print("   3. WebREPL está activo (import webrepl; webrepl.start())")
        return None
    except Exception as e:
        print(f"{RED}❌ Error de conexión: {e}{NC}")
        return None

def main():
    print(f"{BLUE}🐔 Libre-Gallinero WebREPL Deploy (PC){NC}\n")

    # Cambiar al directorio del proyecto
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    os.chdir(project_dir)

    print(f"📂 Directorio proyecto: {project_dir}\n")

    # Conectar a WebREPL (busca automáticamente si no hay IP en .env)
    ws = connect_webrepl()
    if not ws:
        sys.exit(1)

    print(f"\n📤 Iniciando upload de archivos...\n")

    # Contador
    success = 0
    failed = 0

    # Archivos a subir (boot.py y main.py consolidados)
    files_to_upload = [
        ("src/boot.py", "boot.py"),      # Boot minimalista WiFi + WebREPL
        ("src/main.py", "main.py"),      # Lógica principal + hotspot fallback
        ("src/solar.py", "solar.py"),    # Cálculos solares
        ("src/logic.py", "logic.py"),    # Control relays
    ]

    # Subir archivos
    for local_path, remote_name in files_to_upload:
        if send_file(ws, local_path, remote_name):
            success += 1
        else:
            failed += 1
        print()

    # Subir templates si existen
    templates_dir = os.path.join(project_dir, "src/templates")
    if os.path.isdir(templates_dir):
        print(f"{BLUE}📁 Subiendo templates...{NC}\n")
        for filename in os.listdir(templates_dir):
            if filename.endswith('.html'):
                local_path = os.path.join(templates_dir, filename)
                if send_file(ws, local_path, filename):
                    success += 1
                else:
                    failed += 1
                print()

    # Copiar .env si existe en el repositorio
    env_path = os.path.join(project_dir, '.env')
    if os.path.exists(env_path):
        print(f"{BLUE}📄 Copiando .env al ESP8266...{NC}")
        if send_file(ws, env_path, '.env'):
            success += 1
        else:
            failed += 1
        print()

    # Cerrar conexión
    ws.close()

    # Resumen
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"{GREEN}✅ Exitosos: {success}{NC}")
    if failed > 0:
        print(f"{RED}❌ Fallidos: {failed}{NC}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    if failed > 0:
        print(f"{RED}⚠️  Deploy completado con errores{NC}\n")
        sys.exit(1)

    # Preguntar si reiniciar
    print(f"{YELLOW}🔄 ¿Reiniciar ESP8266 para aplicar cambios? (s/N){NC}")
    reply = input().strip().lower()

    if reply in ['s', 'S']:
        print(f"\n🔄 Reiniciando ESP8266...")

        # Reconectar para reiniciar
        ws = connect_webrepl()
        if ws:
            ws.send("import machine; machine.reset()\r\n")
            time.sleep(0.5)
            ws.close()
            print(f"{GREEN}✅ Deploy completo - ESP8266 reiniciado{NC}\n")
        else:
            print(f"{RED}❌ No se pudo conectar para reiniciar{NC}\n")
    else:
        print(f"{GREEN}✅ Deploy completo{NC}")
        print("   Para aplicar cambios desde WebREPL web:")
        print("   import machine; machine.reset()\n")

if __name__ == '__main__':
    main()

