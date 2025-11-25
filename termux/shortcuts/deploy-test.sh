#!/data/data/com.termux/files/usr/bin/bash
# -*- coding: utf-8 -*-
# Shortcut script para ejecutar el deploy de test.py vía WebREPL

set -e
set -u

cd $HOME/libre-gallinero
git pull --rebase

# Ejecutar deploy de test vía WebREPL
exec python3 termux/webrepl_deploy_test.py
