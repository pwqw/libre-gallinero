# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Libre-Gallinero is a MicroPython-based automation system for chicken coop lighting and temperature control, targeting NodeMCU (ESP8266/ESP32) devices. The system simulates natural summer daylight patterns and maintains optimal temperatures for chicks using DHT11 sensors and relays.

## Commands

### Development Workflow

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run specific test file
pytest tests/test_main.py

# Run tests with timeout (recommended for MicroPython mock tests)
pytest tests/ -v
```

### Deployment

**Todas las herramientas están en `tools/` - funcionan en PC, Mac, Linux y Termux:**

```bash
# Initial setup (USB only, first time) - DEPLOYS COMPLETE SYSTEM
python3 tools/setup_initial.py
# After this, ESP8266 is fully functional with blink app
# LED will start blinking after reboot

# Deploy via WiFi (preferred for development)
python3 tools/deploy_wifi.py gallinero       # Deploy gallinero app
python3 tools/deploy_wifi.py heladera        # Deploy heladera app
python3 tools/deploy_wifi.py blink           # Re-deploy blink
python3 tools/deploy_wifi.py heladera 192.168.1.100  # Specify IP

# Deploy with IP caching (faster, recommended for Termux/mobile)
python3 tools/deploy_app.py gallinero        # Uses cached IP from previous deploy
python3 tools/deploy_app.py heladera         # First run scans network, then caches IP
python3 tools/deploy_app.py blink            # Each app has separate IP cache

# Deploy via USB (faster for local development)
python3 tools/deploy_usb.py gallinero        # Deploy gallinero via USB
python3 tools/deploy_usb.py blink            # Deploy blink via USB
python3 tools/deploy_usb.py heladera         # Deploy heladera via USB

# Utilities
python3 tools/clean_esp8266.py               # Interactive cleanup tool
python3 tools/open_repl.py                   # Open interactive REPL

# Platform-specific wrappers (optional, just call tools/ directly)
./pc/deploy.sh gallinero                     # PC wrapper → tools/deploy_usb.py
python3 pc/setup_webrepl.py                  # PC wrapper → tools/setup_initial.py

# Termux shortcuts (Android/mobile)
./termux/clean.sh                            # Cleanup tool shortcut
```

### Configuration

```bash
# Setup environment
cp .env.example .env
# Edit .env with your WiFi credentials, WebREPL password, and location coordinates
```

## Architecture

### Boot Sequence

The ESP8266 boot sequence follows this flow:

1. **boot.py** - Minimal bootstrap that initializes WDT (30s timeout) and memory cleanup
2. **main.py** - Main orchestrator that:
   - Initializes WDT (60s timeout if available)
   - Loads configuration from .env (falls back to .env.example or hardcoded defaults)
   - Connects to WiFi (with WDT feed callbacks during long operations)
   - Starts WiFi monitor thread (if _thread available)
   - Syncs time via NTP
   - Loads and runs the configured app (blink, gallinero, or heladera)

### Module System

The codebase is split into base modules and app-specific modules:

**Base Modules** (always deployed):
- `config.py` - Configuration loader that reads .env files
- `wifi.py` - WiFi connection manager with auto-reconnect and reset logic
- `ntp.py` - NTP time synchronization
- `app_loader.py` - Dynamic app loader that imports the configured app

**Apps** (deployed when specified, defaults to blink):
- `blink/` - Minimalist LED blink demo (default for initial setup)
  - `blink.py` - Simple LED blink loop
- `gallinero/` - Chicken coop automation (solar calculations, relay control)
  - `app.py` - Main control loop
  - `solar.py` - Sun time calculations
  - `logic.py` - Relay state logic
  - `hardware.py` - Hardware initialization
- `heladera/` - Reserved for future refrigerator app
  - `blink.py` - Currently contains LED blink demo (will evolve)

### Configuration Architecture

Configuration is loaded in this priority order:
1. `.env` file on ESP8266 (if exists)
2. `.env.example` file on ESP8266 (if exists)
3. Hardcoded defaults in `config.py`

The APP configuration variable determines which app module gets loaded by `app_loader.py`.
Each app must expose a `run(cfg)` function. Default is 'blink' for minimal setup.

### WiFi Management

The WiFi system (`wifi.py`) has sophisticated retry and reset logic:
- Scans for networks (unless hidden network)
- Retries connection with exponential backoff
- Resets WiFi interface every 3 failed attempts
- Validates IP addresses (warns if outside 192.168.0.x range)
- Monitors connection in background thread (30s interval)
- Auto-reconnects on disconnection

WebREPL is auto-started on successful connection for remote development.

### Watchdog Timer (WDT) Strategy

Two WDT instances are used:
- `boot.py`: 30s timeout for bootstrap phase
- `main.py`: 60s timeout for main operation, with feed callbacks during WiFi connection

The WDT is optional (gracefully handles absence) to support testing environments.

### Memory Management

The code uses aggressive memory management for MicroPython:
- `gc.collect()` called after major operations
- Modules imported only when needed
- Memory stats logged at startup
- Consistent `log()` functions with stdout.flush() for reliable serial output

## Testing

Tests use pytest with MicroPython mocking patterns:

- All MicroPython-specific modules (machine, _thread, ntptime, utime) are mocked
- Tests use `patch.dict('sys.modules', {...})` to inject mocks
- Timeouts are set globally via `pytest.ini` and per-test with `@pytest.mark.timeout(10)`
- Test files mirror the src/ structure

**Important testing patterns:**
- Mock `gc.mem_free()` to prevent AttributeError
- Mock `sys.print_exception` for MicroPython compatibility
- Clean up `sys.modules` between tests to ensure isolation
- Use `capsys.readouterr()` to capture and verify log output

## File Size Constraints

MicroPython has WebREPL file transfer limits:
- Maximum file size: 100KB (enforced in `common/webrepl_client.py`)
- Files exceeding this must be split or optimized
- Deploy scripts validate file sizes before upload

## Network Discovery

The deployment system uses an improved network scanner that:
- **Fase 1 (Port Scan)**: Escanea toda la red /24 detectando dispositivos con puerto 8266 abierto usando sockets
- **Fase 2 (WebREPL Test)**: Prueba WebREPL en cada dispositivo detectado secuencialmente
- **Sin límites artificiales**: Escanea todos los hosts (no solo 100)
- **Optimizado para Termux/móviles**: Limita threads concurrentes a 100 para no saturar
- **Verboso y claro**: Muestra progreso en ambas fases para debugging

Esto soluciona el problema donde apps externas de escaneo encontraban el ESP32 pero el deploy no.

## Deployment System

The deployment system supports three modes:

**Initial Setup** (`setup_initial.py` - USB, first time only):
- Configures WebREPL password
- Deploys complete working system (~20 files):
  - Bootstrap: boot.py, webrepl_cfg.py, .env
  - Base modules: main.py, config.py, wifi.py, ntp.py, app_loader.py
  - Default app: blink/ (minimal LED test)
- System is fully functional after this single command
- Takes ~30-60 seconds (one time only)
- LED starts blinking automatically after reboot
- Requires physical USB connection

**WiFi Mode** (`deploy_wifi.py`):
- Uses WebREPL protocol
- Auto-discovers ESP8266 IP or accepts explicit IP
- Deploys base modules + specified app
- Defaults to blink if no app specified
- Verifies deployment by importing main.py
- Optional post-deploy reboot
- Use to change apps after initial setup

**USB Mode** (`deploy_usb.py`):
- Uses ampy for file transfer
- Auto-detects serial ports (cross-platform)
- Faster than WiFi for local development
- Requires physical USB connection
- Use to change apps or update code

## Project-Specific Conventions

- All modules have a `log(msg)` function with `[module_name]` prefix
- All log functions call `sys.stdout.flush()` for reliable serial output
- Apps expose a single `run(cfg)` entry point in their `__init__.py`
- Error handling is defensive (try/except with continue operation)
- Network operations feed WDT to prevent timeout during long operations
- WiFi status codes are mapped to human-readable names for debugging

## Location & Solar Calculations

The gallinero app uses latitude/longitude from .env to calculate:
- Sunrise/sunset times for the current day
- Summer solstice (Dec 21 in southern hemisphere) daylight hours
- Relay timing to simulate summer light patterns year-round

Timezone is calculated from longitude (lon / 15).

## App Architecture

### Creating a New App

All apps must follow this structure:

```
src/your_app/
├── __init__.py          # Must export: from .main import run
└── main.py (or any)     # Must have: def run(cfg): ...
```

**Requirements:**
1. App directory in `src/`
2. `__init__.py` that exports `run` function
3. `run(cfg)` function that receives configuration dict
4. App name added to `app_loader.py` conditional

### Default Apps

- **blink**: Minimal LED blink demo for initial setup/testing
- **gallinero**: Production chicken coop automation
- **heladera**: Reserved for future refrigerator automation

Deploy with: `python3 tools/deploy_wifi.py <app_name>`

## WebREPL Protocol Details (MicroPython 1.19)

### Binary File Transfer Protocol

El protocolo WebREPL usa mensajes WebSocket binarios para transferir archivos. Implementación basada en:
- Código oficial: [webrepl_cli.py](https://github.com/micropython/webrepl/blob/master/webrepl_cli.py)
- Servidor C: [modwebrepl.c](https://github.com/micropython/micropython/blob/master/extmod/modwebrepl.c)

**Formato de Request (signature "WA"):**
```python
WEBREPL_REQ_S = "<2sBBQLH64s"  # Struct format
# - 2s: signature "WA" (client → server)
# - B: opcode (1=PUT_FILE, 2=GET_FILE)
# - B: reserved
# - Q: reserved (8 bytes)
# - L: file size (4 bytes)
# - H: filename length (2 bytes)
# - 64s: filename (max 64 bytes)
```

**Formato de Response (signature "WB"):**
```python
# 4 bytes totales:
# - 2 bytes: signature "WB" (server → client)
# - 2 bytes: status code (0 = éxito)
```

### CRÍTICO: No mezclar protocolos

**Problema:** Mezclar comandos de texto (`execute()`) con protocolo binario causa errores:
- "Respuesta WebREPL muy corta: 2 bytes"
- "a bytes-like object is required, not 'str'"
- Datos residuales en buffer WebSocket

**Solución:**
1. Usar SOLO comandos de texto (execute) O protocolo binario, nunca mezclados
2. Limpiar buffer WebSocket antes de transferencias binarias (`_clean_buffer_before_binary_transfer()`)
3. WebREPL crea directorios automáticamente cuando filename contiene "/" - NO usar `os.mkdir()` manualmente

### Implementación Robusta

La implementación en `tools/common/webrepl_client.py` incluye:
- **Retry logic**: Hasta 10 intentos para encontrar signature "WB"
- **Buffer cleaning**: Descarta datos residuales del REPL antes de transferencias
- **Type handling**: Convierte str→bytes para MicroPython 1.19 inconsistencies
- **Automatic directory creation**: Confía en WebREPL para crear subdirectorios

## Common Gotchas

- **First setup takes 30-60 seconds:** setup_initial.py deploys complete system (~20 files). This is normal and only happens once. LED should blink automatically when finished.
- **"Respuesta WebREPL muy corta"**: Causado por mezclar comandos de texto con protocolo binario. NUNCA usar `client.execute()` antes de `send_file()`. WebREPL crea directorios automáticamente.
- **Deploy falla en archivos de app**: Asegurar que buffer WebSocket está limpio antes de protocolo binario. La implementación actual limpia automáticamente.
- WDT timeout during WiFi connection on slow/hidden networks → Use wdt_callback parameter
- WebREPL not starting → Check IP address is valid and WiFi connected
- Import errors after deploy → Ensure __init__.py files are uploaded first
- Tests failing with module not found → Check sys.modules mocking
- .env changes not reflecting → File cached on ESP8266, redeploy or edit directly via WebREPL
