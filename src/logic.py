# Lógica para el control de relés de ponedoras y pollitos
# relay_ponedoras: relé normal cerrado (activo en bajo)
# relay_pollitos: relé normal abierto (activo en alto)
#
# Se asume que la latitud y los horarios de amanecer/atardecer de verano y actuales
# se calculan externamente y se pasan como argumentos.

def relay_ponedoras_state(hora_actual, amanecer_verano, amanecer_actual, atardecer_actual, atardecer_verano):
    """
    Determina el estado del relé de ponedoras (normal cerrado, activo en bajo).
    - Se activa (enciende luz) entre el amanecer de verano y el amanecer actual.
    - Se activa (enciende luz) entre el atardecer actual y el atardecer de verano.
    - El resto del tiempo, desactivado (luz apagada).
    Retorna 0 para activar (cerrar circuito, luz encendida), 1 para desactivar (abrir circuito, luz apagada).
    """
    if amanecer_verano <= hora_actual < amanecer_actual:
        return 0
    if atardecer_actual <= hora_actual < atardecer_verano:
        return 0
    return 1

def relay_pollitos_state(temp, umbral=28):
    """
    Determina el estado del relé de pollitos (normal abierto, activo en alto).
    - Si la temperatura ambiente es mayor al umbral, se activa el relé (apaga la calefacción).
    - Si la temperatura es menor o igual al umbral, desactiva el relé (enciende la calefacción).
    Retorna 1 para activar (abrir circuito, calefacción apagada), 0 para desactivar (cerrar circuito, calefacción encendida).
    """
    return 1 if temp > umbral else 0
