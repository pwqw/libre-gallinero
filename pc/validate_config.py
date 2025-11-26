#!/usr/bin/env python3
"""
Validación de configuración .env
Valida que los valores de configuración sean correctos antes de deploy
"""

import os
import sys
from pathlib import Path

# Importar colores (ajustar path si es necesario)
try:
    from colors import GREEN, YELLOW, BLUE, RED, NC
except ImportError:
    # Si no se puede importar, usar imports relativos
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    from colors import GREEN, YELLOW, BLUE, RED, NC

def load_env():
    """Carga variables desde archivo .env"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    env_path = os.path.join(project_dir, '.env')
    env_example_path = os.path.join(project_dir, '.env.example')
    
    env_vars = {}
    
    # Intentar cargar desde .env
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip().strip('"').strip("'")
    # Si no existe, intentar desde .env.example
    elif os.path.exists(env_example_path):
        with open(env_example_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip().strip('"').strip("'")
    
    return env_vars

def validate_wifi_ssid(ssid):
    """Valida que WIFI_SSID no sea placeholder"""
    if not ssid:
        return False, "WIFI_SSID está vacío"
    if ssid.lower() in ['placeholder', 'your_ssid', 'tu_red_wifi', '']:
        return False, f"WIFI_SSID parece ser un placeholder: {ssid}"
    return True, None

def validate_webrepl_ip(ip):
    """Valida formato de WEBREPL_IP (si está configurada)"""
    if not ip or ip.strip() == '':
        return True, None  # IP vacía es válida (se usará autodiscovery)
    
    try:
        parts = ip.split('.')
        if len(parts) != 4:
            return False, f"WEBREPL_IP formato inválido: {ip} (debe ser IPv4)"
        for part in parts:
            num = int(part)
            if num < 0 or num > 255:
                return False, f"WEBREPL_IP valor inválido: {ip} (cada octeto debe ser 0-255)"
        return True, None
    except ValueError:
        return False, f"WEBREPL_IP formato inválido: {ip} (debe ser números)"

def validate_latitude(lat_str):
    """Valida rango de LATITUDE (-90 a 90)"""
    if not lat_str:
        return True, None  # Opcional
    
    try:
        lat = float(lat_str)
        if lat < -90 or lat > 90:
            return False, f"LATITUDE fuera de rango: {lat} (debe ser -90 a 90)"
        return True, None
    except ValueError:
        return False, f"LATITUDE formato inválido: {lat_str} (debe ser número)"

def validate_longitude(lon_str):
    """Valida rango de LONGITUDE (-180 a 180)"""
    if not lon_str:
        return True, None  # Opcional
    
    try:
        lon = float(lon_str)
        if lon < -180 or lon > 180:
            return False, f"LONGITUDE fuera de rango: {lon} (debe ser -180 a 180)"
        return True, None
    except ValueError:
        return False, f"LONGITUDE formato inválido: {lon_str} (debe ser número)"

def validate_webrepl_password(password):
    """Valida password WebREPL (mínimo 4 caracteres)"""
    if not password:
        return False, "WEBREPL_PASSWORD está vacío"
    if len(password) < 4:
        return False, f"WEBREPL_PASSWORD muy corto: {len(password)} caracteres (mínimo 4)"
    return True, None

def validate(verbose=True):
    """
    Valida configuración .env
    
    Args:
        verbose: Si True, muestra mensajes de validación
        
    Returns:
        tuple: (is_valid: bool, errors: list)
    """
    env = load_env()
    errors = []
    
    if verbose:
        print(f"{BLUE}🔍 Validando configuración...{NC}")
    
    # Validar WIFI_SSID (requerido)
    wifi_ssid = env.get('WIFI_SSID', '')
    is_valid, error = validate_wifi_ssid(wifi_ssid)
    if not is_valid:
        errors.append(error)
        if verbose:
            print(f"{RED}❌ {error}{NC}")
    elif verbose:
        print(f"{GREEN}✅ WIFI_SSID: {wifi_ssid}{NC}")
    
    # Validar WIFI_PASSWORD (requerido)
    wifi_password = env.get('WIFI_PASSWORD', '')
    if not wifi_password:
        errors.append("WIFI_PASSWORD está vacío")
        if verbose:
            print(f"{RED}❌ WIFI_PASSWORD está vacío{NC}")
    elif verbose:
        print(f"{GREEN}✅ WIFI_PASSWORD: {'*' * len(wifi_password)}{NC}")
    
    # Validar WEBREPL_IP (opcional)
    webrepl_ip = env.get('WEBREPL_IP', '')
    is_valid, error = validate_webrepl_ip(webrepl_ip)
    if not is_valid:
        errors.append(error)
        if verbose:
            print(f"{RED}❌ {error}{NC}")
    elif webrepl_ip and verbose:
        print(f"{GREEN}✅ WEBREPL_IP: {webrepl_ip}{NC}")
    elif verbose:
        print(f"{YELLOW}⚠️  WEBREPL_IP no configurada (se usará autodetección){NC}")
    
    # Validar WEBREPL_PASSWORD
    webrepl_password = env.get('WEBREPL_PASSWORD', 'admin')
    is_valid, error = validate_webrepl_password(webrepl_password)
    if not is_valid:
        errors.append(error)
        if verbose:
            print(f"{RED}❌ {error}{NC}")
    elif verbose:
        print(f"{GREEN}✅ WEBREPL_PASSWORD: {'*' * len(webrepl_password)}{NC}")
    
    # Validar LATITUDE (opcional)
    latitude = env.get('LATITUDE', '')
    is_valid, error = validate_latitude(latitude)
    if not is_valid:
        errors.append(error)
        if verbose:
            print(f"{RED}❌ {error}{NC}")
    elif latitude and verbose:
        print(f"{GREEN}✅ LATITUDE: {latitude}{NC}")
    
    # Validar LONGITUDE (opcional)
    longitude = env.get('LONGITUDE', '')
    is_valid, error = validate_longitude(longitude)
    if not is_valid:
        errors.append(error)
        if verbose:
            print(f"{RED}❌ {error}{NC}")
    elif longitude and verbose:
        print(f"{GREEN}✅ LONGITUDE: {longitude}{NC}")
    
    if errors:
        if verbose:
            print(f"\n{RED}❌ Validación falló con {len(errors)} error(es){NC}")
        return False, errors
    else:
        if verbose:
            print(f"\n{GREEN}✅ Configuración válida{NC}")
        return True, []

def main():
    """CLI para validación"""
    is_valid, errors = validate(verbose=True)
    
    if not is_valid:
        print(f"\n{YELLOW}Errores encontrados:{NC}")
        for error in errors:
            print(f"  • {error}")
        print(f"\n{YELLOW}Corrige estos errores en tu archivo .env{NC}")
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == '__main__':
    main()

