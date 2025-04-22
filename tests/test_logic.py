import pytest
from src.logic import relay_ponedoras_state, relay_pollitos_state

def test_relay_ponedoras_state():
    # Amanecer verano: 5, Amanecer actual: 7, Atardecer actual: 18, Atardecer verano: 21
    # Entre 5 y 7: luz encendida
    assert relay_ponedoras_state(5, 5, 7, 18, 21) == 0
    assert relay_ponedoras_state(6, 5, 7, 18, 21) == 0
    # Entre 7 y 18: luz apagada
    assert relay_ponedoras_state(8, 5, 7, 18, 21) == 1
    # Entre 18 y 21: luz encendida
    assert relay_ponedoras_state(19, 5, 7, 18, 21) == 0
    assert relay_ponedoras_state(20, 5, 7, 18, 21) == 0
    # Fuera de esos rangos: luz apagada
    assert relay_ponedoras_state(22, 5, 7, 18, 21) == 1

def test_relay_pollitos_state():
    # Temperatura mayor al umbral: calefacción apagada
    assert relay_pollitos_state(29) == 1
    assert relay_pollitos_state(28.1) == 1
    # Temperatura igual o menor al umbral: calefacción encendida
    assert relay_pollitos_state(28) == 0
    assert relay_pollitos_state(20) == 0
