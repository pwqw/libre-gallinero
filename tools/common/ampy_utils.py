#!/usr/bin/env python3
"""
Utilidades comunes para operaciones con ampy (USB Serial).
Funciones compartidas para setup y deployment de ESP8266.
"""

import os
import sys
import subprocess
import tempfile
import time
from pathlib import Path

# Colores para terminal (compatibilidad)
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'


def run_ampy(cmd, verbose=True, timeout=30):
    """
    Ejecuta comando ampy con manejo robusto de errores.

    Args:
        cmd: Lista de argumentos para ampy (sin 'ampy' al inicio)
        verbose: Si True, muestra mensajes de error
        timeout: Timeout en segundos (default: 30)

    Returns:
        bool: True si el comando fue exitoso, False en caso contrario
    """
    try:
        result = subprocess.run(
            ['ampy'] + cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        if result.returncode != 0:
            if verbose:
                error_msg = result.stderr.strip() or result.stdout.strip()

                # Detectar errores comunes de permisos
                if 'Permission denied' in error_msg or 'could not open port' in error_msg.lower():
                    port = None
                    # Extraer puerto del comando si está disponible
                    if '--port' in cmd:
                        try:
                            port_idx = cmd.index('--port')
                            if port_idx + 1 < len(cmd):
                                port = cmd[port_idx + 1]
                        except (ValueError, IndexError):
                            pass

                    print(f"\n❌ ERROR DE PERMISOS: No tienes acceso al puerto serie")
                    if port:
                        print(f"   Puerto: {port}")
                    print(f"\n💡 Solución:")
                    print(f"   1. Agregar tu usuario al grupo 'dialout':")
                    print(f"      sudo usermod -a -G dialout $USER")
                    print(f"   2. Cerrar sesión y volver a entrar (o reiniciar)")
                    print(f"   3. Verificar permisos: groups | grep dialout")
                    print(f"\n   Alternativa temporal (NO recomendado):")
                    print(f"      sudo chmod 666 {port if port else '/dev/ttyUSB0'}\n")
                elif error_msg:
                    print(f"❌ Error: {error_msg}")
                else:
                    print(f"❌ Error: ampy falló con código {result.returncode}")
            return False
        return True

    except subprocess.TimeoutExpired:
        if verbose:
            print(f"❌ TIMEOUT: El comando tardó más de {timeout} segundos")
            print(f"   Posibles causas:")
            print(f"   • ESP8266 no responde (desconectado o en mal estado)")
            print(f"   • Programa en ESP8266 bloqueado (sin sleep())")
            print(f"   • Puerto serie incorrecto")
        return False
    except FileNotFoundError:
        if verbose:
            print(f"❌ ERROR: 'ampy' no está instalado")
            print(f"   Instalar con: pip install adafruit-ampy")
        return False
    except Exception as e:
        if verbose:
            print(f"❌ Error inesperado: {e}")
        return False


def ensure_directory_exists(port, dir_name, verbose=True):
    """
    Asegura que un directorio existe en el ESP8266.
    Verifica y crea el directorio de forma robusta usando código Python.
    
    Args:
        port: Puerto serie del ESP8266
        dir_name: Nombre del directorio a crear
        verbose: Si True, muestra mensajes informativos
    
    Returns:
        bool: True si el directorio existe o se creó exitosamente, False en caso contrario
    """
    # Crear script Python que verifica y crea el directorio
    create_script = f"""import os
dir_name = '{dir_name}'
try:
    # Listar directorios en la raíz
    files = os.listdir('/')
    if dir_name in files:
        print('DIR_EXISTS')
    else:
        # Intentar crear el directorio
        try:
            os.mkdir(dir_name)
            # Verificar que se creó
            files_after = os.listdir('/')
            if dir_name in files_after:
                print('DIR_CREATED')
            else:
                print('DIR_FAILED')
        except OSError as e:
            # Si el error es EEXIST (17), el directorio ya existe
            if e.args[0] == 17:
                print('DIR_EXISTS')
            else:
                print(f'DIR_ERROR: {{e.args[0]}}')
except Exception as e:
    print(f'DIR_ERROR: {{e}}')
"""
    
    # Usar archivo temporal para ejecutar código Python
    temp_script = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(create_script)
            temp_script = f.name
        
        # Ejecutar script con ampy run
        result = subprocess.run(
            ['ampy', '--port', port, 'run', temp_script],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Analizar salida
        output = result.stdout.strip() + result.stderr.strip()
        
        if 'DIR_EXISTS' in output or 'DIR_CREATED' in output:
            return True
        elif 'DIR_FAILED' in output or 'DIR_ERROR' in output:
            if verbose:
                print(f"   ⚠️  Error con directorio {dir_name}: {output}")
                if result.stdout.strip() or result.stderr.strip():
                    print(f"      stdout: {result.stdout}")
                    print(f"      stderr: {result.stderr}")
            return False
        else:
            # Si no hay salida reconocible, intentar método alternativo
            if verbose:
                print(f"   ⚠️  Salida inesperada al crear {dir_name}, intentando método alternativo...")
            # Intentar directamente con ampy mkdir y verificar
            result_mkdir = subprocess.run(
                ['ampy', '--port', port, 'mkdir', dir_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            # Verificar que existe
            verify_script = f"""import os
if '{dir_name}' in os.listdir('/'):
    print('VERIFIED')
else:
    print('NOT_FOUND')
"""
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f2:
                f2.write(verify_script)
                temp_verify = f2.name
            
            try:
                result_verify = subprocess.run(
                    ['ampy', '--port', port, 'run', temp_verify],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                return 'VERIFIED' in (result_verify.stdout + result_verify.stderr)
            finally:
                try:
                    os.unlink(temp_verify)
                except Exception:
                    pass
            return False
            
    except subprocess.TimeoutExpired:
        if verbose:
            print(f"   ❌ Timeout creando directorio {dir_name}")
        return False
    except Exception as e:
        if verbose:
            print(f"   ❌ Error creando directorio {dir_name}: {e}")
        return False
    finally:
        # Limpiar archivo temporal
        if temp_script:
            try:
                os.unlink(temp_script)
            except Exception:
                pass


def get_app_files(project_dir, app_name='blink'):
    """
    Obtiene lista de archivos de una app para setup inicial.
    
    Args:
        project_dir: Directorio raíz del proyecto (Path o str)
        app_name: Nombre de la app (default: 'blink')
    
    Returns:
        list: Lista de tuplas (local_path, remote_name) o (None, "mkdir:dirname")
    """
    project_dir = Path(project_dir)
    src_dir = project_dir / 'src'
    files = []
    
    # App directory
    app_dir = src_dir / app_name
    if app_dir.exists() and app_dir.is_dir():
        # Create app directory on ESP8266
        files.append((None, f'mkdir:{app_name}'))
        
        # Upload __init__.py first (makes it a valid Python package)
        init_file = app_dir / '__init__.py'
        if init_file.exists():
            files.append((str(init_file), f'{app_name}/__init__.py'))
        
        # Upload other .py files in app directory
        for py_file in app_dir.glob('*.py'):
            if py_file.name != '__init__.py':
                files.append((str(py_file), f'{app_name}/{py_file.name}'))
    else:
        if app_name == 'blink':
            # Blink es requerido, mostrar advertencia
            print(f"⚠️  {app_name}/ no encontrado - sistema puede no funcionar")
    
    return files


def get_base_files_to_upload(project_dir, include_app=True, app_name='blink'):
    """
    Obtiene lista de archivos base del sistema + app opcional para setup inicial.
    
    Args:
        project_dir: Directorio raíz del proyecto (Path o str)
        include_app: Si True, incluye archivos de la app (default: True)
        app_name: Nombre de la app a incluir si include_app es True (default: 'blink')
    
    Returns:
        list: Lista de tuplas (local_path, remote_name) o (None, "mkdir:dirname")
    """
    project_dir = Path(project_dir)
    src_dir = project_dir / 'src'
    files = []
    
    # Base modules (required for boot sequence)
    base_modules = ['boot.py', 'main.py', 'logger.py', 'config.py', 'wifi.py', 'ntp.py', 'timezone.py', 'app_loader.py']
    for filename in base_modules:
        local_path = src_dir / filename
        if local_path.exists():
            files.append((str(local_path), filename))
        else:
            print(f"⚠️  {filename} no encontrado en src/")
    
    # App files (optional)
    if include_app:
        app_files = get_app_files(project_dir, app_name)
        files.extend(app_files)
    
    return files


def verify_app_directory(port, app_name='blink', verbose=True):
    """
    Verifica que el directorio de una app existe y contiene archivos.
    
    Args:
        port: Puerto serie del ESP8266
        app_name: Nombre de la app a verificar (default: 'blink')
        verbose: Si True, muestra mensajes informativos
    
    Returns:
        bool: True si el directorio existe y contiene archivos, False en caso contrario
    """
    verify_script = f"""import os
try:
    files = os.listdir('/')
    if '{app_name}' in files:
        app_files = os.listdir('{app_name}')
        print(f'APP_EXISTS: {{app_files}}')
    else:
        print('APP_NOT_FOUND')
except Exception as e:
    print(f'APP_ERROR: {{e}}')
"""
    temp_verify = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(verify_script)
            temp_verify = f.name
        
        result_verify = subprocess.run(
            ['ampy', '--port', port, 'run', temp_verify],
            capture_output=True,
            text=True,
            timeout=5
        )
        output = (result_verify.stdout + result_verify.stderr).strip()
        if 'APP_EXISTS' in output:
            if verbose:
                print(f"✅ Directorio {app_name}/ verificado correctamente")
            return True
        elif 'APP_NOT_FOUND' in output:
            if verbose:
                print(f"❌ Directorio {app_name}/ NO encontrado después del deploy")
                print(f"   Esto indica un problema con la creación del directorio")
            return False
        else:
            if verbose:
                print(f"⚠️  Verificación ambigua: {output}")
            return False
    except Exception as e:
        if verbose:
            print(f"⚠️  No se pudo verificar directorio {app_name}/: {e}")
        return False
    finally:
        if temp_verify:
            try:
                os.unlink(temp_verify)
            except Exception:
                pass


def check_ampy_installed():
    """
    Verifica si ampy está instalado.
    
    Returns:
        bool: True si ampy está instalado, False en caso contrario
    """
    try:
        import ampy.cli
        return True
    except ImportError:
        return False


def install_ampy():
    """
    Instala ampy si no está disponible.
    
    Returns:
        bool: True si la instalación fue exitosa, False en caso contrario
    """
    print(f"{YELLOW}⚠️  ampy no está instalado. Instalando...{NC}")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'adafruit-ampy', 'pyserial'])
        print(f"{GREEN}✅ ampy instalado correctamente{NC}\n")
        return True
    except subprocess.CalledProcessError:
        print(f"{RED}❌ Error al instalar ampy{NC}")
        return False


def check_port_permissions(port):
    """
    Verifica que el usuario tiene permisos para acceder al puerto serie.

    Args:
        port: Ruta al dispositivo serie (ej: /dev/ttyUSB0)

    Returns:
        bool: True si tiene permisos, False en caso contrario
    """
    if not os.path.exists(port):
        print(f"{RED}❌ Puerto {port} no existe{NC}")
        print(f"   Verifica que el ESP8266 está conectado")
        return False

    # Verificar permisos de lectura/escritura
    try:
        # Verificar si tenemos permisos de lectura y escritura
        if os.access(port, os.R_OK | os.W_OK):
            return True

        # No tenemos permisos
        print(f"\n{RED}❌ ERROR DE PERMISOS: No tienes acceso al puerto {port}{NC}")
        print(f"\n💡 Solución recomendada:")
        print(f"   1. Agregar tu usuario al grupo 'dialout':")
        print(f"      {YELLOW}sudo usermod -a -G dialout $USER{NC}")
        print(f"   2. {YELLOW}Cerrar sesión y volver a entrar{NC} (o reiniciar)")
        print(f"   3. Verificar: {YELLOW}groups | grep dialout{NC}")
        print(f"\n   Alternativa rápida (temporal, NO recomendado):")
        print(f"      {YELLOW}sudo chmod 666 {port}{NC}")
        print(f"\n   Después de aplicar la solución, ejecuta este script nuevamente.\n")
        return False

    except PermissionError:
        print(f"\n{RED}❌ ERROR: Sin permisos para acceder a {port}{NC}")
        print(f"   Aplica las soluciones mostradas arriba")
        return False
    except Exception as e:
        print(f"{YELLOW}⚠️  No se pudo verificar permisos de {port}: {e}{NC}")
        # Continuamos porque puede que funcione de todas formas
        return True


def auto_reset_esp8266(port, method='soft'):
    """
    Resetea ESP8266 automáticamente vía puerto serie

    Args:
        port: Puerto serie (ej: /dev/ttyUSB0)
        method: 'soft' (CTRL-D reboot) o 'hard' (DTR/RTS reset)

    Returns:
        bool: True si reset exitoso, False si falló
    """
    try:
        import serial
    except ImportError:
        print(f"{YELLOW}⚠️  pyserial no instalado. Instalando...{NC}")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyserial'])
        import serial

    try:
        if method == 'soft':
            # Soft reset via CTRL-D (MicroPython soft reboot)
            print(f"{BLUE}🔄 Reseteando ESP8266 (soft reset - CTRL-D)...{NC}")
            ser = serial.Serial(port, 115200, timeout=1)
            time.sleep(0.1)
            ser.write(b'\x04')  # CTRL-D = soft reboot
            time.sleep(2)  # Esperar boot completo
            ser.close()
            print(f"{GREEN}✅ Reset automático exitoso{NC}")
            return True

        elif method == 'hard':
            # Hard reset via DTR/RTS (hardware reset)
            print(f"{BLUE}🔄 Reseteando ESP8266 (hard reset - DTR/RTS)...{NC}")
            ser = serial.Serial(port, 115200)
            ser.setDTR(False)  # DTR low = reset active
            ser.setRTS(True)   # RTS high
            time.sleep(0.1)
            ser.setDTR(True)   # DTR high = reset release
            ser.setRTS(False)  # RTS low
            time.sleep(0.5)    # Esperar estabilización
            ser.close()
            print(f"{GREEN}✅ Reset automático exitoso{NC}")
            return True
        else:
            print(f"{RED}❌ Método desconocido: {method}{NC}")
            return False

    except Exception as e:
        print(f"{YELLOW}⚠️  Reset automático falló: {e}{NC}")
        print(f"{YELLOW}   Reinicia manualmente (desconecta/reconecta USB){NC}")
        return False


def get_files_to_upload(project_dir, app_name=None, include_base=True):
    """
    Obtiene lista de archivos a subir desde src/.
    Función unificada que combina get_base_files_to_upload() y get_files_to_upload_usb().
    
    Args:
        project_dir: Directorio raíz del proyecto (Path o str)
        app_name: Nombre de la app a incluir (blink, gallinero, heladera, etc.) o None
        include_base: Si True, incluye archivos base del sistema (default: True)
    
    Returns:
        list: Lista de tuplas (local_path, remote_name) o (None, "mkdir:dirname") para directorios
    """
    project_dir = Path(project_dir)
    src_dir = project_dir / 'src'
    files = []
    
    # Base modules (si se solicitan)
    if include_base:
        base_modules = ['boot.py', 'main.py', 'logger.py', 'config.py', 'wifi.py', 'ntp.py', 'timezone.py', 'app_loader.py']
        for filename in base_modules:
            local_path = src_dir / filename
            if local_path.exists():
                files.append((str(local_path), filename))
            # No mostrar advertencia si es opcional (deploy_usb puede no necesitar todos)
    
    # App-specific files
    if app_name:
        app_dir_path = src_dir / app_name
        if app_dir_path.exists() and app_dir_path.is_dir():
            # Create app directory
            files.append((None, f"mkdir:{app_name}"))
            
            # Upload __init__.py first
            init_file = app_dir_path / '__init__.py'
            if init_file.exists():
                remote_name = f"{app_name}/__init__.py"
                files.append((str(init_file), remote_name))
            
            # Upload other .py files
            for py_file in app_dir_path.glob('*.py'):
                if py_file.name != '__init__.py':
                    remote_name = f"{app_name}/{py_file.name}"
                    files.append((str(py_file), remote_name))
    
    # Templates if exist (solo si se incluyen archivos base)
    if include_base:
        templates_dir = src_dir / 'templates'
        if templates_dir.exists():
            files.append((None, "mkdir:templates"))
            for html_file in templates_dir.glob('*.html'):
                files.append((str(html_file), f"templates/{html_file.name}"))
    
    return files

