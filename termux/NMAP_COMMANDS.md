# 🔍 Comandos nmap para encontrar ESP8266 en Termux

## ⚠️ Por qué el scanner Python falla en Termux

El scanner Python (`webrepl_client.py:scan_active_hosts`) **NUNCA detectó la ESP8266 en Termux** por:

### 1️⃣ **Timeout muy corto (0.5s)**
- WiFi móvil tiene mayor latencia que PC
- Android introduce delays en networking
- ESP8266 puede tardar más en responder

### 2️⃣ **Threading limitado**
- Python crea 100 threads concurrentes
- Android throttle/mata threads agresivamente
- Límites del sistema en apps sin root

### 3️⃣ **Permisos de red restringidos (Android 10+)**
- Escaneos masivos bloqueados por sistema
- WiFi discovery restringido sin permisos especiales
- Termux no tiene visibilidad completa de la red

### 4️⃣ **Socket timeouts inconsistentes**
- `sock.connect_ex()` puede fallar silenciosamente
- Android scheduler introduce variabilidad
- Sin control fino de timeouts

---

## ✅ Solución: nmap

**nmap** resuelve todos estos problemas:
- ⚡ **10x más rápido** (30-60s vs 2-5 min)
- 🎯 **Mayor precisión** (optimizado para escaneos)
- ✅ **Detecta vendor Espressif** por MAC (con root)
- 📦 **Sin restricciones** de permisos Android
- 🔧 **Configuración flexible** de timeouts y threads

---

## Instalación en Termux

```bash
pkg install nmap
```

---

## 🎯 Comandos directos nmap

### 1️⃣ Escaneo básico puerto 8266 (RECOMENDADO)

```bash
# Detectar IP local
LOCAL_IP=$(ip -4 addr show wlan0 | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | head -1)
NETWORK=$(echo "$LOCAL_IP" | cut -d. -f1-3).0/24

# Escaneo rápido
nmap -p8266 --open -T4 -n --host-timeout 5s $NETWORK
```

**Explicación:**
- `-p8266`: Solo escanea puerto WebREPL
- `--open`: Solo muestra puertos abiertos
- `-T4`: Timing agresivo (rápido)
- `-n`: Sin resolución DNS (más rápido en móvil)
- `--host-timeout 5s`: Timeout de 5s por host

**Tiempo estimado:** 30-60 segundos para red /24 (254 hosts)

---

### 2️⃣ Escaneo con detección de vendor Espressif (requiere root)

```bash
# Requiere Termux con root o termux-root-packages
sudo nmap -p8266 --open -T4 $NETWORK
```

**Output esperado:**
```
Nmap scan report for 192.168.1.123
Host is up (0.045s latency).
PORT     STATE SERVICE
8266/tcp open  unknown
MAC Address: AA:BB:CC:DD:EE:FF (Espressif Inc.)
```

---

### 3️⃣ Escaneo en rango específico

```bash
# Si conoces tu red
nmap -p8266 --open -T4 -n 192.168.1.0/24

# Solo un subconjunto
nmap -p8266 --open -T4 -n 192.168.1.100-150
```

---

### 4️⃣ Escaneo con detección de servicio WebSocket

```bash
# Intenta detectar el servicio WebSocket/WebREPL
nmap -p8266 --open -T4 -sV $NETWORK
```

**Nota:** `-sV` (service version detection) puede tardar más pero da más info.

---

### 5️⃣ Escaneo ultra-rápido (menos preciso)

```bash
# Escaneo SYN rápido (requiere root en algunos casos)
nmap -p8266 --open -T5 -n --min-rate 1000 $NETWORK
```

**Advertencia:** `-T5` es muy agresivo, puede perder hosts en WiFi inestable.

---

## 📋 Scripts automatizados

### Script bash (incluido en el proyecto)

```bash
# Usar el script automático
bash termux/find_esp.sh

# Output:
# 🐔 Buscador ESP8266 con nmap
# 📡 IP local: 192.168.1.50
# 📡 Rango: 192.168.1.0/24
# ✅ Dispositivos con puerto 8266 abierto:
#    • 192.168.1.123
```

### Script Python (más completo)

```bash
# Escaneo automático con verificación WebREPL
python3 tools/find_esp8266.py

# Escaneo en rango específico
python3 tools/find_esp8266.py 192.168.1.0/24

# Solo probar WebREPL (sin nmap)
python3 tools/find_esp8266.py --test-only 192.168.1.123
```

---

## 🔧 Troubleshooting en Termux

### Problema: "Permission denied"

**Solución:** Algunos comandos nmap requieren permisos especiales en Android.

```bash
# Usar comandos sin root:
nmap -p8266 --open -T4 -n $NETWORK  # ✅ Funciona sin root

# Evitar:
nmap -sS ...  # ❌ Requiere root (SYN scan)
nmap -O ...   # ❌ Requiere root (OS detection)
```

### Problema: "nmap: command not found"

```bash
pkg update
pkg install nmap
```

### Problema: Escaneo muy lento

```bash
# Reducir rango:
nmap -p8266 --open -T4 -n 192.168.1.100-200  # Solo 100 hosts

# O aumentar timeout:
nmap -p8266 --open -T5 --max-retries 1 $NETWORK
```

### Problema: No encuentra la ESP8266

**Verificaciones:**

1. **ESP8266 en la misma red:**
   ```bash
   # Ver dispositivos conectados en tu router (si tienes acceso web)
   # O usar arp-scan (si disponible):
   arp-scan --localnet
   ```

2. **Puerto 8266 realmente abierto:**
   ```bash
   # Probar conexión TCP directa
   nc -zv 192.168.1.123 8266
   # O
   telnet 192.168.1.123 8266
   ```

3. **WebREPL activo en ESP8266:**
   ```python
   # Conectar por USB y verificar
   import webrepl
   webrepl.start()
   ```

---

## 💡 Workflow recomendado en Termux

### Primera vez:

```bash
# 1. Escanear red con nmap
bash termux/find_esp.sh

# Output: 192.168.1.123 encontrado

# 2. Verificar WebREPL
python3 tools/find_esp8266.py --test-only 192.168.1.123

# 3. Deploy con IP específica
python3 tools/deploy_wifi.py gallinero 192.168.1.123
```

### Siguientes veces (con caché):

```bash
# Deploy directo (usa IP cacheada)
python3 tools/deploy_app.py gallinero
```

---

## 🎯 One-liner para Termux

```bash
# Detectar ESP8266 y guardar IP
ESP_IP=$(nmap -p8266 --open -T4 -n $(ip -4 addr show wlan0 | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | head -1 | cut -d. -f1-3).0/24 2>/dev/null | grep "Nmap scan report" | awk '{print $5}' | head -1) && echo "ESP8266: $ESP_IP" && python3 tools/deploy_wifi.py gallinero $ESP_IP
```

**Advertencia:** Este one-liner es conveniente pero asume que el primer dispositivo encontrado es tu ESP8266.

---

## 📊 Comparación: nmap vs Python scanner

| Característica | nmap | Python scanner |
|----------------|------|----------------|
| Velocidad | ⚡⚡⚡ Muy rápido (30-60s) | 🐌 Lento (2-5 min) |
| Detección vendor | ✅ Sí (con root) | ❌ No |
| Portabilidad | ⚠️ Requiere instalación | ✅ Built-in |
| Permisos Android | ⚠️ Algunos comandos limitados | ✅ Sin restricciones |
| Precisión | ⚡⚡⚡ Alta | ⚡⚡ Media |

**Recomendación:** Usar **nmap** en Termux siempre que sea posible.

---

## 🔐 Seguridad

**IMPORTANTE:** Estos escaneos son para **uso local en tu propia red**. Escanear redes ajenas sin permiso es ilegal.

Los comandos mostrados son **no invasivos** (solo verifican si un puerto está abierto, no intentan explotar vulnerabilidades).
