# 🖥️ Desarrollo desde PC (Windows/Mac/Linux)

> Scripts para desarrollo y deployment en ESP8266

---

## 🎯 Quick Start

### Flujo Completo (3 pasos)

```bash
# 1️⃣ Setup inicial (USB, solo primera vez)
python3 tools/setup_initial.py
# ↳ Copia boot.py completo, webrepl_cfg.py, .env
# ↳ Abre monitor serial para ver bootstrapping

# 2️⃣ Reinicia ESP8266 y observa el boot

# 3️⃣ Deploy sin cables (WiFi, todas las veces)
python3 tools/deploy_wifi.py
# ↳ Sube archivos vía WebREPL
# ↳ Sin USB, solo WiFi
```

---

## 📊 Comparativa de Scripts

| Script | Conexión | Uso | Velocidad | Cuándo Usarlo |
|--------|----------|-----|-----------|---------------|
| `tools/setup_initial.py` | USB | Setup inicial | ⭐⭐⭐⭐ | Primera vez |
| `tools/deploy_wifi.py` | WiFi | Deploy remoto | ⭐⭐⭐ | Desarrollo diario |
| `tools/deploy_usb.py` | USB | Deploy USB | ⭐⭐⭐⭐ | Alternativa rápida |

---

## 🔧 Scripts Detallados

### `tools/setup_initial.py` - Setup Inicial

**🎯 Propósito**: Instalar boot.py completo y configurar WebREPL

**Características**:
- ✅ Copia `boot.py` completo
- ✅ Configura `webrepl_cfg.py` con password
- ✅ Copia `.env` si existe en el repositorio
- ✅ Abre monitor serial **BLOCKING** para observar boot
- ✅ Detección automática de puerto serie

**Uso**:
```bash
python3 tools/setup_initial.py
```

**Flujo**:
```
[1/4] Detectar puerto serie
[2/4] Copiar webrepl_cfg.py
[3/4] Copiar boot.py completo ⭐
[4/4] Copiar .env (si existe)

✅ Setup completado!
📡 Abriendo monitor serial...
   ↓
[Usuario reinicia ESP8266]
   ↓
[Observa bootstrapping en tiempo real]
   ↓
boot.py → WiFi → WebREPL ✅
```

**Después del setup**:
- ESP8266 tiene boot.py completo
- WebREPL activo en puerto 8266
- Ya no necesitas USB para deploy

---

### `tools/deploy_wifi.py` - Deploy sin Cables

**🎯 Propósito**: Subir código vía WiFi (sin USB)

**Características**:
- ✅ Deploy vía WebREPL (WiFi)
- ✅ Busca ESP8266 automáticamente si no hay IP
- ✅ Sube todos los archivos de `src/` automáticamente
- ✅ Copia `.env` automáticamente
- ✅ Verificación post-deploy
- ✅ Sin necesidad de USB

**Uso**:
```bash
# Opción 1: Con IP configurada en .env
python3 tools/deploy_wifi.py

# Opción 2: Sin .env (busca automáticamente)
python3 tools/deploy_wifi.py
# ↳ Escanea red local para encontrar ESP8266
```

**Archivos subidos**:
```
✅ boot.py       → Bootstrapping completo
✅ main.py       → Lógica principal
✅ solar.py      → Cálculos solares
✅ logic.py      → Control de relés
✅ .env          → Configuración (si existe)
```

**Flujo**:
```
Conectar WebREPL
    ↓
Autenticar con password
    ↓
Subir archivos uno por uno
    ↓
✅ Deploy completado
    ↓
[Reiniciar ESP8266 opcional]
```

---

### `tools/deploy_usb.py` - Deploy por USB

**🎯 Propósito**: Alternativa rápida usando cable USB

**Características**:
- ✅ Más rápido que WebREPL (~10s vs ~30s)
- ✅ Requiere USB conectado
- ✅ Usa `ampy` (adafruit-ampy)
- ✅ Detecta puerto automáticamente
- ✅ Abre monitor serial opcionalmente

**Uso**:
```bash
python3 tools/deploy_usb.py
```

---

## ⚙️ Configuración

### Archivo `.env` (Opcional)

```bash
# WiFi del ESP8266
WIFI_SSID="tu_wifi"
WIFI_PASSWORD="tu_password"

# WebREPL
WEBREPL_IP=192.168.1.123      # IP del ESP8266
WEBREPL_PASSWORD=admin        # Password WebREPL
WEBREPL_PORT=8266             # Puerto (no cambiar)

# Puerto serial (autodetectado si se omite)
# SERIAL_PORT=/dev/ttyUSB0
```

**Si no existe `.env`**:
- `tools/setup_initial.py` detecta puerto automáticamente
- `tools/deploy_wifi.py` busca ESP8266 en la red local automáticamente

---

## 🔄 Flujos de Trabajo

### Primera Instalación

```
1. Flashear MicroPython en ESP8266 (esptool)
   ↓
2. python3 tools/setup_initial.py
   ↓
3. Reiniciar ESP8266
   ↓
4. Observar bootstrapping en monitor serial
   ↓
5. WiFi conecta → WebREPL activo ✅
   ↓
6. Anotar IP del ESP8266
   ↓
7. python3 tools/deploy_wifi.py (deploy remoto)
```

### Desarrollo Diario

```
Editar código localmente
    ↓
python3 tools/deploy_wifi.py
    ↓
Reiniciar ESP8266 (opcional)
    ↓
Verificar funcionamiento
    ↓
Repetir 🔄
```

### Debugging

Usa WebREPL web (https://micropython.org/webrepl/):
```
Conectar a ws://<IP>:8266
    ↓
Ejecutar comandos interactivos
    ↓
>>> import main
>>> import machine
>>> machine.reset()
    ↓
Verificar logs
```

---

## 🛠️ Requisitos Previos

### 1. Python y Entorno Virtual

```bash
# Crear entorno virtual
python3 -m venv env

# Activar
source env/bin/activate        # Mac/Linux
env\Scripts\activate           # Windows
```

### 2. Instalar Dependencias

```bash
pip install -r requirements.txt
```

**Dependencias incluidas**:
- `adafruit-ampy` - Comunicación USB Serial
- `pyserial` - Puerto serie
- `websocket-client` - WebREPL
- `esptool` - Flashear firmware

### 3. MicroPython en ESP8266

```bash
# Descargar firmware
wget https://micropython.org/resources/firmware/ESP8266_GENERIC-20231005-v1.21.0.bin

# Flashear
esptool.py --port /dev/ttyUSB0 erase_flash
esptool.py --port /dev/ttyUSB0 write_flash --flash_size=detect 0 ESP8266_GENERIC-*.bin
```

---

## 🐛 Troubleshooting

### No se detecta puerto serie

**Mac**:
```bash
ls /dev/tty.*
# Busca: /dev/tty.usbserial-* o /dev/tty.wchusbserial*
```

**Linux**:
```bash
# Agregar usuario al grupo dialout
sudo usermod -a -G dialout $USER
# Luego reinicia sesión

# Listar puertos
ls /dev/ttyUSB* /dev/ttyACM*
```

**Windows**:
- Administrador de dispositivos
- Sección "Puertos (COM y LPT)"
- Anota el puerto COM

---

### Error "ampy no encontrado"

```bash
pip install adafruit-ampy pyserial
```

---

### Error conectando WebREPL

1. **Verifica WiFi**:
   ```bash
   # En REPL serial
   >>> import network
   >>> wlan = network.WLAN(network.STA_IF)
   >>> wlan.isconnected()
   # Debe retornar: True
   >>> wlan.ifconfig()
   # Anota la IP
   ```

2. **Verifica WebREPL**:
   ```bash
   >>> import webrepl
   >>> webrepl.start()
   ```

3. **Verifica IP en .env**:
   ```bash
   WEBREPL_IP=192.168.1.XXX  # IP correcta
   ```

4. **Verifica red**:
   - PC y ESP8266 en la misma red WiFi
   - Firewall no bloquea puerto 8266

---

### Error "Permission denied" (Linux)

```bash
# Agregar usuario al grupo dialout
sudo usermod -a -G dialout $USER

# Cerrar sesión y volver a iniciar
# O reiniciar
```

---

## 📚 Referencias

- [MicroPython WebREPL](https://docs.micropython.org/en/latest/esp8266/tutorial/repl.html#webrepl-a-prompt-over-wifi)
- [adafruit-ampy](https://github.com/adafruit/ampy)
- [esptool.py](https://github.com/espressif/esptool)
- [MicroPython ESP8266](https://docs.micropython.org/en/latest/esp8266/tutorial/intro.html)

---

## 💡 Tips

### Velocidad de Deploy

| Método | Tiempo aproximado |
|--------|-------------------|
| USB Serial (ampy) | ~10 segundos |
| WebREPL (WiFi) | ~30 segundos |

**Usa USB si**:
- Estás cerca del ESP8266
- Quieres deploy más rápido
- Tienes cable disponible

**Usa WebREPL si**:
- ESP8266 está lejos o inaccesible
- Desarrollas desde múltiples dispositivos
- Prefieres no usar cables

---

### Búsqueda Automática de ESP8266

`tools/deploy_wifi.py` escanea la red automáticamente si no hay `WEBREPL_IP` en `.env`:

**Estrategia:**
1. Prueba IP del `.env` (si existe)
2. Escanea red local basada en tu IP
3. Prueba `192.168.4.1` (hotspot fallback)

**Ventajas**:
- No necesitas conocer la IP
- Funciona después de reinicio con nueva IP
- Ideal para DHCP dinámico

**Desventajas**:
- Más lento (~10 segundos de escaneo)
- Puede encontrar el ESP8266 equivocado si hay múltiples

**Solución**: Configura `WEBREPL_IP` en `.env` para deploy más rápido

---

**¿Dudas?** Revisa el [README principal](../README.md) 📖
