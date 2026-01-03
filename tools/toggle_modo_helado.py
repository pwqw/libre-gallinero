#!/usr/bin/env python3
"""
toggle_modo_helado.py - Alterna el modo helado de la heladera vía WebREPL

Uso:
    python3 tools/toggle_modo_helado.py              # Usa IP del .env
    python3 tools/toggle_modo_helado.py 192.168.1.50 # IP específica

Funcionamiento:
    1. Se conecta al ESP8266 vía WebREPL
    2. Lee el .env actual
    3. Alterna HELADERA_MODO_HELADO (true/false)
    4. Escribe el .env actualizado
    5. Muestra el estado actual
"""

import sys
import time
import tempfile
from pathlib import Path

# Agregar directorio de herramientas al path
script_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(script_dir / 'common'))

from webrepl_client import WebREPLClient, RED, GREEN, YELLOW, BLUE, CYAN, NC


def parse_env_content(content):
    """Parsea contenido de .env y retorna dict"""
    env_vars = {}
    for line in content.split('\n'):
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            env_vars[k.strip()] = v.strip().strip('"').strip("'")
    return env_vars


def format_env_content(env_vars):
    """Formatea dict de variables de entorno a formato .env"""
    lines = []
    for key, value in env_vars.items():
        # Si el valor contiene espacios o caracteres especiales, usar comillas
        if ' ' in value or any(c in value for c in ['#', '=', '"', "'"]):
            lines.append(f'{key}="{value}"')
        else:
            lines.append(f'{key}={value}')
    return '\n'.join(lines)


def read_env_from_esp8266(client):
    """Lee el .env del ESP8266 usando execute()"""
    print(f"{BLUE}📖 Leyendo .env del ESP8266...{NC}")
    
    # Comando para leer .env
    read_cmd = """
try:
    with open('.env', 'r') as f:
        content = f.read()
    print(content, end='')
except Exception as e:
    print(f'ERROR: {e}', end='')
"""
    
    # Limpiar buffer antes de ejecutar
    client._clean_buffer_before_binary_transfer()
    
    response = client.execute(read_cmd, timeout=5)
    
    if 'ERROR:' in response:
        print(f"{RED}❌ Error leyendo .env: {response}{NC}")
        return None
    
    # Extraer contenido del .env (puede tener prompts de REPL mezclados)
    lines = response.split('\n')
    env_lines = []
    in_env = False
    
    for line in lines:
        # Buscar inicio del contenido (después de >>> o ...)
        if not in_env and ('=' in line or line.strip().startswith('#')):
            in_env = True
        if in_env:
            # Detener si encontramos prompt de nuevo
            if line.strip() in ['>>>', '...']:
                break
            env_lines.append(line)
    
    env_content = '\n'.join(env_lines).strip()
    
    if not env_content:
        print(f"{YELLOW}⚠️  .env vacío o no encontrado, usando valores por defecto{NC}")
        return {}
    
    return parse_env_content(env_content)


def write_env_to_esp8266(client, env_vars):
    """Escribe el .env al ESP8266 usando send_file()"""
    print(f"{BLUE}📝 Escribiendo .env actualizado al ESP8266...{NC}")
    
    # Crear archivo temporal
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as f:
        env_content = format_env_content(env_vars)
        f.write(env_content)
        temp_path = f.name
    
    try:
        # Limpiar buffer antes de transferencia binaria
        client._clean_buffer_before_binary_transfer()
        
        # Enviar archivo
        if client.send_file(temp_path, '.env'):
            print(f"{GREEN}✅ .env actualizado exitosamente{NC}")
            return True
        else:
            print(f"{RED}❌ Error escribiendo .env{NC}")
            return False
    finally:
        # Limpiar archivo temporal
        try:
            Path(temp_path).unlink()
        except:
            pass


def main():
    print(f"{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}")
    print(f"{CYAN}❄️  Alternar Modo Helado{NC}")
    print(f"{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}\n")

    # Parsear argumentos
    ip_arg = None
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if '.' in arg and any(c.isdigit() for c in arg):
            ip_arg = arg
            print(f"{BLUE}🌐 IP especificada: {ip_arg}{NC}\n")

    # Detectar directorio del proyecto
    project_dir = script_dir.parent

    # Conectar a WebREPL
    auto_discover = not bool(ip_arg)
    client = WebREPLClient(project_dir=project_dir, verbose=True, auto_discover=auto_discover)

    if ip_arg:
        client.ip = ip_arg

    if not client.connect():
        print(f"{RED}❌ No se pudo conectar al ESP8266{NC}")
        sys.exit(1)

    print(f"\n{GREEN}✅ Conectado al ESP8266{NC}\n")

    try:
        # Leer .env actual
        env_vars = read_env_from_esp8266(client)
        if env_vars is None:
            print(f"{RED}❌ No se pudo leer .env{NC}")
            client.close()
            sys.exit(1)

        # Obtener estado actual
        current_value = env_vars.get('HELADERA_MODO_HELADO', 'false').lower()
        is_helado = current_value in ('true', '1', 'yes', 'on')

        print(f"\n{YELLOW}Estado actual:{NC}")
        if is_helado:
            print(f"  {CYAN}❄️  Modo HELADO activo{NC}")
            print(f"  Ciclo: 10 min ON / 10 min OFF")
            print(f"  Horario nocturno: IGNORADO (siempre activo)")
        else:
            print(f"  {BLUE}🌡️  Modo NORMAL activo{NC}")
            print(f"  Ciclo: 12 min ON / 18 min OFF")
            print(f"  Horario nocturno: 01:30-07:00 OFF")

        # Alternar valor
        new_value = 'false' if is_helado else 'true'
        env_vars['HELADERA_MODO_HELADO'] = new_value

        print(f"\n{YELLOW}Nuevo estado:{NC}")
        if not is_helado:
            print(f"  {CYAN}❄️  Activando Modo HELADO{NC}")
        else:
            print(f"  {BLUE}🌡️  Desactivando Modo HELADO (volviendo a NORMAL){NC}")

        # Escribir .env actualizado
        if write_env_to_esp8266(client, env_vars):
            print(f"\n{GREEN}✅ Modo helado alternado exitosamente{NC}")
            print(f"{YELLOW}💡 El cambio se aplicará en el próximo ciclo{NC}")
            print(f"{YELLOW}   (o reinicia el ESP8266 para aplicar inmediatamente){NC}\n")
        else:
            print(f"\n{RED}❌ Error al actualizar modo helado{NC}\n")
            client.close()
            sys.exit(1)

    except Exception as e:
        print(f"{RED}❌ Error: {e}{NC}")
        import traceback
        traceback.print_exc()
        client.close()
        sys.exit(1)
    finally:
        client.close()


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
