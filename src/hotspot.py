# hotspot.py
# Módulo para el hotspot de configuración WiFi en NodeMCU (MicroPython)

import network
import socket
import ujson
import machine

AP_SSID = 'Gallinero-Setup'
AP_PASSWORD = 'gallinas123'
AP_IP = '1.1.1.1'
AP_NETMASK = '255.255.255.0'
AP_GATEWAY = '1.1.1.1'
AP_DNS = '1.1.1.1'

CONFIG_FILE = 'wifi_config.json'


def start_ap():
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid=AP_SSID, password=AP_PASSWORD)
    try:
        ap.ifconfig((AP_IP, AP_NETMASK, AP_GATEWAY, AP_DNS))
    except Exception:
        ap.ifconfig(('192.168.0.1', '255.255.255.0', '192.168.0.1', '192.168.0.1'))
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
    s.bind(addr)
    s.listen(1)
    print('Servidor de configuración corriendo en http://1.1.1.1/')
    while True:
        cl, addr = s.accept()
        req = cl.recv(1024)
        req = req.decode('utf-8')
        if 'POST /' in req:
            body = req.split('\r\n\r\n', 1)[1]
            params = ujson.loads(body)
            ssid = params.get('ssid')
            password = params.get('password')
            if ssid and password:
                save_wifi_config(ssid, password)
                response = 'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\nGuardado. Reinicie el dispositivo.'
            else:
                response = 'HTTP/1.1 400 Bad Request\r\n\r\nFaltan datos.'
        else:
            response = 'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n'
            response += """
            <html><body>
            <h2>Configurar WiFi</h2>
            <form method='POST' action='/'>
            Nombre WiFi: <input name='ssid'><br>
            Contraseña: <input name='password' type='password'><br>
            <input type='submit' value='Guardar'>
            </form>
            </body></html>
            """
        cl.send(response)
        cl.close()


def hotspot_config_loop():
    ap = start_ap()
    run_config_server()
