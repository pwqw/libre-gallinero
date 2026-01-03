#!/usr/bin/env python3
"""
Toggle Modo Helado - Alterna modo helado de la heladera vía WebREPL

Uso:
    python3 tools/toggle_modo_helado.py              # Usa IP del .env
    python3 tools/toggle_modo_helado.py 192.168.1.50 # IP específica

Modifica HELADERA_MODO_HELADO en .env local, lo sube al ESP8266,
y reinicia para aplicar cambios.
"""

import sys
import re
from pathlib import Path

script_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(script_dir / 'common'))

from webrepl_client import WebREPLClient, RED, GREEN, YELLOW, BLUE, CYAN, NC


def leer_modo_actual(env_path):
    """Lee HELADERA_MODO_HELADO del .env local"""
    if not env_path.exists():
        return 'false'
    
    with open(env_path, 'r') as f:
        for line in f:
            if line.strip().startswith('HELADERA_MODO_HELADO='):
                valor = line.split('=', 1)[1].strip().strip('"').strip("'")
                return valor.lower()
    return 'false'


def actualizar_env(env_path, nuevo_valor):
    """Actualiza HELADERA_MODO_HELADO en .env local, retorna path al temporal"""
    temp_path = env_path.parent / '.env.tmp'
    
    if env_path.exists():
        with open(env_path, 'r') as f:
            contenido = f.read()
        
        # Actualizar o agregar
        if re.search(r'^HELADERA_MODO_HELADO=', contenido, re.MULTILINE):
            contenido = re.sub(
                r'^HELADERA_MODO_HELADO=.*$',
                f'HELADERA_MODO_HELADO={nuevo_valor}',
                contenido,
                flags=re.MULTILINE
            )
        else:
            if not contenido.endswith('\n'):
                contenido += '\n'
            contenido += f'\n# Modo helado (auto-updated)\nHELADERA_MODO_HELADO={nuevo_valor}\n'
    else:
        contenido = f'HELADERA_MODO_HELADO={nuevo_valor}\n'
    
    with open(temp_path, 'w') as f:
        f.write(contenido)
    
    return temp_path


def main():
    print(f"{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}")
    print(f"{CYAN}❄️  Toggle Modo Helado - Heladera{NC}")
    print(f"{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}\n")

    # Parsear IP opcional
    ip_arg = None
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if '.' in arg and any(c.isdigit() for c in arg):
            ip_arg = arg
            print(f"{BLUE}🌐 IP: {ip_arg}{NC}\n")

    project_dir = script_dir.parent
    env_path = project_dir / '.env'

    # 1. Leer modo actual del .env LOCAL
    modo_actual = leer_modo_actual(env_path)
    es_helado = modo_actual in ('true', '1', 'yes', 'on')

    print(f"{YELLOW}Estado actual:{NC}")
    if es_helado:
        print(f"  {CYAN}❄️  Modo HELADO{NC} (10/10 min, sin horario nocturno)")
    else:
        print(f"  {BLUE}🌡️  Modo NORMAL{NC} (12/18 min, descanso 01:30-07:00)")

    # 2. Alternar valor
    nuevo_valor = 'false' if es_helado else 'true'

    print(f"\n{YELLOW}Nuevo estado:{NC}")
    if nuevo_valor == 'true':
        print(f"  {CYAN}❄️  Activando Modo HELADO{NC}")
    else:
        print(f"  {BLUE}🌡️  Volviendo a Modo NORMAL{NC}")

    # 3. Actualizar .env local
    print(f"\n{BLUE}📝 Actualizando .env local...{NC}")
    temp_env = actualizar_env(env_path, nuevo_valor)
    print(f"{GREEN}   ✅ .env.tmp creado{NC}")

    # 4. Conectar al ESP8266
    print(f"\n{BLUE}🔌 Conectando al ESP8266...{NC}")
    auto_discover = not bool(ip_arg)
    client = WebREPLClient(project_dir=project_dir, verbose=True, auto_discover=auto_discover)
    
    if ip_arg:
        client.ip = ip_arg

    if not client.connect():
        print(f"{RED}❌ No se pudo conectar al ESP8266{NC}")
        temp_env.unlink(missing_ok=True)
        sys.exit(1)

    print(f"{GREEN}   ✅ Conectado{NC}")

    # 5. Subir .env al ESP8266
    print(f"\n{BLUE}📤 Subiendo .env al ESP8266...{NC}")
    try:
        if client.send_file(str(temp_env), '.env'):
            print(f"{GREEN}   ✅ .env actualizado en ESP8266{NC}")
        else:
            print(f"{RED}   ❌ Error subiendo .env{NC}")
            client.close()
            temp_env.unlink(missing_ok=True)
            sys.exit(1)
    finally:
        temp_env.unlink(missing_ok=True)

    # 6. Resetear ESP8266 para aplicar cambios
    print(f"\n{BLUE}🔄 Reiniciando ESP8266...{NC}")
    try:
        client.reset()
        print(f"{GREEN}   ✅ Reset enviado{NC}")
    except:
        print(f"{YELLOW}   ⚠️  No se pudo resetear (aplicará en próximo ciclo){NC}")
    
    client.close()

    # Resumen
    print(f"\n{GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}")
    if nuevo_valor == 'true':
        print(f"{GREEN}✅ Modo HELADO activado{NC}")
        print(f"   Ciclo: 10 min ON / 10 min OFF")
        print(f"   Horario nocturno: IGNORADO")
    else:
        print(f"{GREEN}✅ Modo NORMAL activado{NC}")
        print(f"   Ciclo: 12 min ON / 18 min OFF")
        print(f"   Horario nocturno: 01:30-07:00 OFF")
    print(f"{GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}\n")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Cancelado{NC}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{RED}❌ Error: {e}{NC}")
        sys.exit(1)
