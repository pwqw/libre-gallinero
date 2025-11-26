#!/usr/bin/env python3
"""
Utilidades comunes para operaciones con ampy (USB Serial).
Funciones compartidas para setup y deployment de ESP8266.
"""

import os
import subprocess
import tempfile
from pathlib import Path


def run_ampy(cmd, verbose=True):
    """
    Ejecuta comando ampy.
    
    Args:
        cmd: Lista de argumentos para ampy (sin 'ampy' al inicio)
        verbose: Si True, muestra mensajes de error
    
    Returns:
        bool: True si el comando fue exitoso, False en caso contrario
    """
    result = subprocess.run(['ampy'] + cmd, capture_output=True, text=True)
    if result.returncode != 0:
        if verbose:
            error_msg = result.stderr.strip() or result.stdout.strip()
            if error_msg:
                print(f"Error: {error_msg}")
            else:
                print(f"Error: ampy falló con código {result.returncode}")
        return False
    return True


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
    base_modules = ['boot.py', 'main.py', 'config.py', 'wifi.py', 'ntp.py', 'app_loader.py']
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

