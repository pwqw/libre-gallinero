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
from pathlib import Path

# Agregar directorio de herramientas al path
script_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(script_dir / 'common'))

from webrepl_client import WebREPLClient, RED, GREEN, YELLOW, BLUE, CYAN, NC


def get_current_mode(client):
    """Obtiene el estado actual del modo helado ejecutando código en ESP8266"""
    print(f"{BLUE}📖 Leyendo estado actual...{NC}")
    
    # Comando para leer el valor actual directamente
    check_cmd = """
import sys
try:
    modo = 'false'
    try:
        with open('.env', 'r') as f:
            for line in f:
                if line.strip().startswith('HELADERA_MODO_HELADO='):
                    modo = line.split('=', 1)[1].strip().strip('"').strip("'")
                    break
    except:
        pass
    print('MODO:' + modo, end='')
    if hasattr(sys.stdout, 'flush'):
        sys.stdout.flush()
except Exception as e:
    print('ERROR:' + str(e), end='')
    if hasattr(sys.stdout, 'flush'):
        sys.stdout.flush()
"""
    
    response = client.execute(check_cmd, timeout=5)
    
    if 'ERROR:' in response:
        print(f"{YELLOW}⚠️  No se pudo leer modo actual, asumiendo 'false'{NC}")
        return 'false'
    
    # Buscar MODO: en toda la respuesta
    if 'MODO:' in response:
        idx = response.find('MODO:')
        # Extraer hasta 20 caracteres después de MODO:
        modo_part = response[idx+5:idx+25].strip()
        # Buscar true o false
        if 'true' in modo_part.lower():
            return 'true'
        else:
            return 'false'
    
    print(f"{YELLOW}⚠️  No se encontró HELADERA_MODO_HELADO, asumiendo 'false'{NC}")
    return 'false'


def toggle_mode_on_esp8266(client, current_value):
    """Alterna el modo helado ejecutando código directamente en ESP8266"""
    print(f"{BLUE}📝 Alternando modo helado...{NC}")
    
    # Determinar nuevo valor
    is_helado = current_value.lower() in ('true', '1', 'yes', 'on')
    new_value = 'false' if is_helado else 'true'
    
    # Código Python para modificar .env en el ESP8266
    # Usamos print() inmediatos para evitar buffer
    toggle_cmd = f"""
import os
import sys
try:
    lines = []
    found = False
    try:
        with open('.env', 'r') as f:
            for line in f:
                if line.strip().startswith('HELADERA_MODO_HELADO='):
                    lines.append('HELADERA_MODO_HELADO={new_value}\\n')
                    found = True
                else:
                    lines.append(line)
    except OSError as e:
        pass
    if not found:
        lines.append('HELADERA_MODO_HELADO={new_value}\\n')
    with open('.env.tmp', 'w') as f:
        for line in lines:
            f.write(line)
    try:
        os.remove('.env')
    except:
        pass
    os.rename('.env.tmp', '.env')
    print('SUCCESS:{new_value}', end='')
    if hasattr(sys.stdout, 'flush'):
        sys.stdout.flush()
except Exception as e:
    print('ERROR:' + str(e), end='')
    if hasattr(sys.stdout, 'flush'):
        sys.stdout.flush()
"""
    
    response = client.execute(toggle_cmd, timeout=15)
    
    # Debug: Mostrar respuesta cruda
    print(f"{YELLOW}Debug - Respuesta del ESP8266:{NC}")
    print(f"  Longitud: {len(response)} caracteres")
    print(f"  Contiene SUCCESS: {'SUCCESS:' in response}")
    print(f"  Contiene ERROR: {'ERROR:' in response}")
    print(f"  Primeros 200 chars: {repr(response[:200])}")
    
    # Verificar resultado - buscar en toda la respuesta
    if 'SUCCESS:' in response:
        # Extraer valor después de SUCCESS:
        idx = response.find('SUCCESS:')
        if idx >= 0:
            # Tomar hasta 20 caracteres después de SUCCESS:
            result_part = response[idx:idx+30]
            # Extraer valor (true o false)
            if 'true' in result_part.lower():
                result_value = 'true'
            else:
                result_value = 'false'
            print(f"{GREEN}✅ Modo actualizado a: {result_value}{NC}")
            return result_value
    
    if 'ERROR:' in response:
        print(f"{RED}❌ Error al actualizar modo:{NC}")
        # Mostrar línea con ERROR
        for line in response.split('\n'):
            if 'ERROR:' in line:
                print(f"   {line}")
        return None
    
    print(f"{RED}❌ Respuesta inesperada del ESP8266{NC}")
    print(f"{YELLOW}Respuesta completa:{NC}")
    print(response)
    return None


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
        # Obtener estado actual
        current_value = get_current_mode(client)
        is_helado = current_value.lower() in ('true', '1', 'yes', 'on')

        print(f"\n{YELLOW}Estado actual:{NC}")
        if is_helado:
            print(f"  {CYAN}❄️  Modo HELADO activo{NC}")
            print(f"  Ciclo: 10 min ON / 10 min OFF")
            print(f"  Horario nocturno: IGNORADO (siempre activo)")
        else:
            print(f"  {BLUE}🌡️  Modo NORMAL activo{NC}")
            print(f"  Ciclo: 12 min ON / 18 min OFF")
            print(f"  Horario nocturno: 01:30-07:00 OFF")

        print(f"\n{YELLOW}Alternando modo...{NC}")
        if not is_helado:
            print(f"  {CYAN}❄️  Activando Modo HELADO{NC}")
        else:
            print(f"  {BLUE}🌡️  Desactivando Modo HELADO (volviendo a NORMAL){NC}")

        # Alternar modo directamente en el ESP8266
        new_value = toggle_mode_on_esp8266(client, current_value)
        
        if new_value:
            print(f"\n{GREEN}✅ Modo helado alternado exitosamente{NC}")
            print(f"{YELLOW}💡 El cambio se aplicará en el próximo ciclo (~1 segundo){NC}")
            print(f"{YELLOW}   (o reinicia el ESP8266 para aplicar inmediatamente){NC}\n")
        else:
            print(f"\n{RED}❌ Error al alternar modo helado{NC}\n")
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
