# main.py - Lógica principal con hotspot fallback
# Lee .env para configuración unificada

try:
    import network
    import ntptime
    import machine
    import dht
    import socket
    import gc
    gc.collect()
except ImportError:
    print("[main] ERROR: Módulos MicroPython no encontrados")

import time
from solar import calc_sun_times
from logic import relay_ponedoras_state, relay_pollitos_state

# Hardware
RELAY1_PIN = 5   # D1 - Ponedoras
RELAY2_PIN = 4   # D2 - Pollitos
DHT_PIN = 14     # D5

relay1 = machine.Pin(RELAY1_PIN, machine.Pin.OUT)
relay2 = machine.Pin(RELAY2_PIN, machine.Pin.OUT)
dht_sensor = dht.DHT22(machine.Pin(DHT_PIN))

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
            'LONGITUDE': '-64.1833'
        }
    return cfg

# === HOTSPOT CONFIG ===
def url_decode(s):
    """Decodifica URL"""
    res = []
    i = 0
    while i < len(s):
        c = s[i]
        if c == '%' and i + 2 < len(s):
            try:
                res.append(chr(int(s[i+1:i+3], 16)))
                i += 3
                continue
            except:
                pass
        elif c == '+':
            res.append(' ')
            i += 1
            continue
        res.append(c)
        i += 1
    return ''.join(res)

def scan_networks():
    """Escanea WiFi"""
    print("[main] Escaneando WiFi...")
    gc.collect()
    sta = network.WLAN(network.STA_IF)
    sta.active(True)

    t0 = time.ticks_ms()
    nets = []
    while time.ticks_diff(time.ticks_ms(), t0) < 5000:
        try:
            nets = sta.scan()
            if nets:
                break
        except:
            pass
        time.sleep(1)

    ssids = []
    for n in nets:
        ssid = n[0].decode('utf-8') if isinstance(n[0], bytes) else str(n[0])
        if ssid and ssid not in ssids:
            ssids.append(ssid)

    print(f"[main] Encontradas {len(ssids)} redes")
    gc.collect()
    return ssids

def save_env(ssid, pw, hidden, lat, lon):
    """Guarda config en .env"""
    try:
        with open('.env', 'w') as f:
            f.write('# Libre-Gallinero\n')
            f.write(f'WIFI_SSID="{ssid}"\n')
            f.write(f'WIFI_PASSWORD="{pw}"\n')
            f.write(f'WIFI_HIDDEN={"true" if hidden else "false"}\n')
            f.write('WEBREPL_PASSWORD=admin\n')
            f.write(f'LATITUDE={lat if lat else "-31.4167"}\n')
            f.write(f'LONGITUDE={lon if lon else "-64.1833"}\n')
        print('[main] .env guardado')
        return True
    except Exception as e:
        print('[main] .env FAIL:', e)
        return False

def hotspot_server(ssids):
    """Servidor HTTP config - MINIMALISTA"""
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
            req = cl.recv(2048).decode('utf-8')

            if 'POST /' in req:
                parts = req.split('\r\n\r\n', 1)
                body = parts[1] if len(parts) > 1 else ''

                params = {}
                for pair in body.split('&'):
                    if '=' in pair:
                        k, v = pair.split('=', 1)
                        params[url_decode(k)] = url_decode(v)

                ssid = params.get('ssid')
                pw = params.get('password')
                hidden = params.get('hidden') == 'on'
                lat = params.get('latitude')
                lon = params.get('longitude')

                if ssid and pw:
                    save_env(ssid, pw, hidden, lat, lon)
                    cl.send(b'HTTP/1.1 200 OK\r\n\r\n<h2>OK</h2><p>Guardado. Reinicia ESP8266</p>')
                    cl.close()
                    s.close()
                    return
                else:
                    cl.send(b'HTTP/1.1 400\r\n\r\nError')
            else:
                # GET: formulario HTML minimalista
                html = (
                    'HTTP/1.1 200 OK\r\nContent-Type:text/html\r\n\r\n'
                    '<html><body style="font-family:sans-serif;padding:2em">'
                    '<h2>Libre-Gallinero WiFi</h2>'
                    '<form method="POST">'
                    '<b>Red:</b><br>'
                )

                for i, ssid in enumerate(ssids):
                    html += f'<input type="radio" name="ssid" value="{ssid}" id="s{i}"><label for="s{i}">{ssid}</label><br>'

                html += (
                    '<br><b>Password:</b><br>'
                    '<input name="password" type="password" required style="width:100%;padding:0.5em"><br><br>'
                    '<input type="checkbox" name="hidden"><label>Red oculta</label><br><br>'
                    '<b>Ubicación (opcional):</b><br>'
                    '<input name="latitude" placeholder="Lat -31.4167" style="width:100%;padding:0.5em"><br>'
                    '<input name="longitude" placeholder="Lon -64.1833" style="width:100%;padding:0.5em"><br><br>'
                    '<input type="submit" value="Guardar" style="padding:0.7em 2em">'
                    '</form></body></html>'
                )

                cl.send(html.encode('utf-8'))

            cl.close()
        except Exception as e:
            print('[main] HTTP err:', e)
            try:
                cl.close()
            except:
                pass

def start_hotspot(cfg):
    """Crea hotspot y servidor config"""
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
    print("[main] HTTP Config: http://", ip, sep='')
    print("[main] WebREPL: ws://", ip, ":8266", sep='')
    print("[main] (WebREPL ya iniciado por boot.py)")
    gc.collect()

    ssids = scan_networks()
    hotspot_server(ssids)

# === WIFI + NTP ===
def connect_wifi(cfg):
    """Conecta WiFi"""
    print('[main] Conectando WiFi...')
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        ssid = cfg['WIFI_SSID']
        pw = cfg['WIFI_PASSWORD']
        hidden = cfg['WIFI_HIDDEN'].lower() == 'true'

        try:
            if hidden:
                wlan.connect(ssid, pw, -1)
            else:
                wlan.connect(ssid, pw)
        except TypeError:
            wlan.connect(ssid, pw)

        timeout = 0
        while not wlan.isconnected() and timeout < 15:
            time.sleep(1)
            timeout += 1

    if wlan.isconnected():
        print('[main] WiFi OK:', wlan.ifconfig()[0])
        return True

    print('[main] WiFi FAIL')
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

def get_local_time(cfg):
    """Hora local ajustada por zona"""
    tm = time.localtime()
    lon = float(cfg.get('LONGITUDE', -60))
    tz = int(round(lon / 15))
    hour = (tm[3] + tz) % 24
    return tm[0], tm[1], tm[2], hour, tm[4]

# === CONTROL RELAYS ===
def control_ponedoras(cfg):
    """Control relay ponedoras (solar)"""
    year, month, day, hour, minute = get_local_time(cfg)
    lat = float(cfg.get('LATITUDE', -32.5))
    lon = float(cfg.get('LONGITUDE', -60))

    sunrise_summer, sunset_summer = calc_sun_times(year, 12, 21, lat, lon)
    sunrise_today, sunset_today = calc_sun_times(year, month, day, lat, lon)

    now_min = hour * 60 + minute
    sunrise_summer_min = sunrise_summer[0] * 60 + sunrise_summer[1]
    sunrise_today_min = sunrise_today[0] * 60 + sunrise_today[1]
    sunset_today_min = sunset_today[0] * 60 + sunset_today[1]
    sunset_summer_min = sunset_summer[0] * 60 + sunset_summer[1]

    estado = relay_ponedoras_state(now_min, sunrise_summer_min, sunrise_today_min, sunset_today_min, sunset_summer_min)
    relay1.value(estado)
    print(f'[R1] now={now_min}, estado={estado}')

def control_pollitos():
    """Control relay pollitos (temperatura)"""
    try:
        dht_sensor.measure()
        temp = dht_sensor.temperature()
        estado = relay_pollitos_state(temp)
        relay2.value(estado)
        print(f'[R2] temp={temp}°C, estado={estado}')
    except Exception as e:
        print('[R2] DHT error:', e)

# === MAIN LOOP ===
def main():
    print('\n=== main.py ===')
    cfg = load_config()
    print('[main] Config:', cfg.get('WIFI_SSID'))

    if not connect_wifi(cfg):
        print('[main] Iniciando hotspot...')
        start_hotspot(cfg)
        return

    if not sync_ntp():
        print('[main] Sin NTP, reloj puede estar mal')

    print('[main] Loop principal...')
    while True:
        control_ponedoras(cfg)
        control_pollitos()
        time.sleep(30)

if __name__ == "__main__":
    main()
