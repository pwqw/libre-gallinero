#!/data/data/com.termux/files/usr/bin/bash
# -*- coding: utf-8 -*-
# Shortcut script para ejecutar el setup (update-upgrade)

set -e
set -u

cd "$HOME/libre-gallinero"
exec ./termux/termux-setup.sh

