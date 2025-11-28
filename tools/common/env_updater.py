#!/usr/bin/env python3
"""
Utilidad para actualizar .env con la app correcta antes de deploy.
"""

import re
from pathlib import Path


def update_env_for_app(project_dir, app_name):
    """
    Actualiza o crea .env con APP=<app_name>.

    Args:
        project_dir: Directorio raíz del proyecto
        app_name: Nombre de la app (blink, gallinero, heladera)

    Returns:
        Path: Ruta al archivo .env temporal actualizado
    """
    env_path = Path(project_dir) / '.env'
    temp_env = Path(project_dir) / '.env.tmp'

    if env_path.exists():
        # Leer .env existente
        with open(env_path, 'r') as f:
            env_content = f.read()

        # Actualizar o agregar APP=<app_name>
        if re.search(r'^APP=', env_content, re.MULTILINE):
            # Reemplazar APP existente
            env_content = re.sub(r'^APP=.*$', f'APP={app_name}', env_content, flags=re.MULTILINE)
        else:
            # Agregar APP al final
            if not env_content.endswith('\n'):
                env_content += '\n'
            env_content += f'\n# App configuration (auto-updated)\nAPP={app_name}\n'
    else:
        # Crear .env mínimo
        env_content = f'# Auto-generated\nAPP={app_name}\n'

    # Guardar temporal
    with open(temp_env, 'w') as f:
        f.write(env_content)

    return temp_env


def cleanup_temp_env(project_dir):
    """Elimina archivo .env temporal si existe"""
    temp_env = Path(project_dir) / '.env.tmp'
    if temp_env.exists():
        temp_env.unlink()
