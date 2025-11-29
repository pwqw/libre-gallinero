# 🎯 FOCO DEL PROYECTO

**Framework de deployment vía WebREPL para ESP8266 con MicroPython.**

NO es un proyecto de automatización. Es un **sistema de deployment** que gestiona múltiples ESP8266 flasheados con MicroPython, desplegando diferentes apps en cada dispositivo vía WiFi usando protocolo WebREPL.

---

## 1️⃣ Framework de Deployment WebREPL

### Concepto

Herramientas Python 3.9 (PC/Mac/Linux/Termux) para:
- **Setup inicial** (USB, 1 vez): Flashear ESP8266 con sistema base completo
- **Deploy apps** (WiFi, repetible): Cambiar app en cada ESP8266
- **Multi-dispositivo**: Gestionar múltiples ESP8266, cada uno con su app

### Estructura

```
tools/                      # Deployment tools (Python 3.9)
├── setup_initial.py       # Setup USB (1 vez)
├── deploy_wifi.py         # Deploy WebREPL
├── deploy_app.py          # Deploy con IP cache (Termux)
├── deploy_usb.py          # Deploy USB
└── common/
    ├── webrepl_client.py  # WebREPL protocol (CRÍTICO)
    ├── ampy_utils.py      # USB utils
    └── network_scanner.py # Network scanner

src/                        # Código → ESP8266
├── boot.py                # Bootstrap (WDT 30s)
├── main.py                # Orchestrator (WDT 60s)
├── config.py, wifi.py, ntp.py, app_loader.py
└── blink/, gallinero/, heladera/  # Apps
```

### Flujo

**Primera vez (USB):**
```bash
python3 tools/setup_initial.py
# Despliega ~20 archivos: boot, main, config, wifi, ntp, app_loader, .env, blink/
# LED parpadea automáticamente → sistema funcional
```

**Cambiar app (WiFi):**
```bash
python3 tools/deploy_wifi.py gallinero
python3 tools/deploy_wifi.py heladera
```

### Features
- Zero-config discovery (escaneo automático)
- IP caching (deploy ultra-rápido)
- WebREPL protocol binario oficial
- Multi-plataforma + optimizado Termux

---

## 2️⃣ Setup Inicial - Sistema Base Común

### Archivos base (TODOS los ESP8266)

```
boot.py              # WDT 30s, gc.collect
webrepl_cfg.py       # Password WebREPL
.env                 # Config WiFi, coords, app
main.py              # WDT 60s, WiFi, NTP, app_loader
config.py, wifi.py, ntp.py, app_loader.py
```

### `setup_initial.py` hace:
1. Configura WebREPL (password)
2. Copia sistema base
3. Despliega .env
4. Instala app blink

**Resultado:** ESP8266 100% funcional (WiFi + WebREPL + LED parpadea)

### Apps varían por dispositivo

```bash
python3 tools/deploy_wifi.py gallinero 192.168.1.10  # ESP8266 #1
python3 tools/deploy_wifi.py heladera 192.168.1.11   # ESP8266 #2
python3 tools/deploy_wifi.py blink 192.168.1.12      # ESP8266 #3
```

---

## 3️⃣ WebREPL - Protocolo Binario MicroPython 1.19

### CRÍTICO: WebREPL es el 100% del deployment

Usos: Setup remoto, deploy apps, debugging, OTA updates.
**USB solo para setup inicial.**

### Protocolo Binario

Basado en [webrepl_cli.py](https://github.com/micropython/webrepl/blob/master/webrepl_cli.py) y [modwebrepl.c](https://github.com/micropython/micropython/blob/master/extmod/modwebrepl.c).

**Request (signature "WA"):**
```python
WEBREPL_REQ_S = "<2sBBQLH64s"
# WA + opcode(1=PUT/2=GET) + reserved(9B) + size(4B) + len(2B) + filename(64B)
```

**Response (signature "WB"):**
```python
# 2B signature "WB" + 2B status (0=ok)
```

### CRÍTICO: No mezclar protocolos

**Problema:** Mezclar `execute()` + `send_file()` → errores buffer WebSocket.

**Solución (implementada en webrepl_client.py):**
1. **NUNCA** `execute()` antes de `send_file()`
2. Limpiar buffer: `_clean_buffer_before_binary_transfer()`
3. WebREPL crea dirs automáticamente (NO `os.mkdir()`)
4. Enviar CTRL-C al conectar (interrumpe programa)

### Implementación Robusta

- Retry logic (10 intentos para "WB")
- Buffer cleaning (descarta residuos REPL)
- Type handling (str→bytes MicroPython 1.19)
- Auto-reconexión WebSocket
- Timeout largo (10s WiFi lento)

### Limitaciones
- Max 8KB por archivo (ESP8266 RAM limitada)
- Filename max 64B
- Single-threaded (bloquea app)
- WiFi required

---

## 4️⃣ MicroPython ESP8266 - Single Process

### CRÍTICO: NO hay threads reales

- **Single process:** WiFi + WebREPL + App comparten hilo
- **Blocking I/O:** Todo secuencial
- `_thread` opcional y muy limitado

### Implicaciones

**WiFi + WebREPL + App secuencial:**
```python
# main.py
wifi.connect_wifi()    # Bloquea
ntp.sync_ntp()         # Bloquea
app_loader.load_app()  # Bloquea en loop
```

**WebREPL solo funciona si app NO bloquea:**
- `while True` sin `sleep()` → WebREPL muere
- Apps DEBEN tener sleeps regulares

**WiFi monitoring (opcional):**
```python
try:
    import _thread
    _thread.start_new_thread(wifi.monitor_wifi, (30,))
except: pass  # Sistema funciona sin threading
```

### MicroPython Internals

**WiFi:**
```python
import network
wlan = network.WLAN(network.STA_IF)  # Station
ap = network.WLAN(network.AP_IF)     # Hotspot
```

**WebREPL:**
```python
import webrepl
webrepl.start()  # Puerto 8266
```

**WDT:**
```python
from machine import WDT
wdt = WDT(timeout=30000)
wdt.feed()
```

**Hotspot fallback:**
```python
if not wlan.isconnected():
    ap.active(True)
    ap.config(essid=SSID, password=PWD)
```

**Memory:**
```python
import gc
gc.collect()
gc.mem_free()
```

Estrategia: `gc.collect()` después de cada operación mayor, importar módulos on-demand, archivos <8KB.

---

## 5️⃣ Entorno de Desarrollo

### Python 3.9 venv

```bash
python3.9 -m venv env
source env/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

**requirements.txt:** ampy, esptool, dotenv, pytest, pytest-timeout, pyserial, websocket-client

### pytest

Mock MicroPython modules:
```python
from unittest.mock import MagicMock, patch
mocks = {'machine': MagicMock(), '_thread': MagicMock(), ...}
with patch.dict('sys.modules', mocks):
    import main
```

Ejecutar: `pytest`, `pytest tests/test_main.py -v`

### Termux (Android)

**Setup:**
```bash
pkg install python git
git clone <repo>
python -m venv env && source env/bin/activate
pip install -r requirements.txt
```

**Widgets:** Scripts en `~/.shortcuts/` → Termux:Widget app

**Ventajas:** Deploy desde móvil, debugging in-situ, menor latencia WiFi

### PC Development

```bash
./pc/deploy.sh gallinero           # → tools/deploy_usb.py
python3 tools/open_repl.py         # REPL
screen /dev/ttyUSB0 115200         # Monitor serial
```

---

## 6️⃣ Detalles Implementación

### Boot Sequence
```
Power → boot.py (WDT 30s) → main.py (WDT 60s, WiFi, NTP) → app (loop con sleep)
```

### Config (.env)

Prioridad: `.env` → `.env.example` → hardcoded defaults

```bash
WIFI_SSID="libre gallinero"
WIFI_PASSWORD="huevos1"
WEBREPL_IP=192.168.1.123
WEBREPL_PASSWORD=admin
LATITUDE=-31.4167
LONGITUDE=-64.1833
APP=blink  # gallinero, heladera
```

### Network Discovery

**Fase 1:** Port scan toda la red /24 (puerto 8266, max 100 threads)
**Fase 2:** Test WebREPL secuencial
**Smart:** IP cache → .env → scan → 192.168.4.1 fallback

### App Structure

```
src/app_name/
├── __init__.py  # from .main import run
└── main.py      # def run(cfg): ...
```

Deploy: `python3 tools/deploy_wifi.py <app_name> [ip]`

### Logging Pattern

```python
import sys
def log(msg):
    print(f"[module] {msg}")
    if hasattr(sys.stdout, 'flush'): sys.stdout.flush()
```

### Common Gotchas

1. Setup tarda 30-60s (normal, ~20 archivos USB)
2. "Respuesta corta" → mezclar execute()/send_file()
3. Deploy falla → buffer sucio
4. WebREPL no responde → app sin sleep()
5. WDT timeout → operación larga sin feed()
6. OutOfMemory → archivo >8KB o no gc.collect()
7. Import errors → orden upload (__init__.py primero)
8. .env no refleja → archivo cacheado ESP8266

---

## Commands

**IMPORTANTE:** Todos los comandos requieren venv activado:
```bash
source env/bin/activate  # Activar venv PRIMERO
```

Luego ejecutar:
```bash
# Dev
pytest

# Setup inicial (USB, 1 vez)
python tools/setup_initial.py

# Deploy apps (WiFi)
python tools/deploy_wifi.py gallinero [ip]
python tools/deploy_app.py heladera      # Con cache

# Deploy USB
python tools/deploy_usb.py gallinero

# Utils
python tools/clean_esp8266.py
python tools/open_repl.py
```

---

## Para Claude: Prioridades

1. **MÁXIMA**: Protocolo WebREPL
   - NUNCA mezclar execute()/send_file()
   - SIEMPRE limpiar buffer
   - Confiar en WebREPL para dirs

2. **ALTA**: MicroPython compat
   - Single process (no threading)
   - gc.collect() frecuente
   - Archivos <8KB

3. **MEDIA**: Deployment
   - Tools rápidos/confiables
   - Network discovery robusto
   - IP caching mobile

4. **Testing**: Mock MicroPython (machine, _thread, network, gc)

5. **Flow**: Setup inicial (USB, 1 vez) → Deploy apps (WiFi, repetible)

**NUNCA asumir que es proyecto de automatización.** Es framework de deployment.
