#!/usr/bin/env python3
"""
Módulo reutilizable para monitor serial del ESP8266.
Proporciona funcionalidad de conexión, reconexión automática y monitoreo.
"""

import sys
import time
import glob
import subprocess

# Colores ANSI
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
RED = '\033[0;31m'
NC = '\033[0m'


def find_port():
    """Detecta puerto serie automáticamente"""
    ports = []
    for pattern in ['/dev/tty.usbserial-*', '/dev/tty.wchusbserial*', '/dev/ttyUSB*', '/dev/ttyACM*', '/dev/cu.*']:
        ports.extend(glob.glob(pattern))
    if sys.platform == 'win32':
        try:
            import serial.tools.list_ports
            ports = [p.device for p in serial.tools.list_ports.comports()]
        except:
            pass
    return sorted(set(ports))[0] if ports else None


def ensure_pyserial():
    """Asegura que pyserial esté instalado"""
    try:
        import serial
        return serial
    except ImportError:
        print(f"{YELLOW}Instalando pyserial...{NC}")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyserial'])
        import serial
        return serial


class SerialMonitor:
    """
    Monitor serial con reconexión automática para ESP8266.

    Uso:
        monitor = SerialMonitor(port='/dev/ttyUSB0', baudrate=115200)
        monitor.start()  # Blocking

    O con context manager:
        with SerialMonitor(port='/dev/ttyUSB0') as monitor:
            monitor.start()
    """

    def __init__(self, port=None, baudrate=115200, max_reconnect_attempts=5,
                 auto_detect_port=True, verbose=True):
        """
        Args:
            port: Puerto serial (ej: '/dev/ttyUSB0'). Si es None, intenta detectar.
            baudrate: Velocidad de baudios (default: 115200)
            max_reconnect_attempts: Máximo número de intentos de reconexión
            auto_detect_port: Si True y port es None, detecta automáticamente
            verbose: Si True, muestra mensajes informativos
        """
        self.serial = ensure_pyserial()
        self.baudrate = baudrate
        self.max_reconnect_attempts = max_reconnect_attempts
        self.verbose = verbose
        self.ser = None
        self.reconnect_count = 0
        self.is_running = False

        # Detectar puerto si no se especificó
        if port is None and auto_detect_port:
            port = find_port()
            if port and self.verbose:
                print(f"{BLUE}Puerto detectado: {port}{NC}")

        if not port:
            raise ValueError("Puerto serial requerido. Especifica 'port' o habilita 'auto_detect_port'")

        self.port = port

    def __enter__(self):
        """Context manager enter"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
        return False

    def connect(self):
        """Conecta al puerto serial"""
        if self.verbose:
            print(f"{BLUE}Intentando conectar a {self.port} @ {self.baudrate}...{NC}")

        self.ser = self.serial.Serial(self.port, self.baudrate, timeout=1)

        if self.verbose:
            print(f"{GREEN}🔌 Conectado a {self.port} @ {self.baudrate}{NC}\n")

        return True

    def reconnect(self):
        """Intenta reconectar al puerto serial"""
        if self.reconnect_count >= self.max_reconnect_attempts:
            if self.verbose:
                print(f"\n{RED}❌ Máximo número de intentos de reconexión alcanzado ({self.max_reconnect_attempts}){NC}")
                print(f"{YELLOW}El ESP8266 puede tener problemas. Verifica:{NC}")
                print(f"  1. Cable USB en buen estado")
                print(f"  2. Alimentación suficiente")
                print(f"  3. El ESP8266 no está en boot loop")
            return False

        self.reconnect_count += 1

        if self.verbose:
            print(f"\n{YELLOW}⚠️  Desconexión detectada (intento {self.reconnect_count}/{self.max_reconnect_attempts}){NC}")
            print(f"{YELLOW}   El ESP8266 probablemente se reinició...{NC}")

        # Cerrar puerto actual
        if self.ser and self.ser.is_open:
            self.ser.close()

        # Esperar antes de reconectar
        wait_time = 2 * self.reconnect_count
        if self.verbose:
            print(f"{BLUE}   Esperando {wait_time}s antes de reconectar...{NC}")
        time.sleep(wait_time)

        # Intentar reconectar
        try:
            if self.verbose:
                print(f"{BLUE}   Intentando reconectar a {self.port}...{NC}")

            self.ser = self.serial.Serial(self.port, self.baudrate, timeout=1)

            if self.verbose:
                print(f"{GREEN}   ✅ Reconectado exitosamente{NC}\n")

            return True

        except self.serial.SerialException as reconnect_error:
            if self.verbose:
                print(f"{RED}   ❌ Fallo al reconectar: {reconnect_error}{NC}")
                if self.reconnect_count < self.max_reconnect_attempts:
                    print(f"{YELLOW}   Reintentando...{NC}")
            return False

    def close(self):
        """Cierra la conexión serial"""
        self.is_running = False
        if self.ser and self.ser.is_open:
            self.ser.close()
            if self.verbose:
                print(f"{GREEN}Puerto serial cerrado{NC}")

    def start(self, show_header=True, initial_wait_time=3, no_data_warning_time=5):
        """
        Inicia el monitor serial (BLOCKING hasta Ctrl+C).

        Args:
            show_header: Si True, muestra encabezado informativo
            initial_wait_time: Segundos antes de mostrar warning inicial
            no_data_warning_time: Segundos sin datos para mostrar warning periódico
        """
        try:
            # Conectar si no está conectado
            if not self.ser or not self.ser.is_open:
                self.connect()

            if show_header and self.verbose:
                print(f"{BLUE}{'='*50}{NC}")
                print(f"{BLUE}📡 Monitor Serial Activo{NC}")
                print(f"{BLUE}{'='*50}{NC}\n")
                print(f"{YELLOW}Esperando datos del ESP8266...{NC}")
                print(f"{YELLOW}Si no ves nada, puede ser:{NC}")
                print(f"  1. Problema de memoria en boot.py (no puede imprimir)")
                print(f"  2. ESP8266 no está reiniciado")
                print(f"  3. Baudrate incorrecto (debe ser {self.baudrate})")
                print(f"  4. boot.py tiene errores y no se ejecuta")
                print(f"\n{YELLOW}Nota: Si boot.py tiene problemas de memoria,")
                print(f"      puede funcionar pero no imprimir nada al serial.{NC}")
                print(f"{BLUE}{'='*50}{NC}\n")

            self.is_running = True
            last_data_time = time.time()
            warning_shown = False
            initial_wait = True
            last_warning_time = 0
            warning_interval = 10  # Mostrar advertencia cada 10 segundos

            while self.is_running:
                try:
                    if self.ser.in_waiting:
                        line = self.ser.readline()
                        last_data_time = time.time()
                        warning_shown = False
                        initial_wait = False
                        last_warning_time = 0  # Reset tiempo de última advertencia
                        self.reconnect_count = 0  # Reset contador de reconexión

                        # Decodificar e imprimir
                        try:
                            print(line.decode('utf-8'), end='')
                        except:
                            print(line.decode('latin-1', errors='ignore'), end='')
                    else:
                        # Pequeño sleep para evitar CPU al 100%
                        time.sleep(0.01)

                        if not self.verbose:
                            continue

                        elapsed = time.time() - last_data_time
                        current_time = time.time()

                        # Advertencia inicial
                        if initial_wait and elapsed > initial_wait_time:
                            print(f"\n{YELLOW}⚠️  Esperando datos iniciales...{NC}")
                            print(f"{YELLOW}   Si no aparece nada, el ESP8266 puede tener problemas de memoria.{NC}")
                            print(f"{YELLOW}   Intenta reiniciar el dispositivo (desconecta y reconecta USB).{NC}\n")
                            initial_wait = False
                            warning_shown = True
                            last_warning_time = current_time

                        # Advertencia periódica (cada warning_interval segundos)
                        elif elapsed > no_data_warning_time:
                            # Solo mostrar si ha pasado suficiente tiempo desde la última advertencia
                            if current_time - last_warning_time >= warning_interval:
                                print(f"\n{YELLOW}⚠️  Sin datos desde hace {int(elapsed)}s{NC}")
                                print(f"{YELLOW}   Posibles causas:{NC}")
                                print(f"   - boot.py agotó memoria y no puede imprimir")
                                print(f"   - ESP8266 necesita reinicio (desconecta/reconecta USB)")
                                print(f"   - boot.py tiene errores")
                                print(f"\n{YELLOW}   Si el dispositivo funciona pero no imprime,")
                                print(f"   prueba conectar vía WebREPL en lugar del serial.{NC}\n")
                                last_warning_time = current_time
                                warning_shown = True

                except OSError as e:
                    # Error de I/O - probablemente el ESP8266 se reinició
                    if not self.reconnect():
                        break

                    # Reset timers después de reconexión exitosa
                    last_data_time = time.time()
                    warning_shown = False
                    last_warning_time = 0

        except self.serial.SerialException as e:
            if self.verbose:
                print(f"\n{RED}Error de conexión serial: {e}{NC}")
                print(f"{YELLOW}Verifica que el puerto {self.port} esté disponible{NC}")
                print(f"{YELLOW}  - Desconecta y reconecta el ESP8266{NC}")
                print(f"{YELLOW}  - Verifica que no esté en uso por otro programa{NC}")

        except KeyboardInterrupt:
            if self.verbose:
                print(f"\n\n{YELLOW}❌ Monitor serial cerrado por usuario{NC}")

        except Exception as e:
            if self.verbose:
                print(f"\n{RED}Error en monitor serial: {e}{NC}")
                import traceback
                print(f"{YELLOW}Traceback:{NC}")
                traceback.print_exc()

        finally:
            self.close()


def main():
    """Ejemplo de uso del monitor serial"""
    import argparse

    parser = argparse.ArgumentParser(description='Monitor serial para ESP8266')
    parser.add_argument('-p', '--port', help='Puerto serial (ej: /dev/ttyUSB0)')
    parser.add_argument('-b', '--baudrate', type=int, default=115200, help='Baudrate (default: 115200)')
    parser.add_argument('-r', '--max-reconnect', type=int, default=5, help='Máximo intentos de reconexión')
    parser.add_argument('-q', '--quiet', action='store_true', help='Modo silencioso (solo output del ESP8266)')

    args = parser.parse_args()

    try:
        monitor = SerialMonitor(
            port=args.port,
            baudrate=args.baudrate,
            max_reconnect_attempts=args.max_reconnect,
            verbose=not args.quiet
        )
        monitor.start()
    except ValueError as e:
        print(f"{RED}Error: {e}{NC}")
        print(f"{YELLOW}Usa --port para especificar el puerto serial{NC}")
        sys.exit(1)


if __name__ == '__main__':
    main()
