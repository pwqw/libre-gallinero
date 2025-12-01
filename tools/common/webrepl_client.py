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
import struct
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

# Protocolo binario WebREPL (según webrepl_cli.py oficial)
WEBREPL_REQ_S = "<2sBBQLH64s"  # Formato del request struct
WEBREPL_PUT_FILE = 1  # Opcode para PUT file
WEBREPL_GET_FILE = 2  # Opcode para GET file


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


def test_webrepl_connection(ip, password, port=8266, timeout=5):
    """
    Prueba si un IP tiene WebREPL activo.
    Implementación robusta para WiFi lento (Termux/Android).

    Args:
        ip: IP del dispositivo
        password: Password WebREPL
        port: Puerto WebREPL (default: 8266)
        timeout: Timeout total en segundos (default: 5)

    Returns:
        bool: True si WebREPL responde correctamente
    """
    url = f"ws://{ip}:{port}"
    try:
        # Timeout más largo para WiFi lento (especialmente Termux)
        ws = websocket.create_connection(url, timeout=timeout)

        # Sleep más largo para dar tiempo al ESP8266
        time.sleep(0.5)

        # Intentar leer banner inicial (puede no existir)
        try:
            ws.settimeout(1)
            data = ws.recv()
        except:
            data = ""

        # Enviar password
        ws.send(password + '\r\n')
        time.sleep(0.5)

        # Leer respuesta de autenticación
        try:
            ws.settimeout(2)  # Timeout más largo para la respuesta crítica
            response = ws.recv()
            if isinstance(response, bytes):
                response = response.decode('utf-8', errors='ignore')

            if "WebREPL connected" in response or ">>>" in response:
                ws.close()
                return True
        except Exception as e:
            logger.debug(f"Error leyendo respuesta de {ip}: {e}")
            pass

        ws.close()
        return False
    except ConnectionRefusedError:
        return False
    except Exception as e:
        logger.debug(f"Error conectando a {ip}: {e}")
        return False


def scan_active_hosts(network, port=8266, verbose=True, timeout=0.5):
    """
    Escanea la red buscando hosts con el puerto especificado abierto.
    Usa sockets para detectar hosts activos antes de probar WebREPL.

    Args:
        network: Objeto ipaddress.IPv4Network con el rango a escanear
        port: Puerto a probar (default: 8266)
        verbose: Si True, muestra mensajes de progreso
        timeout: Timeout para cada conexión socket (default: 0.5s)

    Returns:
        list: Lista de IPs con el puerto abierto
    """
    active_hosts = []
    hosts_list = list(network.hosts())
    total_hosts = len(hosts_list)
    checked = 0
    lock = threading.Lock()

    if verbose:
        print(f"{BLUE}🔍 Fase 1: Detectando dispositivos activos en puerto {port}...{NC}")
        print(f"   Escaneando {total_hosts} hosts en {network}")

    def check_port(host_ip):
        nonlocal checked
        host_str = str(host_ip)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            result = sock.connect_ex((host_str, port))
            if result == 0:  # Puerto abierto
                with lock:
                    active_hosts.append(host_str)
                    if verbose:
                        print(f"{GREEN}   ✓ Dispositivo detectado: {host_str}:{port}{NC}")
        except:
            pass
        finally:
            sock.close()
            with lock:
                checked += 1
                if verbose and checked % 20 == 0:
                    print(f"   Progreso: {checked}/{total_hosts} hosts escaneados...", end='\r')

    threads = []
    for host in hosts_list:
        t = threading.Thread(target=check_port, args=(host,))
        t.daemon = True
        t.start()
        threads.append(t)

        # Limitar threads concurrentes para no saturar (especialmente en Termux)
        if len(threads) >= 100:
            for thread in threads:
                thread.join(timeout=2)
            threads = [t for t in threads if t.is_alive()]

    # Esperar a que terminen todos los threads
    for t in threads:
        t.join(timeout=2)

    if verbose:
        print(f"\n{BLUE}   Dispositivos detectados: {len(active_hosts)}{NC}\n")

    return active_hosts


def find_esp8266_in_network(password, port=8266, verbose=True, max_hosts=None):
    """
    Escanea la red local buscando un ESP8266 con WebREPL activo.

    Estrategia mejorada:
    1. Escanea TODA la red detectando hosts activos en el puerto 8266
    2. Prueba WebREPL en cada dispositivo detectado
    3. Retorna el primero que responda correctamente

    Args:
        password: Password de WebREPL
        port: Puerto WebREPL (default: 8266)
        verbose: Si True, muestra mensajes de progreso
        max_hosts: DEPRECATED - se ignora, siempre escanea toda la red

    Returns:
        str: IP del ESP8266 encontrado, o None si no se encuentra
    """
    if verbose:
        print(f"{BLUE}🔍 Escaneando red local en busca de ESP8266/ESP32...{NC}")

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

    # Fase 1: Detectar todos los hosts activos con puerto 8266 abierto
    active_hosts = scan_active_hosts(network, port, verbose)

    if not active_hosts:
        if verbose:
            print(f"{YELLOW}⚠️  No se encontraron dispositivos con puerto {port} abierto{NC}")
        return None

    # Fase 2: Probar WebREPL en cada dispositivo detectado
    if verbose:
        print(f"{BLUE}🔍 Fase 2: Probando WebREPL en {len(active_hosts)} dispositivo(s)...{NC}")

    for i, host_ip in enumerate(active_hosts, 1):
        if verbose:
            print(f"   [{i}/{len(active_hosts)}] Probando {host_ip}...", end=' ')

        # Timeout más largo para WiFi lento (especialmente Termux)
        if test_webrepl_connection(host_ip, password, port, timeout=5):
            if verbose:
                print(f"{GREEN}✅ ESP8266/ESP32 encontrado!{NC}\n")
            return host_ip
        else:
            if verbose:
                print(f"{YELLOW}✗ No es ESP8266/ESP32{NC}")

    if verbose:
        print(f"\n{YELLOW}⚠️  Ninguno de los dispositivos detectados tiene WebREPL activo{NC}")
        print(f"   Verifica que el ESP8266/ESP32 tenga WebREPL habilitado")

    return None


def find_esp8266_smart(config_ip=None, password=None, port=8266, verbose=True, cached_ip=None):
    """
    Busca ESP8266 con WebREPL usando estrategia inteligente:
    0. Intenta IP cacheada (si existe)
    1. Intenta IP del .env (si existe y no es 192.168.4.1)
    2. Obtiene IP local y escanea ese rango
    3. Usa 192.168.4.1 como fallback hardcodeado (hotspot)

    Args:
        config_ip: IP desde configuración (.env)
        password: Password de WebREPL
        port: Puerto WebREPL (default: 8266)
        verbose: Si True, muestra mensajes informativos
        cached_ip: IP cacheada para la app actual

    Returns:
        str: IP del ESP8266 encontrado, o None si no se encuentra
    """
    # 0. Intentar IP cacheada primero (más rápido)
    if cached_ip and cached_ip != '192.168.4.1':
        if verbose:
            print(f"{BLUE}[0/4] Probando IP cacheada: {cached_ip}{NC}")
        if test_webrepl_connection(cached_ip, password, port, timeout=5):
            if verbose:
                print(f"{GREEN}✅ ESP8266 encontrado en: {cached_ip} (desde caché){NC}\n")
            return cached_ip
        else:
            if verbose:
                print(f"{YELLOW}⚠️  IP cacheada no responde, continuando búsqueda...{NC}\n")

    # 1. Intentar IP del .env si existe y no es 192.168.4.1
    if config_ip and config_ip != '192.168.4.1':
        if verbose:
            print(f"{BLUE}[1/4] Probando IP del .env: {config_ip}{NC}")
        if test_webrepl_connection(config_ip, password, port, timeout=5):
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
            print(f"{BLUE}[2/4] IP local detectada: {local_ip}{NC}")
            print(f"{BLUE}🔍 Escaneando rango basado en IP local...{NC}\n")
        found_ip = find_esp8266_in_network(password, port, verbose)
        if found_ip:
            return found_ip
    else:
        if verbose:
            print(f"{YELLOW}⚠️  No se pudo obtener IP local, saltando escaneo de red{NC}\n")

    # 3. Fallback: 192.168.4.1 (hotspot)
    if verbose:
        print(f"{BLUE}[3/4] Probando fallback: 192.168.4.1 (hotspot){NC}")
    if test_webrepl_connection('192.168.4.1', password, port, timeout=5):
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
    
    def connect(self, interrupt_program=True):
        """
        Conecta al WebREPL del ESP8266.
        
        Args:
            interrupt_program: Si True, envía CTRL-C para interrumpir programa corriendo.
                             Si False, conecta sin interrumpir (útil para leer logs).
        
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

                    # IMPORTANTE: Enviar CTRL-C para interrumpir cualquier programa corriendo
                    # Esto es necesario antes de usar el protocolo binario de file transfer
                    # PERO: No interrumpir si solo queremos leer logs
                    if interrupt_program:
                        if self.verbose:
                            print(f"{BLUE}⏸️  Interrumpiendo programa...{NC}")
                        self.ws.send('\x03')  # CTRL-C
                        time.sleep(0.3)
                        # Limpiar buffer de respuesta
                        try:
                            self.ws.recv(timeout=0.5)
                        except:
                            pass

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

                # IMPORTANTE: Enviar CTRL-C para interrumpir cualquier programa corriendo
                # PERO: No interrumpir si solo queremos leer logs
                if interrupt_program:
                    if self.verbose:
                        print(f"{BLUE}⏸️  Interrumpiendo programa...{NC}")
                    self.ws.send('\x03')  # CTRL-C
                    time.sleep(0.3)
                    # Limpiar buffer de respuesta
                    try:
                        self.ws.recv(timeout=0.5)
                    except:
                        pass

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
    
    def _read_webrepl_resp(self):
        """
        Lee respuesta del protocolo binario WebREPL.
        Formato: 4 bytes (2 bytes signature "WB" + 2 bytes status code)

        Basado en webrepl_cli.py oficial de MicroPython.
        Implementación robusta que descarta datos spurious del buffer.

        Returns:
            int: Código de estado (0 = éxito)

        Raises:
            ValueError: Si no se puede leer la respuesta correcta
        """
        # MicroPython 1.19 puede tener datos residuales en el buffer
        # Intentar leer hasta 10 veces para encontrar la signature "WB"
        max_attempts = 10

        for attempt in range(max_attempts):
            try:
                data = self.ws.recv()

                # Convertir a bytes si es string (MicroPython 1.19 inconsistency)
                if isinstance(data, str):
                    data = data.encode('latin1')

                # Si recibimos menos de 4 bytes, seguir intentando
                if len(data) < 4:
                    if self.verbose and attempt < 3:
                        logger.debug(f"Respuesta corta ({len(data)} bytes), reintentando...")
                    continue

                # Buscar signature "WB" en los primeros bytes
                # A veces hay basura al inicio por mezcla de protocolos
                wb_index = data.find(b"WB")

                if wb_index == -1:
                    # No encontramos "WB", pero podría ser texto residual
                    # del REPL - descartar y seguir
                    if self.verbose and attempt < 3:
                        logger.debug(f"Sin signature WB, descartando {len(data)} bytes")
                    continue

                # Asegurar que tenemos 4 bytes desde WB
                if len(data) < wb_index + 4:
                    if self.verbose:
                        logger.debug("WB encontrado pero datos incompletos, esperando más...")
                    continue

                # Extraer signature y code
                sig, code = struct.unpack("<2sH", data[wb_index:wb_index+4])

                if sig == b"WB":
                    logger.debug(f"Respuesta WebREPL OK: code={code}")
                    return code

            except websocket.WebSocketTimeoutException:
                if self.verbose and attempt < 3:
                    logger.debug(f"Timeout en intento {attempt+1}/{max_attempts}")
                continue
            except struct.error as e:
                logger.warning(f"Error struct.unpack: {e}, reintentando...")
                continue
            except Exception as e:
                logger.warning(f"Error leyendo respuesta (intento {attempt+1}): {e}")
                if attempt >= max_attempts - 1:
                    raise
                continue

        # Si llegamos aquí, no pudimos leer una respuesta válida
        raise ValueError(f"No se pudo leer respuesta WebREPL válida después de {max_attempts} intentos")

    def _clean_buffer_before_binary_transfer(self):
        """
        Limpia el buffer WebSocket antes de iniciar transferencia binaria.

        CRÍTICO para MicroPython 1.19: Después de usar comandos de texto (execute),
        pueden quedar datos residuales en el buffer que interfieren con el protocolo
        binario. Esta función los descarta.

        Basado en comportamiento observado y documentación oficial de WebREPL.
        """
        try:
            # Configurar timeout corto para lectura rápida
            old_timeout = self.ws.gettimeout()
            self.ws.settimeout(0.1)

            # Leer y descartar hasta 10 mensajes residuales
            for _ in range(10):
                try:
                    data = self.ws.recv()
                    logger.debug(f"Descartando {len(data)} bytes del buffer: {data[:50]}")
                except websocket.WebSocketTimeoutException:
                    # Buffer limpio, perfecto
                    break
                except:
                    break

            # Restaurar timeout
            self.ws.settimeout(old_timeout)

        except Exception as e:
            logger.warning(f"Error limpiando buffer: {e}")

    def _create_directory_structure(self, remote_name):
        """
        DEPRECADO - WebREPL crea directorios automáticamente.

        El protocolo binario WebREPL crea los directorios necesarios
        automáticamente cuando el filename contiene "/".

        NO usar comandos de texto (execute) aquí porque interfiere
        con el protocolo binario y causa "Respuesta muy corta".

        Args:
            remote_name: Nombre del archivo remoto (ej: "gallinero/app.py")

        Returns:
            bool: True (siempre, los directorios se crean automáticamente)
        """
        # NO HACER NADA - WebREPL lo maneja automáticamente
        return True

    def _ensure_connection(self):
        """
        Verifica que la conexión WebSocket esté activa.
        Si está caída, intenta reconectar.

        Returns:
            bool: True si hay conexión activa
        """
        if not self.ws:
            return False

        try:
            # Ping para verificar que la conexión está viva
            self.ws.ping()
            return True
        except:
            # Conexión caída, intentar reconectar
            if self.verbose:
                print(f"{YELLOW}   ⚠️  Conexión perdida, reconectando...{NC}")
            logger.warning("Conexión WebREPL perdida, intentando reconectar")

            self.close()
            time.sleep(2)
            return self.connect()

    def send_file(self, local_path, remote_name, max_size=None):
        """
        Sube un archivo al ESP8266 usando protocolo binario WebREPL.
        Implementación basada en webrepl_cli.py oficial de MicroPython.

        Args:
            local_path: Ruta local del archivo
            remote_name: Nombre del archivo en el ESP8266
            max_size: Tamaño máximo permitido en bytes (default: MAX_FILE_SIZE)

        Returns:
            bool: True si el upload fue exitoso, False en caso contrario
        """
        # Verificar conexión antes de cada archivo
        if not self._ensure_connection():
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

        logger.info(f"Subiendo archivo (protocolo binario): {local_path} ({file_size} bytes) → {remote_name}")

        if self.verbose:
            print(f"{BLUE}📄 {local_path.name} → {remote_name} ({file_size} bytes){NC}")

        try:
            # Preparar nombre de archivo remoto (sin sandbox prefix)
            dest_fname = remote_name.encode("utf-8")

            # Construir request binario según protocolo WebREPL
            # WEBREPL_REQ_S = "<2sBBQLH64s"
            # - 2s: signature "WA"
            # - B: opcode (1 = PUT_FILE)
            # - B: reserved
            # - Q: reserved (8 bytes)
            # - L: file size (4 bytes)
            # - H: filename length (2 bytes)
            # - 64s: filename (max 64 bytes)
            rec = struct.pack(
                WEBREPL_REQ_S,
                b"WA",                    # Signature
                WEBREPL_PUT_FILE,         # Opcode
                0,                        # Reserved
                0,                        # Reserved
                file_size,                # File size
                len(dest_fname),          # Filename length
                dest_fname                # Filename
            )

            # CRÍTICO: Limpiar buffer antes de protocolo binario
            # MicroPython 1.19 tiene problemas si hay datos residuales del REPL
            self._clean_buffer_before_binary_transfer()

            # Enviar request en dos partes (como hace webrepl_cli.py)
            # Usar timeout más largo para WiFi lento
            old_timeout = self.ws.gettimeout()
            self.ws.settimeout(10)  # 10 segundos para operaciones binarias

            try:
                # webrepl_cli.py oficial envía todo de una vez
                # Según código oficial: ws.write(rec)
                self.ws.send(rec, opcode=websocket.ABNF.OPCODE_BINARY)
            except (BrokenPipeError, ConnectionResetError) as e:
                # Conexión perdida durante envío de header
                if self.verbose:
                    print(f"{RED}   ❌ Conexión perdida durante header: {e}{NC}")
                logger.error(f"Conexión perdida al enviar header para {remote_name}: {e}")
                self.ws.settimeout(old_timeout)
                return False

            # Leer respuesta de confirmación
            try:
                time.sleep(0.5)  # Dar tiempo al ESP8266 a procesar
                resp_code = self._read_webrepl_resp()
                if resp_code != 0:
                    if self.verbose:
                        print(f"{RED}   ❌ ESP8266 rechazó request (code: {resp_code}){NC}")
                    logger.error(f"ESP8266 rechazó request para {remote_name}: code {resp_code}")
                    self.ws.settimeout(old_timeout)
                    return False
            except Exception as e:
                if self.verbose:
                    print(f"{RED}   ❌ Error leyendo respuesta: {e}{NC}")
                logger.error(f"Error leyendo respuesta WebREPL: {e}")
                self.ws.settimeout(old_timeout)
                return False

            # Enviar contenido del archivo en chunks de 1024 bytes
            bytes_sent = 0
            with open(local_path, "rb") as f:
                while True:
                    chunk = f.read(1024)
                    if not chunk:
                        break
                    self.ws.send(chunk, opcode=websocket.ABNF.OPCODE_BINARY)
                    bytes_sent += len(chunk)

                    if self.verbose and bytes_sent % 4096 == 0:
                        print(f"{BLUE}   Enviando: {bytes_sent}/{file_size} bytes\r{NC}", end='', flush=True)

            if self.verbose and bytes_sent > 0:
                print()  # Nueva línea después del progreso

            # Leer respuesta final de confirmación
            try:
                time.sleep(0.5)  # Dar tiempo al ESP8266 a escribir el archivo
                resp_code = self._read_webrepl_resp()
                if resp_code != 0:
                    if self.verbose:
                        print(f"{RED}   ❌ Upload falló (code: {resp_code}){NC}")
                    logger.error(f"Upload falló para {remote_name}: code {resp_code}")
                    self.ws.settimeout(old_timeout)
                    return False
            except Exception as e:
                if self.verbose:
                    print(f"{RED}   ❌ Error en confirmación final: {e}{NC}")
                logger.error(f"Error en confirmación final: {e}")
                self.ws.settimeout(old_timeout)
                return False

            # Restaurar timeout original
            self.ws.settimeout(old_timeout)

            if self.verbose:
                print(f"{GREEN}   ✅ OK ({bytes_sent} bytes){NC}")
            logger.info(f"Archivo subido exitosamente: {remote_name} ({bytes_sent} bytes)")
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

                    # Exit on completion or error (early exit optimization)
                    if ">>>" in response:
                        break
                    if any(err in response for err in ["Traceback", "Error:", "SyntaxError"]):
                        logger.warning(f"Error detectado en respuesta: {response[:200]}")
                        break  # Exit early on error

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
    
    def reset(self):
        """
        Reinicia el ESP8266 usando machine.reset() vía WebREPL.
        
        Según documentación oficial MicroPython 1.19:
        - machine.reset() realiza un hard reset completo del dispositivo
        - Equivalente a presionar el botón RESET físicamente
        - Reinicia todos los periféricos de hardware
        
        El método:
        1. Envía Ctrl-C para interrumpir el programa actual
        2. Importa el módulo machine
        3. Ejecuta machine.reset() que reinicia inmediatamente el dispositivo
        
        Nota: No espera respuesta porque el dispositivo se reinicia inmediatamente.
        La conexión WebREPL se perderá después de ejecutar este método.
        
        Returns:
            bool: True si el comando se envió exitosamente, False en caso de error
        """
        if not self.ws:
            if self.verbose:
                print(f"{RED}❌ No hay conexión WebREPL activa{NC}")
            logger.warning("Intento de reset sin conexión WebREPL")
            return False
        
        logger.info("Reiniciando ESP8266 con machine.reset()")
        
        try:
            # Paso 1: Interrumpir programa actual con Ctrl-C
            self.ws.send("\x03")  # Ctrl-C
            time.sleep(0.3)
            
            # Paso 2: Importar módulo machine
            self.ws.send("import machine\r\n")
            time.sleep(0.2)
            
            # Paso 3: Ejecutar reset (el dispositivo se reinicia inmediatamente)
            self.ws.send("machine.reset()\r\n")
            time.sleep(0.5)  # Dar tiempo para que el comando se envíe
            
            logger.info("Comando machine.reset() enviado exitosamente")
            return True
            
        except Exception as e:
            if self.verbose:
                print(f"{YELLOW}⚠️  Error enviando comando de reset: {e}{NC}")
            logger.error(f"Error enviando reset: {e}", exc_info=True)
            return False
    
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

