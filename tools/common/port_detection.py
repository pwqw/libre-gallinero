#!/usr/bin/env python3
"""
Utilidades comunes para detección de puertos serie.
Funciones compartidas para setup y deployment de ESP8266.
"""

import sys
import platform
import glob
import subprocess


def detect_os():
    """
    Detecta el sistema operativo.
    
    Returns:
        str: 'macos', 'linux', 'windows', o 'unknown'
    """
    system = platform.system().lower()
    if system == 'darwin':
        return 'macos'
    elif system == 'linux':
        return 'linux'
    elif system == 'windows':
        return 'windows'
    return 'unknown'


def find_serial_ports():
    """
    Encuentra puertos serie disponibles según el sistema operativo.
    
    Returns:
        list: Lista de puertos serie disponibles (ordenados)
    """
    os_type = detect_os()
    ports = []
    
    if os_type == 'macos':
        patterns = [
            '/dev/tty.usbserial-*',
            '/dev/tty.wchusbserial*',
            '/dev/cu.usbserial-*',
            '/dev/cu.wchusbserial*',
        ]
    elif os_type == 'linux':
        patterns = [
            '/dev/ttyUSB*',
            '/dev/ttyACM*',
        ]
    elif os_type == 'windows':
        try:
            import serial.tools.list_ports
            ports_list = serial.tools.list_ports.comports()
            ports = [port.device for port in ports_list]
            return ports
        except ImportError:
            # Intentar instalar pyserial si no está disponible
            try:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyserial'], 
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                import serial.tools.list_ports
                ports_list = serial.tools.list_ports.comports()
                ports = [port.device for port in ports_list]
                return ports
            except Exception:
                return []
    else:
        return []
    
    # Buscar puertos usando glob
    for pattern in patterns:
        found = glob.glob(pattern)
        ports.extend(found)
    
    # Eliminar duplicados y ordenar
    ports = sorted(list(set(ports)))
    return ports


def find_port():
    """
    Detecta el primer puerto serie disponible (compatibilidad con serial_monitor.py).
    
    Returns:
        str: Primer puerto disponible o None si no hay puertos
    """
    ports = find_serial_ports()
    return ports[0] if ports else None

