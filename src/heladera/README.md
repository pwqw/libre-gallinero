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
| Encendido fijo | App funcional, heladera en ciclo normal |
| Apagado (durante ciclo) | Relé activado (heladera encendida) |
| Parpadeo 0.5s | Sin NTP (sin WiFi o sin Internet) - modo degradado |

## Hardware

```
NodeMCU ESP-12E (ESP8266)

[D1] (GPIO5)  -> Relay IN (Normally Closed)
[GND]         -> Relay GND
[VIN] (5V)    -> Relay VCC
[LED] (GPIO2) -> LED integrado (indicador de estado)
```

## Lógica de Control

1. **Con NTP (horario conocido):**
   - 07:00-00:00: Ciclos de 30 min ON/OFF
   - 00:00-07:00: Heladera apagada (descanso nocturno)
   - LED encendido cuando heladera está en modo OFF
   - LED apagado cuando relé activa heladera

2. **Sin NTP (sin hora):**
   - LED parpadeante cada 0.5s
   - Ciclos de 30 min ON/OFF continuos (sin descanso nocturno)
