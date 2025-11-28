#!/usr/bin/env bash
# -*- coding: utf-8 -*-
# Wrapper para PC - Usa herramientas de tools/

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

exec python3 tools/deploy_usb.py "$@"
