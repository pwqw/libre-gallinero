"""
Configuración global de pytest para el proyecto.

Agrega src/ al PYTHONPATH para que los imports absolutos de MicroPython
funcionen correctamente durante las pruebas.
"""
import sys
import os
from pathlib import Path

# Obtener el directorio raíz del proyecto
project_root = Path(__file__).parent.parent
src_path = project_root / 'src'

# Agregar src/ al sys.path si no está ya
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

