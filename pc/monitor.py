#!/usr/bin/env python3
"""
Monitor serial standalone para ESP8266.
Script simple para conectarse y monitorear el serial del ESP8266.

Uso:
    ./pc/monitor.py                    # Auto-detecta el puerto
    ./pc/monitor.py -p /dev/ttyUSB0    # Puerto específico
    ./pc/monitor.py -b 9600            # Baudrate diferente
    ./pc/monitor.py -q                 # Modo silencioso (solo output ESP8266)
"""

from serial_monitor import main

if __name__ == '__main__':
    main()
