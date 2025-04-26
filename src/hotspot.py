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
                response = 'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n'
                response += """
                <html>
                <head>
                <meta charset='utf-8'>
                <meta name='viewport' content='width=device-width, initial-scale=1'>
                <style>
                body { font-family: sans-serif; padding: 1em; background: #fff; }
                form { max-width: 320px; margin: auto; }
                input, button {
                  width: 100%;
                  font-size: 1em;
                  margin: 0.5em 0;
                  padding: 0.7em;
                }
                </style>
                </head>
                <body>
                <h2>Configurar WiFi y Ubicación</h2>
                <form method='POST' action='/'>
                Nombre WiFi:<br><input name='ssid' type='text' required><br>
                Contraseña:<br><input name='password' type='password' required><br>
                Latitud:<br><input name='latitude' type='number' step='any' required><br>
                Longitud:<br><input name='longitude' type='number' step='any' required><br>
                <input type='submit' value='Guardar'>
                </form>
                </body></html>
                """
            cl.send(response)
        except Exception as e:
            print('Error en la conexión:', e)
        finally:
            cl.close()


def hotspot_config_loop():
    ap = start_ap()
    run_config_server()
