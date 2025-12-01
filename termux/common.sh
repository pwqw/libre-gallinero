#!/data/data/com.termux/files/usr/bin/bash
# -*- coding: utf-8 -*-
# Funciones comunes para scripts de Termux

# Pausa para leer resultados antes de que se cierre el terminal
# Uso: pause [mensaje]
pause() {
    local msg="${1:-Presiona Enter para continuar...}"
    printf "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    read -p "$msg"
}

# Pausa con mensaje de éxito
pause_success() {
    printf "\n✅ ¡Operación completada exitosamente!\n"
    pause
}

# Pausa con mensaje de error
pause_error() {
    local error_msg="${1:-Ocurrió un error}"
    printf "\n❌ Error: %s\n" "$error_msg"
    pause "Presiona Enter para cerrar..."
}

# Banner estándar
print_banner() {
    local title="$1"
    printf "\n"
    printf "╔════════════════════════════════════════╗\n"
    printf "║       🐔  LIBRE GALLINERO  🐔          ║\n"
    printf "║  %-36s  ║\n" "$title"
    printf "╚════════════════════════════════════════╝\n"
    printf "\n"
}

# Wrapper para ejecutar comando con manejo de errores y pausa
# Uso: run_with_pause "descripción" comando [args...]
run_with_pause() {
    local description="$1"
    shift

    printf "🚀 %s...\n\n" "$description"

    if "$@"; then
        pause_success
        return 0
    else
        local exit_code=$?
        pause_error "$description falló (código: $exit_code)"
        return $exit_code
    fi
}
