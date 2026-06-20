"""
Parámetros laborales por año. Fuente única de constantes para el motor determinista.
David valida estos valores; aquí viven versionados por año (escalabilidad normativa).
"""
from __future__ import annotations

# SMLMV = salario mínimo legal mensual vigente. David confirma el valor 2026.
SMLMV: dict[int, float] = {
    2026: 1_423_500.0,   # [VERIFICAR con David]
}

AUXILIO_TRANSPORTE: dict[int, float] = {
    2026: 200_000.0,     # [VERIFICAR con David] aplica si salario <= 2 SMLMV
}

# Factores fijos del CST
INTERES_CESANTIAS = 0.12        # anual, art. 99 Ley 50/1990
DIAS_ANIO_LABORAL = 360         # base de liquidación laboral colombiana
JORNADA_MAX_2026 = 42           # horas/semana, Ley 2101/2021 (vigor pleno 2026)


def smlmv(year: int) -> float:
    if year not in SMLMV:
        raise KeyError(f"SMLMV no parametrizado para {year}. Pídeselo a David.")
    return SMLMV[year]
