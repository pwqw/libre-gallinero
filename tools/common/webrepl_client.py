#!/usr/bin/env python3
"""
Módulo común para conexión y operaciones WebREPL con ESP8266.
Extrae toda la lógica compartida de los scripts de deployment.
"""

import os
import sys
import websocket
import time
import socket
import ipaddress
import threading
import logging
from pathlib import Path

# Colores ANSI
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'

# Configuración de logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Límite de tamaño de archivo (ESP8266 tiene memoria limitada)
# Según documentación MicroPython 1.19 ESP8266: archivos >16KB pueden causar problemas de memoria
# Usamos 8KB como límite conservador para evitar problemas de memoria
MAX_FILE_SIZE = 8 * 1024  # 8KB - límite conservador para ESP8266


def validate_file_size(file_path, max_size=None):
    """
    Valida que un archivo no exceda el tamaño máximo permitido.
    Función común para evitar duplicación de código (DRY).
    
    Args:
        file_path: Ruta al archivo a validar (Path o str)
        max_size: Tamaño máximo en bytes (default: MAX_FILE_SIZE)
    
    Returns:
        tuple: (is_valid: bool, file_size: int, error_message: str)
    """
    if max_size is None:
        max_size = MAX_FILE_SIZE
    
    file_path = Path(file_path)
    if not file_path.exists():
        return False, 0, f"Archivo no encontrado: {file_path}"
    
    file_size = file_path.stat().st_size
    if file_size > max_size:
        return False, file_size, f"Archivo demasiado grande: {file_size} bytes (máximo: {max_size} bytes)"
    
    return True, file_size, None


def load_config(project_dir=None):
    """
    Carga configuración desde archivo .env.
    
    Args:
        project_dir: Directorio raíz del proyecto. Si es None, se detecta automáticamente.
    
    Returns:
        dict: Variables de configuración, o {} si no existe .env
    """
    if project_dir is None:
        # Detectar directorio del proyecto (buscar src/ o .git)
        current = Path.cwd()
        for path in [current, current.parent]:
            if (path / 'src').exists() or (path / '.git').exists():
                project_dir = path
                break
        if project_dir is None:
            project_dir = current
    
    env_path = Path(project_dir) / '.env'
    env_vars = {}
    
    if not env_path.exists():
        return {}
    
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip().strip('"').strip("'")
    
    return env_vars


def get_local_ip():
    """Obtiene la IP local de la máquina"""
    try:
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
        if '/' in ip:
            network = ipaddress.ip_network(ip, strict=False)
        else:
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
        
        try:
            data = ws.recv(timeout=1)
        except:
            data = ""
        
        ws.send(password + '\r\n')
        time.sleep(0.3)
        
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


def find_esp8266_in_network(password, port=8266, verbose=True, max_hosts=100):
    """
    Escanea la red local buscando un ESP8266 con WebREPL activo.
    
    Args:
        password: Password de WebREPL
        port: Puerto WebREPL (default: 8266)
        verbose: Si True, muestra mensajes de progreso
        max_hosts: Número máximo de hosts a escanear (default: 100)
    
    Returns:
        str: IP del ESP8266 encontrado, o None si no se encuentra
    """
    if verbose:
        print(f"{BLUE}🔍 Escaneando red local en busca de ESP8266...{NC}")
    
    local_ip = get_local_ip()
    if not local_ip:
        if verbose:
            print(f"{RED}❌ No se pudo obtener la IP local{NC}")
        return None
    
    if verbose:
        print(f"   IP local: {local_ip}")
    
    network = get_network_range(local_ip)
    if not network:
        if verbose:
            print(f"{RED}❌ No se pudo determinar el rango de red{NC}")
        return None
    
    if verbose:
        print(f"   Escaneando: {network.network_address} - {network.broadcast_address}")
        print(f"   Probando puerto {port} con password '{password}'...\n")
    
    found_ip = None
    hosts_list = list(network.hosts())
    total_hosts = min(len(hosts_list), max_hosts)  # Limitar número de hosts
    checked = 0
    
    lock = threading.Lock()
    start_time = time.time()
    max_scan_time = 30  # Timeout máximo de 30 segundos para el escaneo
    
    def check_host(host_ip):
        nonlocal found_ip
        if found_ip:
            return
        
        host_str = str(host_ip)
        if test_webrepl_connection(host_str, password, port, timeout=1):
            with lock:
                if not found_ip:
                    found_ip = host_str
                    if verbose:
                        print(f"\n{GREEN}✅ ESP8266 encontrado en: {host_str}{NC}\n")
    
    threads = []
    for host in hosts_list[:max_hosts]:  # Limitar a max_hosts
        if found_ip:
            break
        if time.time() - start_time > max_scan_time:
            if verbose:
                print(f"\n{YELLOW}⚠️  Timeout de escaneo alcanzado ({max_scan_time}s){NC}")
            break
        t = threading.Thread(target=check_host, args=(host,))
        t.daemon = True
        t.start()
        threads.append(t)
        checked += 1
        
        if verbose and checked % 10 == 0:
            print(f"   Escaneados {checked}/{total_hosts} hosts...", end='\r')
        
        if len(threads) >= 50:
            for t in threads:
                t.join(timeout=0.1)
            threads = [t for t in threads if t.is_alive()]
    
    # Esperar a que terminen los threads restantes con timeout
    for t in threads:
        t.join(timeout=0.5)
    
    if not found_ip and verbose:
        print(f"\n{YELLOW}⚠️  No se encontró ESP8266 en la red local{NC}")
    
    return found_ip


def find_esp8266_smart(config_ip=None, password=None, port=8266, verbose=True):
    """
    Busca ESP8266 con WebREPL usando estrategia inteligente:
    1. Intenta IP del .env (si existe y no es 192.168.4.1)
    2. Obtiene IP local y escanea ese rango
    3. Usa 192.168.4.1 como fallback hardcodeado (hotspot)
    
    Args:
        config_ip: IP desde configuración (.env)
        password: Password de WebREPL
        port: Puerto WebREPL (default: 8266)
        verbose: Si True, muestra mensajes informativos
    
    Returns:
        str: IP del ESP8266 encontrado, o None si no se encuentra
    """
    # 1. Intentar IP del .env si existe y no es 192.168.4.1
    if config_ip and config_ip != '192.168.4.1':
        if verbose:
            print(f"{BLUE}[1/3] Probando IP del .env: {config_ip}{NC}")
        if test_webrepl_connection(config_ip, password, port, timeout=2):
            if verbose:
                print(f"{GREEN}✅ ESP8266 encontrado en: {config_ip} (desde .env){NC}\n")
            return config_ip
        else:
            if verbose:
                print(f"{YELLOW}⚠️  IP del .env no responde, continuando búsqueda...{NC}\n")
    
    # 2. Obtener IP local y escanear ese rango
    local_ip = get_local_ip()
    if local_ip:
        if verbose:
            print(f"{BLUE}[2/3] IP local detectada: {local_ip}{NC}")
            print(f"{BLUE}🔍 Escaneando rango basado en IP local...{NC}\n")
        found_ip = find_esp8266_in_network(password, port, verbose)
        if found_ip:
            return found_ip
    else:
        if verbose:
            print(f"{YELLOW}⚠️  No se pudo obtener IP local, saltando escaneo de red{NC}\n")
    
    # 3. Fallback: 192.168.4.1 (hotspot)
    if verbose:
        print(f"{BLUE}[3/3] Probando fallback: 192.168.4.1 (hotspot){NC}")
    if test_webrepl_connection('192.168.4.1', password, port, timeout=2):
        if verbose:
            print(f"{GREEN}✅ ESP8266 encontrado en: 192.168.4.1 (hotspot){NC}\n")
        return '192.168.4.1'
    else:
        if verbose:
            print(f"{RED}❌ No se encontró ESP8266 en ninguna ubicación{NC}\n")
        return None


class WebREPLClient:
    """
    Cliente WebREPL para ESP8266.
    Encapsula conexión, autenticación y operaciones de archivos.
    """
    
    def __init__(self, ip=None, password=None, port=8266, project_dir=None, verbose=True, auto_discover=True):
        """
        Inicializa cliente WebREPL.
        
        Args:
            ip: IP del ESP8266 (si es None, se intenta autodiscovery)
            password: Password de WebREPL
            port: Puerto WebREPL (default: 8266)
            project_dir: Directorio raíz del proyecto
            verbose: Si True, muestra mensajes informativos
            auto_discover: Si True y ip es None, intenta encontrar ESP8266 automáticamente
        """
        self.verbose = verbose
        self.project_dir = project_dir or self._detect_project_dir()
        self.config = load_config(self.project_dir)
        
        self.password = password or self.config.get('WEBREPL_PASSWORD', 'admin')
        self.port = port or int(self.config.get('WEBREPL_PORT', '8266'))
        self.ip = ip or self.config.get('WEBREPL_IP')
        
        self.ws = None
        
        # Si no hay IP y auto_discover está habilitado, buscar automáticamente
        if not self.ip and auto_discover:
            if verbose:
                print(f"{BLUE}🔍 IP no configurada, buscando ESP8266 automáticamente...{NC}\n")
            self.ip = find_esp8266_smart(
                config_ip=self.config.get('WEBREPL_IP'),
                password=self.password,
                port=self.port,
                verbose=verbose
            )
    
    def _detect_project_dir(self):
        """Detecta el directorio raíz del proyecto"""
        current = Path.cwd()
        for path in [current, current.parent]:
            if (path / 'src').exists() or (path / '.git').exists():
                return path
        return current
    
    def connect(self):
        """
        Conecta al WebREPL del ESP8266.
        
        Returns:
            bool: True si la conexión fue exitosa, False en caso contrario
        """
        if not self.ip:
            if self.verbose:
                print(f"{RED}❌ No se pudo encontrar el ESP8266{NC}")
                print("   Opciones:")
                print("   1. Configura WEBREPL_IP en .env")
                print("   2. Asegúrate de que el ESP8266 esté conectado a WiFi")
                print("   3. Verifica que WebREPL esté activo")
            return False
        
        url = f"ws://{self.ip}:{self.port}"
        if self.verbose:
            print(f"{BLUE}🔌 Conectando a {url}...{NC}")
        
        try:
            self.ws = websocket.create_connection(url, timeout=10)
            
            time.sleep(0.5)
            try:
                data = self.ws.recv(timeout=1)
            except:
                data = ""
            
            self.ws.send(self.password + '\r\n')
            time.sleep(0.5)
            
            try:
                response = self.ws.recv(timeout=1)
                if isinstance(response, bytes):
                    response = response.decode('utf-8', errors='ignore')
                if "WebREPL connected" in response or ">>>" in response:
                    if self.verbose:
                        print(f"{GREEN}✅ Conectado a WebREPL{NC}")
                    return True
                else:
                    if self.verbose:
                        print(f"{RED}❌ Error de autenticación{NC}")
                        print(f"   Verifica el password en WEBREPL_PASSWORD")
                    self.close()
                    return False
            except:
                if self.verbose:
                    print(f"{GREEN}✅ Conectado a WebREPL{NC}")
                return True
        
        except ConnectionRefusedError:
            if self.verbose:
                print(f"{RED}❌ No se pudo conectar a {url}{NC}")
                print("   Verifica:")
                print("   1. ESP8266 está encendido")
                print("   2. ESP8266 está conectado a WiFi")
                print("   3. WebREPL está activo (import webrepl; webrepl.start())")
            logger.error(f"No se pudo conectar a {url}: ConnectionRefusedError")
            return False
        except Exception as e:
            if self.verbose:
                print(f"{RED}❌ Error de conexión: {e}{NC}")
            logger.error(f"Error de conexión a {url}: {e}", exc_info=True)
            return False
    
    def send_file(self, local_path, remote_name, max_size=None):
        """
        Sube un archivo al ESP8266 usando WebREPL.
        
        Args:
            local_path: Ruta local del archivo
            remote_name: Nombre del archivo en el ESP8266
            max_size: Tamaño máximo permitido en bytes (default: MAX_FILE_SIZE)
        
        Returns:
            bool: True si el upload fue exitoso, False en caso contrario
        """
        if not self.ws:
            if self.verbose:
                print(f"{RED}❌ No hay conexión WebREPL activa{NC}")
            logger.error("No hay conexión WebREPL activa")
            return False
        
        local_path = Path(local_path)
        if not local_path.exists():
            if self.verbose:
                print(f"{RED}❌ Archivo no encontrado: {local_path}{NC}")
            logger.error(f"Archivo no encontrado: {local_path}")
            return False
        
        # Validar tamaño de archivo
        file_size = local_path.stat().st_size
        max_allowed = max_size or MAX_FILE_SIZE
        
        if file_size > max_allowed:
            error_msg = f"Archivo muy grande: {file_size} bytes (máximo: {max_allowed} bytes)"
            if self.verbose:
                print(f"{RED}❌ {error_msg}{NC}")
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info(f"Subiendo archivo: {local_path} ({file_size} bytes) → {remote_name}")
        
        if self.verbose:
            print(f"{BLUE}📄 {local_path} → {remote_name} ({file_size} bytes){NC}")
        
        try:
            with open(local_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            logger.debug(f"Contenido leído: {len(content)} caracteres")
            
            content_escaped = content.replace('\\', '\\\\').replace("'", "\\'")
            
            # Crear directorios necesarios si el archivo está en una subcarpeta
            remote_path = Path(remote_name)
            dir_creation = ""
            if len(remote_path.parts) > 1:
                # Hay subdirectorios, crear la estructura
                dirs_to_create = []
                current_path = ""
                for part in remote_path.parts[:-1]:  # Todos excepto el nombre del archivo
                    current_path = f"{current_path}/{part}" if current_path else part
                    dirs_to_create.append(current_path)
                
                # Crear código para crear directorios (compatible con MicroPython)
                # Usar OSError con código de error específico para EEXIST
                dir_lines = ["import os"]
                for dir_path in dirs_to_create:
                    dir_lines.append(f"try:")
                    dir_lines.append(f"    os.mkdir('{dir_path}')")
                    dir_lines.append(f"    print(f'📁 Directorio creado: {dir_path}')")
                    dir_lines.append(f"except OSError as e:")
                    dir_lines.append(f"    if e.args[0] != 17:  # 17 = EEXIST (ya existe)")
                    dir_lines.append(f"        raise")
                    dir_lines.append(f"    print(f'📁 Directorio ya existe: {dir_path}')")
                dir_creation = "\n".join(dir_lines) + "\n"
            
            upload_code = f"""{dir_creation}import gc
gc.collect()
with open('{remote_name}', 'w') as f:
    f.write('''{content_escaped}''')
print('✅ Uploaded: {remote_name} ({len(content)} bytes)')
"""
            
            self.ws.send(upload_code + '\r\n')
            time.sleep(0.5)
            
            response = ""
            try:
                start_time = time.time()
                timeout = 10  # Timeout de 10 segundos para recibir respuesta
                while time.time() - start_time < timeout:
                    try:
                        self.ws.settimeout(1)  # Timeout de 1 segundo por recv
                        data = self.ws.recv()
                        if isinstance(data, bytes):
                            response += data.decode('utf-8', errors='ignore')
                        else:
                            response += data
                        
                        if "Uploaded" in response or ">>>" in response:
                            break
                    except websocket.WebSocketTimeoutException:
                        # Continuar intentando hasta el timeout total
                        pass
                    
                    time.sleep(0.1)
            except websocket.WebSocketTimeoutException:
                pass
            
            if "Uploaded" in response or remote_name in response:
                if self.verbose:
                    print(f"{GREEN}   ✅ OK{NC}")
                logger.info(f"Archivo subido exitosamente: {remote_name}")
                return True
            else:
                if self.verbose:
                    print(f"{YELLOW}   ⚠️  Completado (sin confirmación clara){NC}")
                logger.warning(f"Upload completado sin confirmación clara: {remote_name}")
                return True
        
        except ValueError:
            # Re-lanzar ValueError (tamaño de archivo)
            raise
        except Exception as e:
            if self.verbose:
                print(f"{RED}   ❌ Error: {e}{NC}")
            logger.error(f"Error subiendo archivo {local_path}: {e}", exc_info=True)
            return False
    
    def execute(self, command, timeout=2):
        """
        Ejecuta un comando Python en el ESP8266.
        
        Args:
            command: Comando Python a ejecutar
            timeout: Timeout en segundos
        
        Returns:
            str: Respuesta del comando, o "" si hay error
        """
        if not self.ws:
            logger.warning("Intento de ejecutar comando sin conexión WebREPL")
            return ""
        
        logger.debug(f"Ejecutando comando: {command[:50]}...")
        
        try:
            self.ws.send(command + '\r\n')
            time.sleep(0.3)
            
            response = ""
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    self.ws.settimeout(0.5)
                    data = self.ws.recv()
                    if isinstance(data, bytes):
                        response += data.decode('utf-8', errors='ignore')
                    else:
                        response += data
                    
                    if ">>>" in response:
                        break
                except websocket.WebSocketTimeoutException:
                    continue
                except:
                    break
            
            logger.debug(f"Respuesta recibida: {response[:100]}...")
            return response
        except Exception as e:
            if self.verbose:
                print(f"{YELLOW}⚠️  Error ejecutando comando: {e}{NC}")
            logger.error(f"Error ejecutando comando: {e}", exc_info=True)
            return ""
    
    def download_file(self, remote_name, local_path):
        """
        Descarga un archivo del ESP8266 usando WebREPL.
        
        Args:
            remote_name: Nombre del archivo en el ESP8266
            local_path: Ruta local donde guardar el archivo
        
        Returns:
            bool: True si el download fue exitoso, False en caso contrario
        """
        if not self.ws:
            if self.verbose:
                print(f"{RED}❌ No hay conexión WebREPL activa{NC}")
            logger.error("No hay conexión WebREPL activa")
            return False
        
        logger.info(f"Descargando archivo: {remote_name} → {local_path}")
        
        if self.verbose:
            print(f"{BLUE}📥 {remote_name} → {local_path}{NC}")
        
        try:
            # Comando para leer archivo completo
            read_code = f"""
try:
    with open('{remote_name}', 'r') as f:
        content = f.read()
    print('FILE_CONTENT_START')
    print(content, end='')
    print('FILE_CONTENT_END')
except Exception as e:
    print(f'ERROR: {{e}}')
"""
            
            self.ws.send(read_code + '\r\n')
            time.sleep(0.5)
            
            response = ""
            start_time = time.time()
            timeout = 5  # Timeout para descarga
            
            while time.time() - start_time < timeout:
                try:
                    self.ws.settimeout(1)
                    data = self.ws.recv()
                    if isinstance(data, bytes):
                        response += data.decode('utf-8', errors='ignore')
                    else:
                        response += data
                    
                    # Buscar marcadores de inicio y fin
                    if 'FILE_CONTENT_START' in response and 'FILE_CONTENT_END' in response:
                        break
                    
                    if 'ERROR:' in response:
                        error_msg = response.split('ERROR:')[1].split('\n')[0].strip()
                        if self.verbose:
                            print(f"{RED}   ❌ Error: {error_msg}{NC}")
                        logger.error(f"Error descargando archivo: {error_msg}")
                        return False
                    
                except websocket.WebSocketTimeoutException:
                    continue
                except Exception as e:
                    logger.warning(f"Excepción durante descarga: {e}")
                    break
            
            # Extraer contenido del archivo
            if 'FILE_CONTENT_START' in response and 'FILE_CONTENT_END' in response:
                start_idx = response.find('FILE_CONTENT_START') + len('FILE_CONTENT_START')
                end_idx = response.find('FILE_CONTENT_END')
                content = response[start_idx:end_idx].strip()
                
                # Guardar archivo local
                local_path_obj = Path(local_path)
                local_path_obj.parent.mkdir(parents=True, exist_ok=True)
                
                with open(local_path_obj, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                if self.verbose:
                    print(f"{GREEN}   ✅ OK ({len(content)} bytes){NC}")
                logger.info(f"Archivo descargado exitosamente: {local_path} ({len(content)} bytes)")
                return True
            else:
                if self.verbose:
                    print(f"{YELLOW}   ⚠️  No se pudo extraer contenido del archivo{NC}")
                logger.warning(f"No se pudo extraer contenido del archivo: {remote_name}")
                return False
        
        except Exception as e:
            if self.verbose:
                print(f"{RED}   ❌ Error: {e}{NC}")
            logger.error(f"Error descargando archivo {remote_name}: {e}", exc_info=True)
            return False
    
    def close(self):
        """Cierra la conexión WebREPL"""
        if self.ws:
            try:
                self.ws.close()
            except:
                pass
            self.ws = None
    
    def __enter__(self):
        """Context manager enter"""
        if not self.ws:
            self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
        return False

