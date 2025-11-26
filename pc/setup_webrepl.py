#!/usr/bin/env python3
"""
Setup WebREPL simplificado para ESP8266
Wrapper minimalista que usa tools/setup_initial.py
"""

import sys
import os
from pathlib import Path

# Ajustar path para imports locales
script_dir = Path(__file__).parent.absolute()
project_dir = script_dir.parent
sys.path.insert(0, str(project_dir / 'pc'))

from colors import GREEN, YELLOW, BLUE, RED, NC

# Importar y ejecutar setup_initial directamente
sys.path.insert(0, str(project_dir / 'tools'))
from setup_initial import main as setup_initial_main

if __name__ == '__main__':
    print(f"{BLUE}🔧 Setup WebREPL para ESP8266{NC}\n")
    print(f"{YELLOW}💡 Usando tools/setup_initial.py (sistema compartido){NC}\n")
    setup_initial_main()
