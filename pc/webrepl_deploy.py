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

# Ajustar path para imports locales
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Importar colores centralizados
from colors import RED, GREEN, YELLOW, BLUE, NC
from validate_config import validate

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
# Password por defecto: intentar 'Eco1!.' primero (común en este proyecto), luego 'admin'
WEBREPL_PASSWORD = env.get('WEBREPL_PASSWORD', 'Eco1!.')
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

        # Mejorar escaping para manejar triple quotes y caracteres especiales
        content_escaped = (content
            .replace('\\', '\\\\')        # Backslashes primero
            .replace("'''", "\\'\\'\\'")  # Triple quotes
            .replace("'", "\\'"))         # Single quotes

        # Verificar si el contenido tiene secuencias problemáticas
        use_base64 = False
        if "'''" in content or len(content_escaped) > len(content) * 1.5:
            use_base64 = True

        # Código para escribir archivo en ESP8266
        if use_base64:
            # Usar base64 encoding para archivos con contenido problemático
            import base64
            content_b64 = base64.b64encode(content.encode('utf-8')).decode('ascii')
            upload_code = f"""
import ubinascii
with open('{remote_name}', 'wb') as f:
    f.write(ubinascii.a2b_base64('{content_b64}'))
print('✅ Uploaded: {remote_name} ({len(content)} bytes)')
"""
        else:
            # Usar método normal con escaping mejorado
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

        # Check for errors FIRST
        if any(err in response for err in ["Traceback", "Error:", "SyntaxError", "MemoryError"]):
            print(f"{RED}   ❌ Error en upload{NC}")
            return False

        # Require explicit confirmation
        if "Uploaded" in response and remote_name in response:
            print(f"{GREEN}   ✅ OK{NC}")
            return True
        elif ">>>" in response and len(response) > 10:
            print(f"{YELLOW}   ⚠️  Completado (verificar manualmente){NC}")
            return True
        else:
            print(f"{RED}   ❌ Sin confirmación de upload{NC}")
            return False

    except Exception as e:
        print(f"{RED}   ❌ Error: {e}{NC}")
        return False

def send_directory(ws, local_dir, remote_base_dir):
    """
    Sube un directorio completo al ESP8266 usando WebREPL
    """
    if not os.path.isdir(local_dir):
        print(f"{RED}❌ Directorio no encontrado: {local_dir}{NC}")
        return 0, 0
    
    success = 0
    failed = 0
    
    # Crear directorio remoto si no existe
    if remote_base_dir:
        try:
            create_dir_code = f"""
import os
os.makedirs('{remote_base_dir}', exist_ok=True)
print('✅ Directory created: {remote_base_dir}')
"""
            ws.send(create_dir_code + '\r\n')
            time.sleep(0.3)
        except:
            pass
    
    # Recorrer archivos en el directorio
    for root, dirs, files in os.walk(local_dir):
        # Calcular ruta relativa
        rel_path = os.path.relpath(root, local_dir)
        if rel_path == '.':
            remote_dir = remote_base_dir
        else:
            remote_dir = os.path.join(remote_base_dir, rel_path).replace('\\', '/')
        
        # Crear subdirectorio si es necesario
        if remote_dir and remote_dir != '.':
            try:
                create_dir_code = f"""
import os
os.makedirs('{remote_dir}', exist_ok=True)
print('✅ Directory created: {remote_dir}')
"""
                ws.send(create_dir_code + '\r\n')
                time.sleep(0.3)
            except:
                pass
        
        # Subir archivos
        for filename in files:
            if filename.endswith('.py') or filename.endswith('.pyc'):
                local_path = os.path.join(root, filename)
                remote_path = os.path.join(remote_dir, filename).replace('\\', '/')
                if send_file(ws, local_path, remote_path):
                    success += 1
                else:
                    failed += 1
                print()
    
    return success, failed

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

def test_webrepl_connection(ip, password, port=8266, timeout=3):
    """Prueba si un IP tiene WebREPL activo"""
    url = f"ws://{ip}:{port}"
    try:
        # Aumentar timeout de conexión
        ws = websocket.create_connection(url, timeout=timeout)
        time.sleep(0.5)
        
        # Leer prompt de password (puede tardar un poco)
        try:
            ws.settimeout(2)
            data = ws.recv()
            if isinstance(data, bytes):
                data = data.decode('utf-8', errors='ignore')
        except:
            data = ""
        
        # Enviar password
        ws.send(password + '\r\n')
        time.sleep(0.5)
        
        # Verificar login - leer respuesta con más tiempo
        try:
            ws.settimeout(2)
            response = ws.recv()
            if isinstance(response, bytes):
                response = response.decode('utf-8', errors='ignore')
            
            # Verificar múltiples indicadores de éxito
            if any(indicator in response for indicator in ["WebREPL connected", ">>>", "Password:", "WebREPL"]):
                ws.close()
                return True
        except Exception as e:
            # Si no hay respuesta pero la conexión se estableció, puede estar OK
            # WebREPL a veces no envía respuesta inmediata
            pass
        
        ws.close()
        return True  # Si llegamos aquí, la conexión se estableció
    except ConnectionRefusedError:
        return False
    except Exception as e:
        # Otros errores (timeout, etc.) = no disponible
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
        if test_webrepl_connection(host_str, password, port, timeout=2):
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
    2. Obtiene IP local y prueba IPs comunes primero (más rápido)
    3. Escanea rango completo si no encuentra
    4. Usa 192.168.4.1 como fallback hardcodeado (hotspot)
    """
    # 1. Intentar IP del .env si existe y no es 192.168.4.1
    env_ip = WEBREPL_IP
    if env_ip and env_ip != '192.168.4.1':
        print(f"{BLUE}[1/4] Probando IP del .env: {env_ip}{NC}")
        if test_webrepl_connection(env_ip, password, port, timeout=3):
            print(f"{GREEN}✅ ESP8266 encontrado en: {env_ip} (desde .env){NC}\n")
            return env_ip
        else:
            print(f"{YELLOW}⚠️  IP del .env no responde, continuando búsqueda...{NC}\n")
    
    # 2. Obtener IP local y probar IPs comunes primero (más rápido)
    local_ip = get_local_ip()
    if local_ip:
        print(f"{BLUE}[2/4] IP local detectada: {local_ip}{NC}")
        
        # Extraer base de red (ej: 192.168.103.x)
        try:
            ip_parts = local_ip.split('.')
            base_network = '.'.join(ip_parts[:3])
            
            # Probar IPs comunes primero (gateway, .1, .100, .142, etc.)
            common_ips = [
                f"{base_network}.1",      # Gateway común
                f"{base_network}.100",    # IP común
                f"{base_network}.142",     # IP conocida del log
                f"{base_network}.101",
                f"{base_network}.102",
                f"{base_network}.103",
            ]
            
            print(f"{BLUE}🔍 Probando IPs comunes primero...{NC}")
            for test_ip in common_ips:
                if test_ip == local_ip:
                    continue  # Saltar nuestra propia IP
                if test_webrepl_connection(test_ip, password, port, timeout=2):
                    print(f"{GREEN}✅ ESP8266 encontrado en: {test_ip}{NC}\n")
                    return test_ip
            
            # Si no encontramos en IPs comunes, escanear rango completo
            print(f"{BLUE}🔍 IPs comunes no responden, escaneando rango completo...{NC}\n")
            found_ip = find_esp8266_in_network(password, port)
            if found_ip:
                return found_ip
        except Exception as e:
            print(f"{YELLOW}⚠️  Error procesando IP local: {e}{NC}")
            # Fallback a escaneo completo
            print(f"{BLUE}🔍 Escaneando rango completo...{NC}\n")
            found_ip = find_esp8266_in_network(password, port)
            if found_ip:
                return found_ip
    else:
        print(f"{YELLOW}⚠️  No se pudo obtener IP local, saltando escaneo de red{NC}\n")
    
    # 3. Fallback: 192.168.4.1 (hotspot)
    print(f"{BLUE}[3/4] Probando fallback: 192.168.4.1 (hotspot){NC}")
    if test_webrepl_connection('192.168.4.1', password, port, timeout=3):
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

    # Validar configuración antes de continuar
    print(f"{BLUE}Validando configuración...{NC}\n")
    is_valid, errors = validate(verbose=True)
    if not is_valid:
        print(f"\n{YELLOW}⚠️  Configuración tiene errores, pero continuando...{NC}")
        print(f"{YELLOW}   Corrige los errores en .env para evitar problemas{NC}\n")
    else:
        print()

    # Conectar a WebREPL (busca automáticamente si no hay IP en .env)
    ws = connect_webrepl()
    if not ws:
        sys.exit(1)

    print(f"\n📤 Iniciando upload de archivos...\n")

    # Contador
    success = 0
    failed = 0

    # Archivos base a subir
    files_to_upload = [
        ("src/boot.py", "boot.py"),      # Boot minimalista
        ("src/main.py", "main.py"),      # WiFi/Hotspot manager + project loader
    ]

    # Subir archivos base
    for local_path, remote_name in files_to_upload:
        if send_file(ws, local_path, remote_name):
            success += 1
        else:
            failed += 1
        print()

    # Subir directorio gallinero
    gallinero_dir = os.path.join(project_dir, "src/gallinero")
    if os.path.isdir(gallinero_dir):
        print(f"{BLUE}📁 Subiendo gallinero/...{NC}\n")
        s, f = send_directory(ws, gallinero_dir, "gallinero")
        success += s
        failed += f
        print()

    # Subir directorio heladera
    heladera_dir = os.path.join(project_dir, "src/heladera")
    if os.path.isdir(heladera_dir):
        print(f"{BLUE}📁 Subiendo heladera/...{NC}\n")
        s, f = send_directory(ws, heladera_dir, "heladera")
        success += s
        failed += f
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
            ws.send("\x03")  # Ctrl-C to reset REPL state
            time.sleep(0.2)
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

