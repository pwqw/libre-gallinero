# hotspot.py
# Módulo para el hotspot de configuración WiFi en NodeMCU (MicroPython)

try:
    import network # type: ignore[import]
    import socket
    import ujson # type: ignore[import]
except ImportError:
    print("Error: Este script debe ejecutarse en un entorno MicroPython.")


AP_SSID = 'Gallinero-Setup'
AP_PASSWORD = 'gallinas123'  # Debe tener al menos 8 caracteres
AP_IP = '192.168.4.1'
AP_NETMASK = '255.255.255.0'
AP_GATEWAY = '192.168.4.1'
AP_DNS = '192.168.4.1'

CONFIG_FILE = 'wifi_config.json'


def start_ap():
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid=AP_SSID, password=AP_PASSWORD, authmode=3)  # WPA2
    try:
        ap.ifconfig((AP_IP, AP_NETMASK, AP_GATEWAY, AP_DNS))
    except Exception as e:
        print('Error configurando ifconfig:', e)
        ap.ifconfig(('192.168.4.1', '255.255.255.0', '192.168.4.1', '192.168.4.1'))
    return ap


def save_wifi_config(ssid, password):
    with open(CONFIG_FILE, 'w') as f:
        ujson.dump({'ssid': ssid, 'password': password}, f)


def load_wifi_config():
    try:
        with open(CONFIG_FILE, 'r') as f:
            return ujson.load(f)
    except Exception:
        return None


def run_config_server():
    # Escanear redes WiFi disponibles (5 segundos)
    sta_if = network.WLAN(network.STA_IF)
    sta_if.active(True)
    import time
    print('Escaneando redes WiFi...')
    scan_results = []
    t0 = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), t0) < 5000:
        try:
            scan_results = sta_if.scan()
            if scan_results:
                break
        except Exception as e:
            print('Error escaneando WiFi:', e)
        time.sleep(1)
    ssids = []
    for net in scan_results:
        ssid = net[0].decode('utf-8') if isinstance(net[0], bytes) else str(net[0])
        if ssid and ssid not in ssids:
            ssids.append(ssid)
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(1)
    print('Servidor de configuración corriendo en http://192.168.4.1/')
    while True:
        cl, addr = s.accept()
        try:
            req = cl.recv(1024)
            req = req.decode('utf-8')
            if 'POST /' in req:
                body = req.split('\r\n\r\n', 1)[1]
                params = ujson.loads(body)
                ssid = params.get('ssid')
                password = params.get('password')
                latitude = params.get('latitude')
                longitude = params.get('longitude')
                if ssid and password:
                    save_wifi_config(ssid, password)
                if latitude is not None and longitude is not None:
                    from config import save_location_config
                    save_location_config(float(latitude), float(longitude))
                response = 'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\nGuardado. Reinicie el dispositivo.'
            else:
                html = [
                    'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n',
                    '<html><head>',
                    '<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">',
                    '<style>body{font-family:sans-serif;padding:1em;background:#fff;}form{max-width:340px;margin:auto;}input,button{width:100%;font-size:1em;margin:0.5em 0;padding:0.7em;}fieldset{margin-bottom:1em;border-radius:6px;border:1px solid #ccc;padding:1em;}.ssid-list{margin-bottom:1em;}</style>',
                    '<script>function toggleManualSSID(){var o=document.getElementById("ssid_otro"),m=document.getElementById("manual_ssid");if(m)m.style.display=o&&o.checked?"block":"none";if(m)m.required=o&&o.checked;}</script>',
                    '</head><body>',
                    '<h2>Configurar WiFi y Ubicación</h2>',
                    '<form method="POST" action="/">',
                    '<fieldset><legend>WiFi</legend>',
                    '<div class="ssid-list"><b>Red WiFi:</b><br>'
                ]
                if ssids:
                    for i, ssid in enumerate(ssids):
                        html.append("<input type='radio' name='ssid_radio' value='{}' id='ssid_{}' onclick=\"document.getElementById('manual_ssid').style.display='none';document.getElementById('manual_ssid').required=false;\"><label for='ssid_{}'>{}</label><br>".format(ssid, i, i, ssid))
                    html.append("<input type='radio' name='ssid_radio' value='' id='ssid_otro' onclick='toggleManualSSID()'><label for='ssid_otro'>Otro (ingresar manualmente)</label><br>")
                    html.append("<input name='ssid' id='manual_ssid' type='text' placeholder='Nombre WiFi' style='display:none;'>")
                else:
                    html.append("<input name='ssid' id='manual_ssid' type='text' placeholder='Nombre WiFi' required>")
                html.append('</div>')
                html.append("Contraseña:<br><input name='password' type='password' required><br>")
                html.append('</fieldset>')
                html.append('<fieldset><legend>Ubicación (opcional)</legend>')
                html.append("Latitud:<br><input name='latitude' type='number' step='any'><br>")
                html.append("Longitud:<br><input name='longitude' type='number' step='any'><br>")
                html.append('</fieldset>')
                html.append("<input type='submit' value='Guardar'>")
                html.append('</form>')
                html.append('<script>document.querySelector("form").onsubmit=function(e){var r=document.getElementsByName("ssid_radio"),s="";if(r.length){for(var i=0;i<r.length;i++){if(r[i].checked)s=r[i].value;}if(!s){s=document.getElementById("manual_ssid").value;}}else{s=document.getElementById("manual_ssid").value;}var si=document.createElement("input");si.type="hidden";si.name="ssid";si.value=s;this.appendChild(si);return true;};</script>')
                html.append('</body></html>')
                response = ''.join(html)
            if isinstance(response, str):
                response = response.encode('utf-8')
            chunk_size = 128
            import time as _t
            for i in range(0, len(response), chunk_size):
                cl.send(response[i:i+chunk_size])
                _t.sleep_ms(10)
        except Exception as e:
            print('Error en la conexión:', e)
        finally:
            cl.close()


def hotspot_config_loop():
    ap = start_ap()
    run_config_server()
