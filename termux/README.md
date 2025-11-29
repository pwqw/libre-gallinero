# Desarrollo ESP8266 desde Android/Mac

Desarrollo MicroPython en ESP8266 usando WebREPL - 100% libre, sin root, sin cables.

## Solución: WebREPL MicroPython

Software 100% libre, sin root, sin USB después del setup inicial, funciona en Android/Mac.

---

## FASE 1: Setup Inicial (Una vez - Requiere PC/Mac)

### Hardware
- ESP8266 NodeMCU
- Cable USB
- PC/Mac (sin privilegios admin)

### Proceso

1. **Instalar esptool:**
   ```bash
   pip install esptool
   ```

2. **Descargar firmware MicroPython:**
   - Visita: https://micropython.org/download/ESP8266_GENERIC/
   - Descarga la última versión estable (ej: `ESP8266_GENERIC-20240602-v1.23.0.bin`)

3. **Flashear firmware en ESP8266:**
   ```bash
   # Borrar flash
   esptool.py --port /dev/ttyUSB0 erase_flash

   # Flashear MicroPython
   esptool.py --port /dev/ttyUSB0 --baud 460800 write_flash --flash_size=detect 0 ESP8266_GENERIC-*.bin
   ```

   En Mac el puerto suele ser `/dev/tty.usbserial-*` o `/dev/tty.wchusbserial*`

4. **Conectar por serial y configurar WebREPL:**
   ```bash
   # Usando screen (Mac/Linux)
   screen /dev/ttyUSB0 115200

   # O usando miniterm (Python)
   python -m serial.tools.miniterm /dev/ttyUSB0 115200 --rts 0 --dtr 0
   ```

5. **En el REPL de MicroPython, configurar WebREPL:**
   ```python
   >>> import webrepl_setup
   ```

   Sigue las instrucciones:
   - Enable WebREPL: `E` (Enable)
   - Set password: Elige una contraseña
   - Reiniciará automáticamente

6. **Conectar ESP8266 a WiFi:**
   ```python
   >>> import network
   >>> wlan = network.WLAN(network.STA_IF)
   >>> wlan.active(True)
   >>> wlan.connect('TU_SSID', 'TU_PASSWORD')

   # Esperar conexión (10-30 segundos)
   >>> wlan.isconnected()
   True

   # Obtener IP asignada
   >>> wlan.ifconfig()
   ('192.168.1.123', '255.255.255.0', '192.168.1.1', '8.8.8.8')
   ```

7. **Anotar la IP del ESP8266** (ej: `192.168.1.123`)

8. **Asegurar que WebREPL inicia automáticamente:**
   ```python
   # Crear boot.py con auto-inicio de WebREPL
   >>> with open('boot.py', 'w') as f:
   ...     f.write('import webrepl\nwebrepl.start()\n')
   ```

**Resultado:** ESP8266 con MicroPython + WebREPL activo en puerto 8266, conectado a WiFi.

---

## FASE 2: Uso desde Android/Mac (Sin cables)

### Método A: Interface Web (Más Simple - RECOMENDADO)

**Herramienta:** Navegador web (Chrome, Firefox, cualquiera)

**Proceso:**
1. Abrir en navegador: https://micropython.org/webrepl/
2. Conectar a: `ws://IP_ESP8266:8266` (ej: `ws://192.168.1.123:8266`)
3. Autenticar con el password configurado
4. Usar REPL directamente en el navegador
5. Subir archivos con botón **"Send a file"**

**Ventajas:**
- Cero instalación
- GUI amigable
- Funciona desde cualquier dispositivo con navegador
- Drag & drop de archivos
- REPL interactivo en tiempo real

---

### Método B: Script Python (Automatizado - RECOMENDADO)

**Herramienta:** Termux (Android) o Terminal (Mac)

**Dependencias:**
```bash
# En Termux o Mac
pip install websocket-client
```

**Configuración (solo primera vez):**
```bash
# Copiar template de configuración
cp .env.example .env

# Editar .env con tu editor favorito
nano .env  # o vim, vi, etc

# Configurar:
# - WEBREPL_IP: IP del ESP8266 (la verás en el boot)
# - WEBREPL_PASSWORD: Password configurado en webrepl_setup
# - WIFI_SSID y WIFI_PASSWORD (opcional, para generar wifi_config.json)
```

**Uso:**
```bash
# Desde Termux o Mac
python3 tools/deploy_wifi.py
```

El script automáticamente:
- Lee configuración desde `.env`
- Busca ESP8266 automáticamente si no hay IP configurada
- Sube todos los archivos de `src/`
- Copia `.env` al ESP8266
- Verifica que el deploy funcionó
- Ofrece reiniciar el ESP8266

**Ventajas:**
- Automatizable
- Scripteable
- No requiere navegador
- Integrable en workflows
- Deploy completo con un comando

---

### Método C: CLI Oficial (Directo)

**Herramienta:** `webrepl_cli.py` de MicroPython

**Proceso:**
1. Descargar webrepl_cli.py oficial:
   ```bash
   curl -O https://raw.githubusercontent.com/micropython/webrepl/master/webrepl_cli.py
   ```

2. Subir archivo:
   ```bash
   python webrepl_cli.py -p PASSWORD archivo.py IP_ESP8266:/archivo.py
   ```

**Ventajas:**
- Oficial de MicroPython
- Una línea de comando
- Sin código custom

---

## FASE 3: Workflow Diario

### Setup Inicial (Solo primera vez)
1. Copiar configuración: `cp .env.example .env`
2. Editar `.env` con IP del ESP8266 y credenciales
3. El ESP8266 muestra su IP al iniciar (desde boot.py)

### Desarrollo
1. Editar código en Android (Termux/editor) o Mac
2. **Opción Simple:** Abrir WebREPL web, subir archivos manualmente
3. **Opción Automatizada (Recomendada):** Ejecutar `python3 tools/deploy_wifi.py`
4. Verificar en REPL web

### Debug
1. Abrir https://micropython.org/webrepl/ en navegador
2. Conectar a `ws://IP_ESP8266:8266`
3. Ejecutar comandos Python directamente en REPL
4. Ver output en tiempo real
5. Reiniciar si necesario: `import machine; machine.reset()`

### Uso de Shortcuts (Termux Widget)
Si instalaste Termux Widget, puedes usar los shortcuts:
- **Update Setup**: Actualiza el repositorio y dependencias
- **Abrir REPL**: Abre REPL interactivo del ESP8266
- **Ver Logs**: Lee logs del ESP8266 en tiempo real (NUEVO)
- **Limpiar ESP8266**: Limpia archivos del ESP8266 de forma interactiva
- **Deploy Blink**: Despliega app Blink (LED test) con caché de IP
- **Deploy Gallinero**: Despliega app Gallinero (producción) con caché de IP
- **Deploy Heladera**: Despliega app Heladera (experimental) con caché de IP

**Ventajas del caché de IPs:**
- Primera ejecución: escanea red buscando ESP8266 en puerto 8266 (~10-30s)
- Siguientes ejecuciones: usa IP cacheada (~2s)
- Cada app tiene su propia IP cacheada (útil si tienes múltiples ESP8266)
- Cache válido por 7 días

---

## Arquitectura

```
┌─────────────────────────────────┐
│  Android/Mac/Cualquier OS       │
│                                  │
│  ┌────────────────────────┐    │
│  │  Navegador Web         │    │
│  │  o                     │    │
│  │  Termux/Terminal       │    │
│  │  + Python script       │    │
│  └───────┬────────────────┘    │
│          │                      │
└──────────┼──────────────────────┘
           │
           │ WebSocket
           │ ws://IP:8266
           │ (WiFi)
           │
┌──────────▼──────────────┐
│   ESP8266 NodeMCU       │
│   - MicroPython         │
│   - WebREPL enabled     │
│   - libre-gallinero     │
└─────────────────────────┘
```

---

## Comparativa de Métodos

| Método | Simplicidad | Automatización | Requiere |
|--------|-------------|----------------|----------|
| Web GUI | ⭐⭐⭐⭐⭐ | ⭐ | Navegador |
| Script Python | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Python + websocket-client |
| webrepl_cli.py | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Python |

---

## Ventajas

- Cero USB después del setup inicial
- 100% software libre (MicroPython, WebREPL)
- Sin root ni privilegios admin
- Funciona en Android (Termux/Navegador)
- Funciona en Mac/Linux sin privilegios
- Simple - Interface web lista para usar
- Scripteable - Deploy automático si lo prefieres
- Wireless - Todo por WiFi

---

## Limitaciones

- Requiere PC/Mac para flasheo inicial (limitación técnica de Android sin root)
- ESP8266 y dispositivo deben estar en la misma red WiFi
- WebREPL requiere password (seguridad básica)

---

## Troubleshooting

| Problema | Solución |
|----------|----------|
| No puedo conectar a WebREPL | Verificar que ESP8266 esté en la misma red WiFi, ping a la IP |
| "Connection refused" | WebREPL no está activo, ejecutar `import webrepl; webrepl.start()` desde serial |
| Password incorrecto | Reconectar por serial y ejecutar `webrepl_setup` de nuevo |
| No responde después de subir archivo | Verificar sintaxis del archivo, revisar REPL por errores |

---

## Referencias

- [MicroPython WebREPL](https://docs.micropython.org/en/latest/esp8266/tutorial/repl.html#webrepl-a-prompt-over-wifi)
- [WebREPL Client Web](https://micropython.org/webrepl/)
- [MicroPython ESP8266](https://docs.micropython.org/en/latest/esp8266/tutorial/intro.html)
