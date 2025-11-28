#!/usr/bin/env python3
"""
Sistema de caché de IPs por app para acelerar el descubrimiento.
Guarda la última IP exitosa de cada app (blink, gallinero, heladera).
"""

import os
import time
from pathlib import Path

# Colores ANSI
YELLOW = '\033[1;33m'
GREEN = '\033[0;32m'
BLUE = '\033[0;34m'
NC = '\033[0m'


def get_cache_dir():
    """Obtiene el directorio de caché (compatible con Termux y PC)"""
    # En Termux: $HOME/.cache/libre-gallinero
    # En PC: $HOME/.cache/libre-gallinero
    home = Path.home()
    cache_dir = home / '.cache' / 'libre-gallinero'
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_cached_ip(app_name, verbose=True):
    """
    Obtiene la IP cacheada para una app específica.

    Args:
        app_name: Nombre de la app (blink, gallinero, heladera)
        verbose: Si True, muestra mensajes informativos

    Returns:
        str: IP cacheada, o None si no existe o expiró
    """
    cache_file = get_cache_dir() / f"ip_{app_name}.txt"

    if not cache_file.exists():
        return None

    try:
        with open(cache_file, 'r') as f:
            lines = f.read().strip().split('\n')
            if len(lines) < 2:
                return None

            ip = lines[0].strip()
            timestamp = float(lines[1].strip())

        # Cache válido por 7 días (604800 segundos)
        cache_age = time.time() - timestamp
        if cache_age > 604800:
            if verbose:
                print(f"{YELLOW}⏰ Caché de IP para '{app_name}' expirado (edad: {cache_age/86400:.1f} días){NC}")
            return None

        if verbose:
            print(f"{GREEN}📋 IP cacheada para '{app_name}': {ip} (edad: {cache_age/3600:.1f}h){NC}")
        return ip

    except Exception as e:
        if verbose:
            print(f"{YELLOW}⚠️  Error leyendo caché de IP: {e}{NC}")
        return None


def save_cached_ip(app_name, ip, verbose=True):
    """
    Guarda la IP de una app en el caché.

    Args:
        app_name: Nombre de la app (blink, gallinero, heladera)
        ip: IP del ESP8266
        verbose: Si True, muestra mensajes informativos
    """
    cache_file = get_cache_dir() / f"ip_{app_name}.txt"

    try:
        with open(cache_file, 'w') as f:
            f.write(f"{ip}\n")
            f.write(f"{time.time()}\n")

        if verbose:
            print(f"{GREEN}💾 IP guardada en caché para '{app_name}': {ip}{NC}")

    except Exception as e:
        if verbose:
            print(f"{YELLOW}⚠️  Error guardando caché de IP: {e}{NC}")


def clear_cache(app_name=None, verbose=True):
    """
    Limpia el caché de IPs.

    Args:
        app_name: Nombre de la app a limpiar, o None para limpiar todo
        verbose: Si True, muestra mensajes informativos
    """
    cache_dir = get_cache_dir()

    if app_name:
        cache_file = cache_dir / f"ip_{app_name}.txt"
        if cache_file.exists():
            cache_file.unlink()
            if verbose:
                print(f"{GREEN}🗑️  Caché de '{app_name}' limpiado{NC}")
    else:
        # Limpiar todos los cachés
        for cache_file in cache_dir.glob("ip_*.txt"):
            cache_file.unlink()
        if verbose:
            print(f"{GREEN}🗑️  Todos los cachés limpiados{NC}")
