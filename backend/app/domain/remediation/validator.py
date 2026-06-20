"""
M5 — Validador determinista de cifras en documentos generados.

Principio anti-alucinación: TODA cifra inyectada por el motor debe aparecer
literalmente en el cuerpo del documento. Si falta una sola → blocked.

Función pura: mismo input → mismo veredicto (determinista por diseño).
El jurado audita que NINGUNA cifra venga del LLM; este validador es el guardián.
"""
from __future__ import annotations


def validate_figures(body: str, figures: dict) -> bool:
    """
    Verifica que cada valor numérico de `figures` aparezca en `body`.

    Normaliza float enteros (42.0 → "42") para comparar con el texto.
    Cadenas y enteros se comparan directamente.
    Retorna False en cuanto falta el primer valor — no acumula errores.
    """
    for _key, value in figures.items():
        if isinstance(value, float) and value.is_integer():
            str_val = str(int(value))
        else:
            str_val = str(value)
        if str_val not in body:
            return False
    return True
