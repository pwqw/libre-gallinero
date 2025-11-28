# PC/Mac/Linux - Desarrollo ESP8266

> **Nota:** Todas las herramientas principales están en `tools/` y funcionan cross-platform.
> Este directorio solo contiene wrappers opcionales.

## Quick Start

```bash
# 1. Setup inicial (USB, solo primera vez)
python3 tools/setup_initial.py

# 2. Deploy apps (WiFi, desarrollo diario)
python3 tools/deploy_wifi.py gallinero
python3 tools/deploy_app.py gallinero   # Con caché de IP (más rápido)
python3 tools/deploy_usb.py gallinero   # USB (alternativa)

# 3. Utilidades
python3 tools/open_repl.py              # REPL interactivo
python3 tools/clean_esp8266.py          # Limpiar archivos viejos
```

## Herramientas principales (en `tools/`)

| Script | Descripción | Uso |
|--------|-------------|-----|
| `setup_initial.py` | Setup inicial vía USB | Primera vez solamente |
| `deploy_wifi.py` | Deploy vía WiFi | Desarrollo diario |
| `deploy_app.py` | Deploy con caché de IP | Desarrollo móvil/rápido |
| `deploy_usb.py` | Deploy vía USB | Alternativa rápida |
| `open_repl.py` | REPL interactivo | Debug/testing |
| `clean_esp8266.py` | Limpieza de archivos | Mantenimiento |

## Wrappers en este directorio (opcionales)

- `deploy.sh` → Llama a `tools/deploy_usb.py`
- `setup_webrepl.py` → Llama a `tools/setup_initial.py`

## Configuración

```bash
# Copiar y editar .env
cp .env.example .env
nano .env
```

Configuración mínima en `.env`:
```bash
WIFI_SSID=tu_wifi
WIFI_PASSWORD=tu_password
WEBREPL_PASSWORD=admin
```

Opcional (auto-detectado si se omite):
```bash
WEBREPL_IP=192.168.1.123    # Auto-descubierto si no existe
```

## Requisitos

```bash
# Instalar dependencias
pip install -r requirements.txt

# Flashear MicroPython (primera vez)
esptool.py --port /dev/ttyUSB0 erase_flash
esptool.py --port /dev/ttyUSB0 write_flash 0 ESP8266_GENERIC-*.bin
```

## Troubleshooting

**Puerto serie no detectado (Linux):**
```bash
sudo usermod -a -G dialout $USER
# Reiniciar sesión
```

**WebREPL no conecta:**
```bash
# Verificar IP del ESP8266 vía serial
>>> import network
>>> wlan = network.WLAN(network.STA_IF)
>>> wlan.ifconfig()
```

**Ver más:** [../README.md](../README.md) | [Documentación completa](../docs/)
