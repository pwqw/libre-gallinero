# Libre Gallinero

## Descripción
Sistema de automatización para el control lumínico y térmico de gallineros, especialmente diseñado para gallinas ponedoras. Utiliza NodeMCU con MicroPython para simular los horarios de luz natural del verano y mantener una temperatura adecuada para los pollitos.

Para una descripción más detallada del proyecto, sus componentes y funcionalidades, consulta la [Descripción Detallada del Proyecto](DESCRIPCION-DEL-PROYECTO.md).

## Características
- Control automático de iluminación basado en horarios solares de verano
- Control de temperatura para pollitos con sensor DHT11
- Interfaz web para monitoreo
- Compatible con NodeMCU (ESP8266/ESP32)
- Configuración WiFi vía punto de acceso

## Requisitos
- NodeMCU (ESP8266 o ESP32).
- Python 3.x instalado en tu sistema.
- pip (gestor de paquetes de Python).
- [MicroPython](https://micropython.org/) instalado en el dispositivo.
- Cable USB para conectar el NodeMCU a tu computadora.
- Editor de texto o IDE compatible (por ejemplo, [Thonny](https://thonny.org/) o [VS Code](https://code.visualstudio.com/)).

## Instalación
1. Clona este repositorio:
   ```bash
   git clone git@github.com:pwqw/libre-gallinero.git
   cd libre-gallinero
   ```
2. Crea y activa un entorno virtual:
   ```bash
   python3 -m venv env
   source env/bin/activate  # En Mac/Linux
   # O en Windows:
   # env\Scripts\activate
   ```
3. Instala las dependencias de Python:
   ```bash
   pip install -r requirements.txt
   ```
4. Conecta tu NodeMCU a tu computadora mediante un cable USB.
5. Flashea MicroPython en tu dispositivo si aún no lo has hecho. Puedes seguir [esta guía](https://docs.micropython.org/en/latest/esp8266/tutorial/intro.html).
6. Identifica el puerto serie de tu NodeMCU:
   - En Mac/Linux: Ejecuta `ls /dev/tty.*` y busca algo como `/dev/tty.usbserial-*`
   - En Windows: Usa el Administrador de dispositivos y busca el puerto COM asignado

7. Configura la variable de entorno para ampy:
   ```bash
   # En Mac/Linux (ajusta el puerto según tu sistema)
   set -x AMPY_PORT /dev/tty.usbserial-XXXX

   # En Windows (ajusta el puerto según tu sistema)
   set -x AMPY_PORT COM3
   ```

8. Sube los archivos al NodeMCU:
   ```bash
   ampy put -r src .
   ```

## Estructura del Proyecto
```
libre-gallinero/
├── src/             # Código fuente del proyecto
│   ├── main.py      # Control principal del sistema
│   ├── config.py    # Configuración de WiFi y parámetros del sistema
│   ├── solar.py     # Cálculos de horarios solares
│   └── tests/*.py   # Pruebas unitarias
├── docs/            # Documentación y diagramas
└── requirements.txt # Dependencias de Python
```

## Uso
1. Configura los parámetros de WiFi y ubicación en `config.py`
2. Sube los archivos al NodeMCU
3. Al iniciar, el dispositivo creará un punto de acceso WiFi si no puede conectarse a la red configurada
4. Accede a la interfaz web para monitorear el estado del sistema

## Contribuciones
¡Las contribuciones son bienvenidas! Si deseas contribuir, por favor sigue estos pasos:
1. Haz un fork del repositorio.
2. Crea una rama para tu característica o corrección de errores (`git checkout -b mi-rama`).
3. Realiza tus cambios y haz un commit (`git commit -m 'Descripción de los cambios'`).
4. Sube tus cambios a tu fork (`git push origin mi-rama`).
5. Abre un Pull Request en este repositorio.

## Licencia
Este proyecto está licenciado bajo la [MIT License](LICENSE).

## Recursos
- [Documentación oficial de MicroPython](https://docs.micropython.org/)
- [Foro de MicroPython](https://forum.micropython.org/)
- [Documentación de NodeMCU](https://nodemcu.readthedocs.io/)

---

¡Gracias por usar esta plantilla! Si tienes alguna pregunta o sugerencia, no dudes en abrir un issue.
