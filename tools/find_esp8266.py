#!/usr/bin/env python3
"""
Escaneo de red optimizado para encontrar ESP8266/ESP32 usando nmap.
Especialmente útil en Termux/Android donde los escaneos Python son limitados.

Uso:
    # Escaneo automático (detecta red local):
    python3 tools/find_esp8266.py

    # Escaneo en rango específico:
    python3 tools/find_esp8266.py 192.168.1.0/24

    # Solo probar WebREPL sin nmap:
    python3 tools/find_esp8266.py --test-only 192.168.1.100

Instalación de nmap en Termux:
    pkg install nmap

Estrategia:
    1. Escaneo rápido puerto 8266 con nmap (-p8266 --open)
    2. Detección de vendor Espressif por MAC (si root)
    3. Verificación WebREPL en dispositivos encontrados
    4. Fallback a escaneo Python si nmap no disponible
"""

import sys
import os
import subprocess
import json
import re
from pathlib import Path

# Agregar tools/common al path
script_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(script_dir))

from common.webrepl_client import (
    get_local_ip, get_network_range, test_webrepl_connection,
    load_config, GREEN, YELLOW, BLUE, RED, NC
)


def update_env_ip(project_dir, new_ip, verbose=True):
    """
    Actualiza WEBREPL_IP en .env con la nueva IP encontrada.

    Args:
        project_dir: Directorio del proyecto
        new_ip: Nueva IP a guardar
        verbose: Mostrar mensajes

    Returns:
        bool: True si se actualizó correctamente
    """
    env_path = Path(project_dir) / '.env'

    # Si no existe .env, copiar desde .env.example
    if not env_path.exists():
        env_example = Path(project_dir) / '.env.example'
        if env_example.exists():
            import shutil
            shutil.copy(env_example, env_path)
            if verbose:
                print(f"{BLUE}📄 Creado .env desde .env.example{NC}")
        else:
            if verbose:
                print(f"{RED}❌ No existe .env ni .env.example{NC}")
            return False

    # Leer .env
    with open(env_path, 'r') as f:
        lines = f.readlines()

    # Buscar y actualizar WEBREPL_IP
    updated = False
    for i, line in enumerate(lines):
        if line.strip().startswith('WEBREPL_IP='):
            old_ip = line.split('=', 1)[1].strip().strip('"').strip("'")
            lines[i] = f'WEBREPL_IP={new_ip}\n'
            updated = True
            if verbose:
                print(f"{BLUE}📝 Actualizando .env:{NC}")
                print(f"   Anterior: {old_ip}")
                print(f"   Nueva:    {new_ip}")
            break

    if not updated:
        # Si no existe la línea, agregarla
        lines.append(f'\nWEBREPL_IP={new_ip}\n')
        if verbose:
            print(f"{BLUE}📝 Agregando WEBREPL_IP={new_ip} a .env{NC}")

    # Escribir .env actualizado
    with open(env_path, 'w') as f:
        f.writelines(lines)

    if verbose:
        print(f"{GREEN}✅ .env actualizado{NC}")

    return True


def check_nmap_available():
    """Verifica si nmap está instalado"""
    try:
        result = subprocess.run(['nmap', '--version'],
                              capture_output=True,
                              timeout=5)
        return result.returncode == 0
    except:
        return False


def scan_with_nmap(network_range, port=8266, verbose=True):
    """
    Escanea la red usando nmap para encontrar dispositivos con puerto 8266 abierto.

    Args:
        network_range: Rango de red (ej: "192.168.1.0/24")
        port: Puerto a escanear (default: 8266)
        verbose: Mostrar progreso

    Returns:
        list: Lista de IPs con puerto abierto
    """
    if verbose:
        print(f"{BLUE}🔍 Escaneando red con nmap...{NC}")
        print(f"   Red: {network_range}")
        print(f"   Puerto: {port}")
        print(f"   {YELLOW}(puede tardar 30-60 segundos){NC}\n")

    # Comando nmap optimizado:
    # -p8266: solo puerto WebREPL
    # --open: solo mostrar puertos abiertos
    # -T4: timing agresivo (rápido)
    # -n: no resolver DNS (más rápido)
    # --host-timeout: timeout por host
    cmd = [
        'nmap',
        '-p', str(port),
        '--open',
        '-T4',
        '-n',
        '--host-timeout', '5s',
        network_range
    ]

    # Si tenemos root, agregar detección de vendor MAC
    # (en Termux sin root esto no funciona, pero intentamos)
    if os.geteuid() == 0:
        cmd.insert(1, '-sV')  # Version detection
        cmd.insert(1, '--script')
        cmd.insert(2, 'banner')

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode != 0:
            if verbose:
                print(f"{YELLOW}⚠️  Nmap completó con advertencias{NC}")
            # No fallar por warnings, procesar output de todas formas

        # Parsear output de nmap
        hosts = parse_nmap_output(result.stdout, port, verbose)
        return hosts

    except subprocess.TimeoutExpired:
        if verbose:
            print(f"{RED}❌ Timeout en escaneo nmap (red muy grande){NC}")
        return []
    except Exception as e:
        if verbose:
            print(f"{RED}❌ Error ejecutando nmap: {e}{NC}")
        return []


def parse_nmap_output(nmap_output, port, verbose=True):
    """
    Parsea la salida de nmap para extraer IPs con puerto abierto.

    Args:
        nmap_output: Output de nmap (texto)
        port: Puerto que se buscó
        verbose: Mostrar info detallada

    Returns:
        list: Lista de dicts con info de cada host encontrado
    """
    hosts = []
    current_ip = None
    port_open = False
    mac_vendor = None

    lines = nmap_output.split('\n')

    for line in lines:
        # Detectar IP del host
        match_ip = re.search(r'Nmap scan report for (\d+\.\d+\.\d+\.\d+)', line)
        if match_ip:
            # Guardar host anterior si tenía puerto abierto
            if current_ip and port_open:
                hosts.append({
                    'ip': current_ip,
                    'mac_vendor': mac_vendor,
                    'is_espressif': mac_vendor and 'espressif' in mac_vendor.lower()
                })

            # Nuevo host
            current_ip = match_ip.group(1)
            port_open = False
            mac_vendor = None

        # Detectar puerto abierto
        if current_ip and f'{port}/tcp' in line and 'open' in line:
            port_open = True

        # Detectar MAC vendor (requiere root)
        match_mac = re.search(r'MAC Address: [0-9A-F:]+ \((.+?)\)', line, re.IGNORECASE)
        if match_mac:
            mac_vendor = match_mac.group(1)

    # Guardar último host si corresponde
    if current_ip and port_open:
        hosts.append({
            'ip': current_ip,
            'mac_vendor': mac_vendor,
            'is_espressif': mac_vendor and 'espressif' in mac_vendor.lower()
        })

    if verbose and hosts:
        print(f"{GREEN}✅ Nmap encontró {len(hosts)} dispositivo(s) con puerto {port} abierto:{NC}")
        for h in hosts:
            vendor = f" - {h['mac_vendor']}" if h['mac_vendor'] else ""
            espressif_mark = " 🎯 (Espressif)" if h['is_espressif'] else ""
            print(f"   • {h['ip']}{vendor}{espressif_mark}")
        print()

    return hosts


def test_webrepl_on_hosts(hosts, password, port=8266, verbose=True):
    """
    Prueba conexión WebREPL en cada host encontrado.
    Prioriza hosts Espressif primero.

    Args:
        hosts: Lista de dicts con info de hosts (de parse_nmap_output)
        password: Password WebREPL
        port: Puerto WebREPL
        verbose: Mostrar progreso

    Returns:
        str: IP del primer ESP8266 que responde, o None
    """
    if not hosts:
        return None

    # Ordenar: Espressif primero
    hosts_sorted = sorted(hosts, key=lambda h: not h.get('is_espressif', False))

    if verbose:
        print(f"{BLUE}🔍 Probando WebREPL en {len(hosts_sorted)} dispositivo(s)...{NC}\n")

    for i, host in enumerate(hosts_sorted, 1):
        ip = host['ip']
        vendor_info = f" ({host['mac_vendor']})" if host.get('mac_vendor') else ""

        if verbose:
            print(f"   [{i}/{len(hosts_sorted)}] {ip}{vendor_info}...", end=' ')

        # Timeout más largo para WiFi lento (especialmente Termux)
        if test_webrepl_connection(ip, password, port, timeout=5):
            if verbose:
                print(f"{GREEN}✅ ESP8266 encontrado!{NC}\n")
            return ip
        else:
            if verbose:
                print(f"{YELLOW}✗ Sin WebREPL{NC}")

    if verbose:
        print()

    return None


def fallback_python_scan(password, port=8266, verbose=True):
    """
    Fallback: escaneo Python si nmap no está disponible.
    Usa el scanner existente de webrepl_client.
    """
    if verbose:
        print(f"{YELLOW}⚠️  Nmap no disponible, usando escaneo Python (más lento)...{NC}\n")

    from common.webrepl_client import find_esp8266_in_network

    return find_esp8266_in_network(password, port, verbose)


def main():
    print(f"{BLUE}🐔 Libre-Gallinero - Buscador de ESP8266{NC}\n")

    # Argumentos
    network_range = None
    test_only = False

    if len(sys.argv) > 1:
        if sys.argv[1] == '--test-only':
            if len(sys.argv) < 3:
                print(f"{RED}❌ Uso: {sys.argv[0]} --test-only <ip>{NC}")
                sys.exit(1)
            test_only = True
            test_ip = sys.argv[2]
        else:
            network_range = sys.argv[1]

    # Cargar config
    project_dir = script_dir.parent
    config = load_config(project_dir)
    password = config.get('WEBREPL_PASSWORD', 'admin')
    port = int(config.get('WEBREPL_PORT', 8266))

    # Modo test-only: solo verificar WebREPL en IP específica
    if test_only:
        print(f"{BLUE}🔍 Probando WebREPL en {test_ip}:{port}...{NC}\n")
        if test_webrepl_connection(test_ip, password, port, timeout=5):
            print(f"{GREEN}✅ ESP8266 con WebREPL activo en {test_ip}{NC}")
            print(f"\n💡 Para deployar:")
            print(f"   python3 tools/deploy_wifi.py <app> {test_ip}\n")
            sys.exit(0)
        else:
            print(f"{RED}❌ No se pudo conectar a WebREPL en {test_ip}{NC}")
            print(f"\n🔧 Verifica:")
            print(f"   • ESP8266 encendido y conectado a WiFi")
            print(f"   • WebREPL habilitado (import webrepl_setup)")
            print(f"   • Password correcto en .env (actual: '{password}')\n")
            sys.exit(1)

    # Detectar rango de red si no se especificó
    if not network_range:
        local_ip = get_local_ip()
        if not local_ip:
            print(f"{RED}❌ No se pudo detectar IP local{NC}")
            print(f"\n💡 Especifica el rango manualmente:")
            print(f"   {sys.argv[0]} 192.168.1.0/24\n")
            sys.exit(1)

        network = get_network_range(local_ip)
        network_range = str(network)
        print(f"{BLUE}📡 IP local: {local_ip}{NC}")
        print(f"{BLUE}📡 Rango detectado: {network_range}{NC}\n")

    # Verificar si nmap está disponible
    has_nmap = check_nmap_available()

    if has_nmap:
        print(f"{GREEN}✅ nmap disponible{NC}\n")

        # Escaneo con nmap
        hosts = scan_with_nmap(network_range, port, verbose=True)

        if not hosts:
            print(f"{YELLOW}⚠️  Nmap no encontró dispositivos con puerto {port} abierto{NC}\n")
            print(f"🔧 Verifica:")
            print(f"   • ESP8266 está encendido")
            print(f"   • ESP8266 está en la misma red WiFi")
            print(f"   • WebREPL está habilitado\n")
            sys.exit(1)

        # Probar WebREPL en hosts encontrados
        esp_ip = test_webrepl_on_hosts(hosts, password, port, verbose=True)

        if esp_ip:
            print(f"{GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}")
            print(f"{GREEN}✅ ESP8266 encontrado en: {esp_ip}{NC}")
            print(f"{GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}\n")

            # Actualizar .env automáticamente si hay exactamente 1 dispositivo
            # (comportamiento del bash script original)
            current_ip = config.get('WEBREPL_IP', '')
            num_hosts = len(hosts)
            
            if current_ip != esp_ip:
                if num_hosts == 1:
                    # Un solo dispositivo: actualizar automáticamente
                    print(f"{BLUE}📝 Actualizando .env automáticamente (1 dispositivo encontrado){NC}")
                    print(f"   IP anterior: {current_ip}")
                    print(f"   IP nueva:    {esp_ip}\n")
                    update_env_ip(project_dir, esp_ip, verbose=True)
                    print()
                else:
                    # Múltiples dispositivos: preguntar
                    print(f"{YELLOW}⚠️  Se encontraron {num_hosts} dispositivos con puerto {port} abierto{NC}")
                    print(f"   IP actual en .env: {current_ip}")
                    print(f"   IP encontrada:     {esp_ip}")
                    print(f"{YELLOW}¿Actualizar .env con la nueva IP? (s/N){NC}")
                    try:
                        response = input().strip().lower()
                        if response == 's':
                            print()
                            update_env_ip(project_dir, esp_ip, verbose=True)
                            print()
                    except (EOFError, KeyboardInterrupt):
                        print()

            print(f"💡 Para deployar:")
            print(f"   python3 tools/deploy_wifi.py blink {esp_ip}")
            print(f"   python3 tools/deploy_wifi.py gallinero {esp_ip}")
            print(f"   python3 tools/deploy_wifi.py heladera {esp_ip}\n")
            sys.exit(0)
        else:
            print(f"{RED}❌ Ninguno de los dispositivos encontrados tiene WebREPL activo{NC}\n")
            print(f"🔧 Posibles causas:")
            print(f"   • WebREPL no está configurado (ejecuta: import webrepl_setup)")
            print(f"   • Password incorrecto en .env (actual: '{password}')")
            print(f"   • ESP8266 ejecutando código que bloquea WebREPL\n")
            sys.exit(1)

    else:
        # Fallback a escaneo Python
        print(f"{YELLOW}⚠️  nmap NO disponible{NC}")
        print(f"\n💡 Instalar nmap en Termux:")
        print(f"   pkg install nmap\n")

        esp_ip = fallback_python_scan(password, port, verbose=True)

        if esp_ip:
            print(f"{GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}")
            print(f"{GREEN}✅ ESP8266 encontrado en: {esp_ip}{NC}")
            print(f"{GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}\n")

            # Actualizar .env automáticamente (fallback scan solo encuentra 1)
            current_ip = config.get('WEBREPL_IP', '')
            if current_ip != esp_ip:
                print(f"{BLUE}📝 Actualizando .env automáticamente{NC}")
                print(f"   IP anterior: {current_ip}")
                print(f"   IP nueva:    {esp_ip}\n")
                update_env_ip(project_dir, esp_ip, verbose=True)
                print()

            print(f"💡 Para deployar:")
            print(f"   python3 tools/deploy_wifi.py blink {esp_ip}")
            print(f"   python3 tools/deploy_wifi.py gallinero {esp_ip}\n")
            sys.exit(0)
        else:
            print(f"{RED}❌ No se encontró ESP8266 en la red{NC}\n")
            sys.exit(1)


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
