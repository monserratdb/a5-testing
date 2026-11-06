"""Tu implementacion de Spectrum-Based Fault Localization - Actividad 5.

El notebook te entrega el espectro ya calculado. Tu trabajo es la formula.

El espectro es un dict con:

    espectro["lineas"]  lista de lineas ejecutables del programa
    espectro["nf"]      cuantos tests fallan en total
    espectro["np"]      cuantos tests pasan en total
    espectro["ef"][l]   tests que FALLAN y ejecutan la linea l
    espectro["ep"][l]   tests que PASAN  y ejecutan la linea l
    espectro["tests"]   la matriz cruda, por si la necesitas

Debes devolver un dict {linea: puntaje}, donde mas alto es mas sospechoso.
"""

import math


# ==========================================================================
# EJEMPLO RESUELTO - Tarantula
# ==========================================================================

def tarantula(espectro):
    """Formula de Tarantula. Sirve de ejemplo del contrato de entrada y salida."""
    nf, np_ = espectro["nf"], espectro["np"]
    puntajes = {}
    for l in espectro["lineas"]:
        ef, ep = espectro["ef"][l], espectro["ep"][l]
        a = ef / nf if nf else 0.0
        b = ep / np_ if np_ else 0.0
        puntajes[l] = a / (a + b) if (a + b) else 0.0
    return puntajes


# ==========================================================================
# TU TRABAJO
# ==========================================================================

def ochiai(espectro):
    """Implementa Ochiai.

                            ef(l)
        ochiai(l) = -----------------------
                     sqrt( nf * (ef + ep) )

    donde ef y ep son los de la linea l, y nf es el total de tests que fallan.
    Cuida el caso en que el denominador sea cero.
    """
    nf = espectro["nf"]
    puntajes = {}
    for l in espectro["lineas"]:
        ef, ep = espectro["ef"][l], espectro["ep"][l]
        denominador = math.sqrt(nf * (ef + ep))
        puntajes[l] = ef / denominador if denominador else 0.0
    return puntajes
