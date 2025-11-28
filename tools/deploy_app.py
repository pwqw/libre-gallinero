#!/usr/bin/env python3
"""
Wrapper para deploy_wifi.py con soporte de caché de IPs por app.
Acelera el descubrimiento de ESP8266 guardando la última IP exitosa.

Uso:
    python3 tools/deploy_app.py blink
    python3 tools/deploy_app.py gallinero
    python3 tools/deploy_app.py heladera
    python3 tools/deploy_app.py <app> <ip_opcional>

Este script:
1. Carga la IP cacheada para la app (si existe)
2. Actualiza el repo con git pull
3. Ejecuta deploy_wifi.py con la app especificada
4. Guarda la IP exitosa en el caché para próximas ejecuciones
"""

import sys
import subprocess
from pathlib import Path

# Agregar tools/common al path
script_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(script_dir))

from common.ip_cache import get_cached_ip, save_cached_ip
from common.webrepl_client import GREEN, YELLOW, BLUE, RED, NC


def main():
    if len(sys.argv) < 2:
        print(f"{RED}❌ Uso: {sys.argv[0]} <app_name> [ip_opcional]{NC}")
        print(f"   Apps válidas: blink, gallinero, heladera")
        sys.exit(1)

    app_name = sys.argv[1]
    ip_arg = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"{BLUE}🐔 Libre-Gallinero Deploy: {app_name}{NC}\n")

    # Detectar directorio del proyecto
    project_dir = script_dir.parent

    # Git pull para actualizar el repo
    print(f"{BLUE}🔄 Actualizando repositorio...{NC}")
    try:
        result = subprocess.run(
            ['git', 'pull', '--rebase'],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            # Mostrar solo si hay cambios
            if "Already up to date" not in result.stdout:
                print(f"{GREEN}✅ Repositorio actualizado{NC}")
                print(result.stdout.strip())
            else:
                print(f"{GREEN}✅ Repositorio ya actualizado{NC}")
        else:
            print(f"{YELLOW}⚠️  Git pull falló (continuando de todas formas){NC}")
    except Exception as e:
        print(f"{YELLOW}⚠️  Error en git pull: {e} (continuando de todas formas){NC}")

    print()

    # Cargar IP cacheada si no se especificó una
    cached_ip = None
    if not ip_arg:
        cached_ip = get_cached_ip(app_name, verbose=True)
        if cached_ip:
            print()

    # Construir argumentos para deploy_wifi.py
    deploy_args = ['python3', 'tools/deploy_wifi.py', app_name]

    # Si se especificó IP manualmente, usarla (tiene prioridad sobre caché)
    if ip_arg:
        deploy_args.append(ip_arg)
        print(f"{BLUE}🌐 Usando IP especificada: {ip_arg}{NC}\n")
    elif cached_ip:
        # Pasar la IP cacheada como argumento
        deploy_args.append(cached_ip)

    # Ejecutar deploy_wifi.py
    print(f"{BLUE}🚀 Ejecutando deploy de '{app_name}'...{NC}\n")
    print("━" * 50)
    print()

    try:
        result = subprocess.run(
            deploy_args,
            cwd=project_dir,
            env={**subprocess.os.environ, 'DEPLOY_APP_NAME': app_name}  # Pasar app_name en env
        )

        if result.returncode == 0:
            # Deploy exitoso - guardar IP en caché
            # La IP fue descubierta por deploy_wifi.py, necesitamos extraerla
            # Para esto, vamos a modificar deploy_wifi.py para que guarde en caché

            print()
            print("━" * 50)
            print(f"{GREEN}✅ Deploy de '{app_name}' completado exitosamente{NC}")

            # NOTA: El guardado de caché ahora se hace desde deploy_wifi.py
            # usando la variable de entorno DEPLOY_APP_NAME
            sys.exit(0)
        else:
            print()
            print("━" * 50)
            print(f"{RED}❌ Deploy de '{app_name}' falló{NC}")
            sys.exit(1)

    except KeyboardInterrupt:
        print()
        print(f"{YELLOW}⚠️  Deploy cancelado por el usuario{NC}")
        sys.exit(130)
    except Exception as e:
        print()
        print(f"{RED}❌ Error ejecutando deploy: {e}{NC}")
        sys.exit(1)


if __name__ == '__main__':
    main()
