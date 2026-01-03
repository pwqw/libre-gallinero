# Heladera - Refrigerator Automation

Control automático de heladera con ciclo temporizado y descanso nocturno.

## Funcionalidad

La app **heladera** controla una heladera mediante un relé normalmente cerrado (NC) que alterna ciclos de 30 minutos encendido/apagado durante el día, y descansa completamente durante la noche para evitar ruido.

**Características:**
- Ciclo: 30 min ON → 30 min OFF (solo de día)
- Horario activo: 07:00 - 00:00
- Horario de descanso: 00:00 - 07:00 (sin ruido nocturno)
- Requiere sincronización NTP para horario nocturno
- LED integrado indica estado de la aplicación

## Indicadores LED

| Estado LED | Significado |
|------------|-------------|
| 3 parpadeos rápidos al boot | Cargando estado desde flash |
| Encendido fijo | App funcional, heladera en ciclo normal |
| Apagado (durante ciclo) | Relé activado (heladera encendida) |
| Parpadeo 0.5s | Sin NTP (sin WiFi o sin Internet) - modo degradado |

## Hardware

```
 +---------------------------------------------------+
 |                                                   |
 |   NodeMCU ESP-12E (ESP8266)                       |
 |                                                   |
 |  [ ] = Pin usado                                  |
 |                                                   |
 |         [D1] (GPIO5)  <--- Relay IN (NC)          |
 |         [D2] (GPIO2)  <--- LED integrado          |
 |                                                   |
 |         [GND] --------+--- Relay GND              |
 |         [3V3] --------- Relay VCC                 |
 |                                                   |
 +---------------------------------------------------+

Pines usados:
  D1 (GPIO5)  -> Relay IN (Normally Closed)
  D2 (GPIO2)  -> LED integrado (status indicator)
  GND         -> Relay GND
  3V3         -> Relay VCC

⚠️ IMPORTANTE: Usar 3V3 (NO VIN/5V) para evitar leakage current
   El relay debe alimentarse con 3.3V para que el optoacoplador
   se apague correctamente cuando GPIO5 está en LOW (0V).
   Con 5V en VCC, el voltaje residual mantiene el relay activado.
```

## Arquitectura de Persistencia

La app mantiene el estado de los ciclos a través de reinicios y cortes de luz usando un archivo JSON en flash:

```
┌─────────────────────────────────────────────────────────────┐
│                      Heladera App                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Boot → load_state() → recover_state_after_boot()          │
│           │               │                                 │
│           │               ├─ Sin NTP: 15 min ON inicial    │
│           │               └─ Con NTP: calcular estado      │
│           │                                                 │
│  Loop → ciclo 30/30 min                                     │
│           │                                                 │
│           ├─ Cambio ciclo → save_state() inmediato         │
│           └─ Cada 10 min → save_state() checkpoint         │
│                                                             │
│  Shutdown → save_state() final                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
                    ┌──────────────┐
                    │ /state.json  │  (Flash persistente)
                    └──────────────┘
```

**Archivo de estado** (`/state.json`):
- `last_ntp_timestamp`: Último timestamp NTP conocido
- `last_save_timestamp`: Cuándo se guardó el estado
- `fridge_on`: Estado del relé (true=ON, false=OFF)
- `cycle_elapsed_seconds`: Tiempo transcurrido en ciclo actual
- `total_runtime_seconds`: Tiempo total de operación
- `boot_count`: Contador de reinicios

**Estrategia de recuperación**:
- **Sin NTP**: Arranca con 15 min ON (conservador) para promediar incertidumbre, luego continúa con ciclos 30/30 normales
- **Con NTP**: Calcula cuánto tiempo pasó desde último guardado y recupera el estado esperado del ciclo
- **Corte largo (>2h)**: Resetea ciclo por deriva del reloj interno
- **Checkpoints**: Guarda estado cada 10 min + en cada cambio de ciclo

**Mitigación de drift del reloj**:
- **Re-sincronización periódica**: NTP se re-sincroniza automáticamente cada 24 horas (configurable vía `NTP_RESYNC_INTERVAL_SECONDS`)
- **Detección de drift**: Valida que el tiempo no tenga drift excesivo (>5 min por defecto, configurable vía `MAX_TIME_DRIFT_SECONDS`)
- **Validación de tiempo**: Verifica rango de año (2020-2030) y coherencia temporal antes de usar NTP
- **Modo degradado**: Si se detecta drift excesivo o tiempo inválido, cae a modo degradado (sin NTP)

## Lógica de Control

### Modo Normal (por defecto)
1. **Con NTP (horario conocido):**
   - 07:00-01:30: Ciclos de 12 min ON / 18 min OFF
   - 01:30-07:00: Heladera apagada (descanso nocturno)
   - LED encendido cuando heladera está en modo OFF
   - LED apagado cuando relé activa heladera

2. **Sin NTP (sin hora o drift excesivo):**
   - LED parpadeante cada 0.5s
   - Ciclos de 12 min ON / 18 min OFF continuos
   - Se activa automáticamente si:
     - No hay sincronización NTP inicial
     - Drift del reloj excede `MAX_TIME_DRIFT_SECONDS` (default 300s = 5 min)
     - Año fuera de rango válido (2020-2030)

### Modo Helado
Activar con `HELADERA_MODO_HELADO=true` en `.env`:
- Ciclos de 10 min ON / 10 min OFF
- Sin descanso nocturno (funciona 24/7)
- Útil para hacer hielo o enfriamiento intensivo

## Configuración NTP

Variables de configuración en `.env`:

```bash
# Intervalo de re-sincronización NTP (segundos)
# Default: 86400 (24 horas)
NTP_RESYNC_INTERVAL_SECONDS=86400

# Drift máximo permitido antes de caer a modo degradado (segundos)
# Default: 300 (5 minutos)
MAX_TIME_DRIFT_SECONDS=300
```

**Nota**: Estas configuraciones aplican a todas las apps que usan NTP, no solo heladera.

## Toggle Modo Helado

Para alternar entre modo normal y modo helado:

**Desde PC/Mac/Termux:**
```bash
python3 tools/toggle_modo_helado.py              # Usa IP del .env
python3 tools/toggle_modo_helado.py 192.168.1.50 # IP específica
```

**Desde Termux Widget:**
- Ejecutar shortcut: "Toggle Modo Helado"

El script:
1. Lee el modo actual del .env local
2. Alterna el valor (true ↔ false)
3. Sube el .env actualizado al ESP8266
4. Reinicia el ESP8266 para aplicar cambios

**Modo Manual:**
Editar `.env` y agregar/modificar:
```bash
HELADERA_MODO_HELADO=true   # Activar modo helado
HELADERA_MODO_HELADO=false  # Desactivar (modo normal)
```

Luego hacer deploy:
```bash
python3 tools/deploy_wifi.py heladera
```
