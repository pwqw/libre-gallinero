# Libre Gallinero

## Descripción
Sistema de automatización para el control lumínico y térmico de aves de corral, especialmente diseñado para gallinas ponedoras. Utiliza NodeMCU con MicroPython para simular los horarios de luz natural del verano y mantener una temperatura adecuada para los pollitos.

Para una descripción más detallada del proyecto, sus componentes y funcionalidades, consulta la [Descripción Detallada del Proyecto](DESCRIPCION-DEL-PROYECTO.md).

## Características
- Control automático de iluminación basado en horarios solares de verano
- Control de temperatura para pollitos con sensor DHT11
- Sincronización de hora vía hotspot cuando no hay WiFi
- Compatible con NodeMCU (ESP8266/ESP32)
- WebREPL para desarrollo remoto

## Requisitos
- NodeMCU (ESP8266 o ESP32).
- Python 3.x instalado en tu sistema.
- pip (gestor de paquetes de Python).
- [MicroPython](https://micropython.org/) instalado en el dispositivo.
- Cable USB para conectar el NodeMCU a tu computadora.
- Editor de texto o IDE compatible (por ejemplo, [Thonny](https://thonny.org/) o [VS Code](https://code.visualstudio.com/)).

## Quick Start

### Primera vez (PC/Mac - Requiere USB)

```bash
# 1. Clonar repositorio
git clone https://github.com/pwqw/libre-gallinero.git
cd libre-gallinero

# 2. Configurar
cp .env.example .env
nano .env  # Editar WiFi y password

# 3. Setup inicial (USB, solo una vez)
python3 tools/setup_initial.py

# 4. Deploy (ya sin cables)
python3 tools/deploy_wifi.py
```

### Desarrollo diario (PC/Mac o Termux/Android)

```bash
# Editar código
vim src/main.py

# Deploy automático
python3 tools/deploy_wifi.py gallinero  # WiFi (sin cables)
# O con caché de IPs (más rápido, ideal para móvil)
python3 tools/deploy_app.py gallinero   # WiFi + caché de IP
# O
python3 tools/deploy_usb.py gallinero   # USB (más rápido)
```

### Instalación rápida en Termux (Android)

```bash
curl -sL https://raw.githubusercontent.com/pwqw/libre-gallinero/main/termux/termux-setup.sh | sh
```

Luego configura `.env` y usa `python3 tools/deploy_wifi.py` para deploy.

## Estructura del Proyecto
```
libre-gallinero/
├── src/             # Código ESP8266
│   ├── boot.py      # Bootstrapping WiFi + WebREPL
│   ├── main.py      # Lógica principal
│   ├── solar.py     # Cálculos solares
│   └── logic.py     # Control de relés
├── tools/           # Scripts de deployment
│   ├── deploy_wifi.py    # Deploy vía WiFi
│   ├── deploy_usb.py     # Deploy vía USB
│   └── setup_initial.py  # Setup inicial
├── docs/            # Documentación
└── requirements.txt # Dependencias Python
```

## Documentación

- **Instalación completa:** Ver [pc/README.md](pc/README.md) o [termux/README.md](termux/README.md)
- **Descripción del proyecto:** Ver [DESCRIPCION-DEL-PROYECTO.md](DESCRIPCION-DEL-PROYECTO.md)

## Contribuciones
¡Las contribuciones son bienvenidas! Si deseas contribuir, por favor sigue estos pasos:
1. Haz un fork del repositorio.
2. Crea una rama para tu característica o corrección de errores (`git checkout -b mi-rama`).
3. Realiza tus cambios y haz un commit (`git commit -m 'Descripción de los cambios'`).
4. Sube tus cambios a tu fork (`git push origin mi-rama`).
5. Abre un Pull Request en este repositorio.

## Licencia
Este proyecto está licenciado bajo la [GNU General Public License v3.0](LICENSE).

## Recursos
- [Documentación oficial de MicroPython](https://docs.micropython.org/)
- [Foro de MicroPython](https://forum.micropython.org/)
- [Documentación de NodeMCU](https://nodemcu.readthedocs.io/)

---

¡Gracias por ver este proyecto! Si tienes alguna pregunta o sugerencia, no dudes en abrir un issue.
