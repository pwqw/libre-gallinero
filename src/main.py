# main.py - Generic WiFi/Hotspot Manager + Project Loader
# Reusable across different projects (gallinero, heladera, etc.)

try:
    import network
    import ntptime
    import machine
    import socket
    import gc
    gc.collect()
except ImportError:
    print("[main] ERROR: Módulos MicroPython no encontrados")

import time

# === CONFIGURACIÓN ===
def parse_env(path):
    """Lee .env"""
    cfg = {}
    try:
        with open(path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    cfg[k.strip()] = v.strip().strip('"').strip("'")
    except:
        pass
    return cfg

def load_config():
    """Carga config desde .env con defaults"""
    cfg = parse_env('.env')
    if not cfg:
        cfg = parse_env('.env.example')
    if not cfg:
        cfg = {
            'WIFI_SSID': 'libre gallinero',
            'WIFI_PASSWORD': 'huevos1',
            'WIFI_HIDDEN': 'false',
            'LATITUDE': '-31.4167',
            'LONGITUDE': '-64.1833',
            'PROJECT': 'gallinero'  # Default project
        }
    return cfg

# === HOTSPOT TIME SYNC ===
def hotspot_server():
    """Servidor HTTP para sincronización de hora vía JavaScript"""
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(1)

    print('[main] HTTP: 192.168.4.1')
    gc.collect()

    while True:
        try:
            cl, _ = s.accept()
            req = cl.recv(1024).decode('utf-8')

            if 'POST /settime' in req:
                parts = req.split('\r\n\r\n', 1)
                body = parts[1] if len(parts) > 1 else ''

                try:
                    # Espera JSON: {"timestamp": 1234567890}
                    import json
                    data = json.loads(body)
                    timestamp = data.get('timestamp')

                    if timestamp:
                        # Convertir timestamp a tupla de tiempo
                        import utime
                        tm = utime.localtime(timestamp)
                        machine.RTC().datetime((tm[0], tm[1], tm[2], tm[6], tm[3], tm[4], tm[5], 0))
                        print('[main] Hora sincronizada:', tm)
                        cl.send(b'HTTP/1.1 200 OK\r\n\r\n{"status":"ok"}')
                    else:
                        cl.send(b'HTTP/1.1 400\r\n\r\n{"status":"error"}')
                except Exception as e:
                    print('[main] Sync error:', e)
                    cl.send(b'HTTP/1.1 500\r\n\r\n{"status":"error"}')
            else:
                # GET: página con JavaScript para sync (optimizada para memoria)
                h='HTTP/1.1 200 OK\r\nContent-Type:text/html\r\n\r\n'
                h+='<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Libre-Gallinero</title></head>'
                h+='<body style="font-family:sans-serif;padding:2em;text-align:center">'
                h+='<h2>Libre-Gallinero</h2><p id="s">Sincronizando hora...</p><script>'
                h+='fetch("/settime",{method:"POST",headers:{"Content-Type":"application/json"},'
                h+='body:JSON.stringify({timestamp:Math.floor(Date.now()/1000)})'
                h+='}).then(r=>r.json()).then(d=>{'
                h+='document.getElementById("s").textContent='
                h+='d.status==="ok"?"Hora sincronizada":"Error";'
                h+='}).catch(()=>{document.getElementById("s").textContent="Error conexión";});'
                h+='</script></body></html>'
                cl.send(h.encode('utf-8'))
                gc.collect()

            cl.close()
        except Exception as e:
            print('[main] HTTP err:', e)
            try:
                cl.close()
            except:
                pass

def start_hotspot(cfg):
    """Crea hotspot para sincronización de hora"""
    ap_ssid = cfg['WIFI_SSID']
    ap_pw = cfg['WIFI_PASSWORD']

    print("[main] Creando hotspot:", ap_ssid)
    gc.collect()

    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid=ap_ssid, password=ap_pw, authmode=3)

    try:
        ap.ifconfig(('192.168.4.1', '255.255.255.0', '192.168.4.1', '192.168.4.1'))
    except:
        pass

    ip = ap.ifconfig()[0]
    print("[main] Hotspot OK:", ip)
    print("[main] SSID:", ap_ssid)
    print("[main] HTTP Sync: http://", ip, sep='')
    print("[main] WebREPL: ws://", ip, ":8266", sep='')
    print("[main] (WebREPL ya iniciado por boot.py)")
    gc.collect()

    hotspot_server()

# === WIFI + NTP ===
def connect_wifi(cfg):
    """
    Conecta WiFi siguiendo lógica:
    1. Busca red por SSID
    2. Intenta conectar con password
    3. Si falla, retorna False (main.py creará hotspot)
    """
    print('[main] === Iniciando conexión WiFi ===')
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        print('[main] WiFi ya conectado:', wlan.ifconfig()[0])
        return True

    ssid = cfg['WIFI_SSID']
    pw = cfg['WIFI_PASSWORD']
    hidden = cfg.get('WIFI_HIDDEN', 'false').lower() == 'true'

    print(f'[main] Buscando red: {ssid}')
    
    # Escanear redes disponibles para verificar que existe
    print('[main] Escaneando redes...')
    networks = wlan.scan()
    found = False
    for net in networks:
        net_ssid = net[0].decode('utf-8') if isinstance(net[0], bytes) else net[0]
        if net_ssid == ssid:
            found = True
            print(f'[main] ✓ Red encontrada: {ssid}')
            break
    
    if not found and not hidden:
        print(f'[main] ⚠ Red no encontrada en escaneo: {ssid}')
        print('[main] Intentando conexión directa (puede ser red oculta)...')

    # Intentar conectar
    print(f'[main] Intentando conectar a {ssid}...')
    try:
        if hidden:
            wlan.connect(ssid, pw, -1)
        else:
            wlan.connect(ssid, pw)
    except TypeError:
        wlan.connect(ssid, pw)
    except Exception as e:
        print(f'[main] Error al conectar: {e}')
        return False

    # Esperar conexión (timeout 15s)
    timeout = 0
    while not wlan.isconnected() and timeout < 15:
        time.sleep(1)
        timeout += 1
        if timeout % 3 == 0:
            print(f'[main] Esperando conexión... ({timeout}/15s)')

    if wlan.isconnected():
        ip = wlan.ifconfig()[0]
        print(f'[main] ✓ WiFi conectado: {ip}')
        print(f'[main] WebREPL: ws://{ip}:8266')
        print('[main] === Conexión WiFi exitosa ===')
        return True

    print(f'[main] ✗ WiFi FAIL - No se pudo conectar a {ssid}')
    print('[main] === Fallo de conexión WiFi ===')
    return False

def sync_ntp():
    """Sincroniza NTP"""
    print('[main] Sincronizando NTP...')
    for i in range(5):
        try:
            ntptime.settime()
            print('[main] NTP OK')
            return True
        except Exception as e:
            print(f'[main] NTP intento {i+1}/5: {e}')
            time.sleep(2)
    print('[main] NTP FAIL')
    return False

# === PROJECT LOADER ===
def load_project(project_name, cfg):
    """Load and run project-specific code"""
    print(f'[main] Cargando proyecto: {project_name}')
    gc.collect()
    
    try:
        if project_name == 'gallinero':
            import gallinero
            gallinero.run(cfg)
        elif project_name == 'heladera':
            import heladera
            heladera.blink_led()
        else:
            print(f'[main] Proyecto desconocido: {project_name}')
            print('[main] Proyectos disponibles: gallinero, heladera')
    except ImportError as e:
        print(f'[main] Error importando proyecto {project_name}: {e}')
        print('[main] Asegúrate de que el módulo existe en src/')
    except Exception as e:
        print(f'[main] Error ejecutando proyecto {project_name}: {e}')
        import sys
        sys.print_exception(e)

# === MAIN LOOP ===
def main():
    """Función principal - DEBE ejecutarse manualmente vía WebREPL: import main"""
    print('\n=== main.py ===')
    gc.collect()
    
    cfg = load_config()
    project = cfg.get('PROJECT', 'gallinero')
    print('[main] Config:', cfg.get('WIFI_SSID'))
    print('[main] Proyecto:', project)
    gc.collect()

    if not connect_wifi(cfg):
        print('[main] Iniciando hotspot...')
        gc.collect()
        start_hotspot(cfg)
        return

    if not sync_ntp():
        print('[main] Sin NTP, reloj puede estar mal')
    gc.collect()

    # Load and run project-specific code
    load_project(project, cfg)

# IMPORTANTE: main.py NO se ejecuta automáticamente
# Para iniciar manualmente vía WebREPL:
#   >>> import main
#   >>> main.main()
# O simplemente:
#   >>> from main import main; main()
#
# Esto garantiza que WebREPL siempre esté disponible después de boot.py
