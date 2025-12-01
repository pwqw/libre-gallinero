#!/usr/bin/env python3
"""
Wrapper simplificado para deploy_wifi.py.
Usa siempre la IP del .env y hace git pull antes del deploy.

Uso:
    python3 tools/deploy_app.py blink
    python3 tools/deploy_app.py gallinero
    python3 tools/deploy_app.py heladera

Este script:
1. Actualiza el repo con git pull
2. Ejecuta deploy_wifi.py con la app especificada
3. La IP se obtiene siempre del .env
"""

import sys
import subprocess
from pathlib import Path

# Agregar tools/common al path
script_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(script_dir))

from common.webrepl_client import GREEN, YELLOW, BLUE, RED, NC


def main():
    if len(sys.argv) < 2:
        print(f"{RED}❌ Uso: {sys.argv[0]} <app_name>{NC}")
        print(f"   Apps válidas: blink, gallinero, heladera")
        sys.exit(1)

    app_name = sys.argv[1]

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

    # Construir argumentos para deploy_wifi.py (sin IP, usará .env)
    deploy_args = ['python3', 'tools/deploy_wifi.py', app_name]

    # Ejecutar deploy_wifi.py
    print(f"{BLUE}🚀 Ejecutando deploy de '{app_name}'...{NC}\n")
    print("━" * 50)
    print()

    try:
        result = subprocess.run(deploy_args, cwd=project_dir)

        if result.returncode == 0:
            print()
            print("━" * 50)
            print(f"{GREEN}✅ Deploy de '{app_name}' completado exitosamente{NC}")
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
