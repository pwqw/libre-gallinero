import pytest
from pathlib import Path


def test_all_modules_under_8kb():
    """Verifica que todos los módulos Python en src pesen menos de 8KB (límite de MAX_FILE_SIZE)."""
    src_dir = Path(__file__).parent.parent / "src"
    max_size = 8 * 1024  # 8KB en bytes (consistente con MAX_FILE_SIZE en webrepl_client.py)
    wifi_max_size = 12 * 1024  # 12KB para wifi.py (excepción especial)
    
    failed_modules = []
    
    # Recorrer recursivamente todos los archivos .py en src
    for py_file in src_dir.rglob("*.py"):
        file_size = py_file.stat().st_size
        # Excepción: wifi.py puede ser hasta 12KB
        allowed_size = wifi_max_size if py_file.name == "wifi.py" else max_size
        if file_size > allowed_size:  # Usar > en lugar de >= para ser consistente con validate_file_size
            failed_modules.append((py_file.relative_to(src_dir.parent), file_size, allowed_size))
    
    if failed_modules:
        error_msg = "Los siguientes módulos exceden su límite de tamaño:\n"
        for module_path, size, limit in failed_modules:
            size_kb = size / 1024
            limit_kb = limit / 1024
            error_msg += f"  - {module_path}: {size_kb:.2f}KB (límite: {limit_kb:.0f}KB)\n"
        pytest.fail(error_msg)

