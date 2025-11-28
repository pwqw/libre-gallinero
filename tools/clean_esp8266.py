#!/usr/bin/env python3
"""
Limpia archivos viejos del ESP8266 vía WebREPL.
Útil para borrar apps viejas o archivos residuales.
"""

import sys
from pathlib import Path

# Agregar tools/common al path
script_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(script_dir))

from common.webrepl_client import WebREPLClient, GREEN, YELLOW, BLUE, RED, NC, load_config


def list_files(client):
    """Lista todos los archivos y directorios en el ESP8266"""
    print(f"{BLUE}📋 Listando archivos en ESP8266...{NC}\n")

    code = """
import os
def list_all(path='/', indent=0):
    try:
        items = os.listdir(path)
        for item in sorted(items):
            full_path = path + ('/' if path != '/' else '') + item
            try:
                # Try to list it as directory
                os.listdir(full_path)
                print('  ' * indent + f'📁 {item}/')
                list_all(full_path, indent + 1)
            except OSError:
                # It's a file
                try:
                    size = os.stat(full_path)[6]
                    print('  ' * indent + f'📄 {item} ({size} bytes)')
                except:
                    print('  ' * indent + f'📄 {item}')
    except Exception as e:
        print(f'Error listing {path}: {e}')

list_all('/')
"""

    response = client.execute(code, timeout=10)
    print(response)


def remove_directory(client, dir_name):
    """Elimina un directorio y todo su contenido"""
    print(f"{YELLOW}🗑️  Eliminando directorio: {dir_name}{NC}")

    code = f"""
import os

def rmdir_recursive(path):
    try:
        items = os.listdir(path)
        for item in items:
            full_path = path + '/' + item
            try:
                # Try as directory
                os.listdir(full_path)
                rmdir_recursive(full_path)
            except OSError:
                # It's a file
                os.remove(full_path)
                print(f'  Eliminado: {{full_path}}')
        os.rmdir(path)
        print(f'  Directorio eliminado: {{path}}')
    except Exception as e:
        print(f'  Error: {{e}}')

rmdir_recursive('{dir_name}')
"""

    response = client.execute(code, timeout=10)
    print(response)


def remove_file(client, file_name):
    """Elimina un archivo"""
    print(f"{YELLOW}🗑️  Eliminando archivo: {file_name}{NC}")

    code = f"""
import os
try:
    os.remove('{file_name}')
    print('✅ Eliminado: {file_name}')
except Exception as e:
    print(f'❌ Error: {{e}}')
"""

    response = client.execute(code, timeout=5)
    print(response)


def interactive_clean(client):
    """Modo interactivo para eliminar archivos/directorios"""
    print()
    print(f"{GREEN}{'━' * 60}{NC}")
    print(f"{GREEN}Modo de Limpieza Interactiva{NC}")
    print(f"{GREEN}{'━' * 60}{NC}")
    print()

    while True:
        print(f"{BLUE}Opciones:{NC}")
        print(f"  1. Listar archivos")
        print(f"  2. Eliminar directorio (ej: blink, gallinero, heladera)")
        print(f"  3. Eliminar archivo (ej: main.py, boot.py)")
        print(f"  4. Eliminar TODO (formato completo)")
        print(f"  5. Salir")
        print()

        try:
            choice = input(f"{YELLOW}Selección (1-5): {NC}").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if choice == '1':
            list_files(client)
        elif choice == '2':
            dir_name = input(f"{YELLOW}Nombre del directorio: {NC}").strip()
            if dir_name:
                confirm = input(f"{RED}⚠️  ¿Eliminar '{dir_name}/' y todo su contenido? (s/N): {NC}").strip().lower()
                if confirm == 's':
                    remove_directory(client, dir_name)
                else:
                    print(f"{BLUE}Cancelado{NC}")
        elif choice == '3':
            file_name = input(f"{YELLOW}Nombre del archivo: {NC}").strip()
            if file_name:
                confirm = input(f"{RED}⚠️  ¿Eliminar '{file_name}'? (s/N): {NC}").strip().lower()
                if confirm == 's':
                    remove_file(client, file_name)
                else:
                    print(f"{BLUE}Cancelado{NC}")
        elif choice == '4':
            print(f"{RED}⚠️  PELIGRO: Esto eliminará TODOS los archivos del ESP8266{NC}")
            confirm = input(f"{RED}¿Borrar TODO? [s/N]: {NC}").strip().lower()
            if confirm == 's':
                format_all(client)
            else:
                print(f"{BLUE}Cancelado{NC}")
        elif choice == '5':
            print(f"{GREEN}👋 Saliendo...{NC}")
            break
        else:
            print(f"{RED}Opción inválida{NC}")

        print()


def format_all(client):
    """Elimina TODOS los archivos del ESP8266 (formato completo)"""
    print(f"{RED}🗑️  FORMATEANDO ESP8266...{NC}")

    code = """
import os

def rmdir_recursive(path):
    try:
        items = os.listdir(path)
        for item in items:
            if item in ['boot.py', 'webrepl_cfg.py']:
                # Preserve boot.py and webrepl_cfg.py for recovery
                continue
            full_path = path + ('/' if path != '/' else '') + item
            try:
                os.listdir(full_path)
                rmdir_recursive(full_path)
            except OSError:
                os.remove(full_path)
                print(f'  Eliminado: {full_path}')
        if path != '/':
            os.rmdir(path)
            print(f'  Directorio eliminado: {path}')
    except Exception as e:
        print(f'  Error: {e}')

rmdir_recursive('/')
print('✅ ESP8266 formateado (boot.py y webrepl_cfg.py preservados)')
"""

    response = client.execute(code, timeout=15)
    print(response)
    print()
    print(f"{YELLOW}⚠️  ESP8266 formateado. Ejecuta un deploy para instalar una app.{NC}")


def main():
    print(f"{BLUE}🐔 Libre-Gallinero - Limpieza de ESP8266{NC}\n")

    # Detectar directorio del proyecto
    project_dir = script_dir.parent
    config = load_config(project_dir)

    # Conectar
    client = WebREPLClient(project_dir=project_dir, verbose=True, auto_discover=True)

    if not client.connect():
        sys.exit(1)

    # Interrumpir programa actual
    print(f"{BLUE}⏸️  Deteniendo programa actual...{NC}")
    try:
        client.execute("\x03", timeout=1)
        print(f"{GREEN}✅ Programa detenido{NC}\n")
    except:
        print(f"{YELLOW}⚠️  No se pudo detener programa{NC}\n")

    # Modo interactivo
    interactive_clean(client)

    client.close()


if __name__ == '__main__':
    main()
