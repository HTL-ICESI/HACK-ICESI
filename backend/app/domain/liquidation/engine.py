"""
M4 — Motor de liquidación de prestaciones. NÚCLEO DETERMINISTA.

Funciones puras: mismo input -> mismo output, sin I/O, sin LLM. Cada función
implementa una fórmula del CST. ESTO es lo que el jurado audita como confiabilidad.

Contrato de testing: dado el caso gold (José Ospino), el total coincide ±$1.
Reglas que el gold enseña:
  - La base de liquidación se COMPONE: básico + promedio_variable + auxilio_transporte.
  - Cesantías, intereses y prima usan la base CON auxilio.
  - Vacaciones usa la base SIN auxilio y se calcula sobre DÍAS PENDIENTES.
  - La indemnización depende del MOTIVO de terminación (renuncia -> 0).
"""
from __future__ import annotations

from dataclasses import dataclass

from app.domain.liquidation import constants as K


@dataclass(frozen=True)
class LiquidationInput:
    salario_basico: float                  # COP, salario básico mensual (con source en M2)
    promedio_variable: float = 0.0         # promedio último año de comisiones/HE (de novedad_nomina)
    auxilio_transporte: float = 0.0        # COP, si aplica (salario <= 2 SMLMV)
    days_worked: int = 0                   # días del período liquidado (base 360)
    dias_pendientes_vacaciones: int = 0    # días de vacaciones causados y no tomados
    vinculo_type: str = "termino_indefinido"
    termination_cause: str = "renuncia"    # renuncia|justa_causa|sin_justa_causa|mutuo_acuerdo|transaccion
    months_remaining_fixed: int = 0        # término fijo: meses que faltaban (indemnización art. 64)
    antiguedad_anios: float = 0.0          # indefinido: antigüedad para la tabla art. 64
    bonificacion: float = 0.0              # transacción: bonificación acordada


@dataclass(frozen=True)
class LiquidationResult:
    cesantias: float
    intereses_cesantias: float
    prima: float
    vacaciones: float
    total_prestaciones: float   # cesantías + intereses + prima + vacaciones (= "TOTAL LIQUIDACIÓN" del formato HG)
    indemnizacion: float        # se reporta y paga aparte de las prestaciones
    total: float                # total_prestaciones + indemnización = exposición económica total


# --------------------------------------------------------------------------- #
# Composición de la base (regla del caso gold)
# --------------------------------------------------------------------------- #
def salario_base_liquidacion(basico: float, promedio_variable: float, auxilio: float) -> float:
    """Base CON auxilio: la que usan cesantías, intereses y prima."""
    return basico + promedio_variable + auxilio


def salario_base_ordinario(basico: float, promedio_variable: float) -> float:
    """Base SIN auxilio (el auxilio de transporte no es salario): vacaciones e indemnización."""
    return basico + promedio_variable


# --------------------------------------------------------------------------- #
# Prestaciones (fórmulas CST). Las funciones escalares se mantienen estables.
# --------------------------------------------------------------------------- #
def cesantias(salary: float, days: int) -> float:
    """Art. 249 CST: un mes de salario por año -> salario * días / 360."""
    return salary * days / K.DIAS_ANIO_LABORAL


def intereses_cesantias(cesantias_value: float, days: int) -> float:
    """Art. 99 Ley 50/1990: 12% anual sobre cesantías, proporcional a los días."""
    return cesantias_value * K.INTERES_CESANTIAS * days / K.DIAS_ANIO_LABORAL


def prima(salary: float, days_semester: int) -> float:
    """Art. 306 CST: 15 días por semestre -> salario * días_semestre / 360."""
    return salary * days_semester / K.DIAS_ANIO_LABORAL


def vacaciones(salary: float, days: int) -> float:
    """Art. 186 CST (acumulación): 15 días hábiles por año -> salario * días / 720."""
    return salary * days / (K.DIAS_ANIO_LABORAL * 2)


def vacaciones_pendientes(base_sin_auxilio: float, dias_pendientes: int) -> float:
    """Vacaciones por DÍAS PENDIENTES (método del caso gold): base_sin_aux/30 * días.
    Excluye el auxilio de transporte (no es salario para efectos de vacaciones)."""
    return base_sin_auxilio / 30 * dias_pendientes


def indemnizacion(inp: LiquidationInput) -> float:
    """
    Indemnización por terminación (art. 64 CST). Depende del MOTIVO:
      - renuncia / justa_causa / mutuo_acuerdo -> 0 (solo prestaciones).
      - transaccion -> la bonificación acordada.
      - sin_justa_causa:
          * término fijo -> salarios que faltaban para terminar el contrato.
          * indefinido (< 10 SMLMV) -> 30 días por el primer año + 20 por año adicional.
    La indemnización se calcula sobre el salario ordinario (sin auxilio de transporte).
    """
    base = salario_base_ordinario(inp.salario_basico, inp.promedio_variable)
    cause = inp.termination_cause

    if cause == "transaccion":
        return inp.bonificacion
    if cause != "sin_justa_causa":
        return 0.0  # renuncia, justa causa, mutuo acuerdo

    if inp.vinculo_type == "termino_fijo":
        # Salarios correspondientes al tiempo que faltaba (meses * salario mensual).
        return base * inp.months_remaining_fixed

    # Término indefinido, < 10 SMLMV: 30 días primer año + 20 por año adicional.
    salario_diario = base / 30
    dias = 30 + 20 * max(0.0, inp.antiguedad_anios - 1)
    return salario_diario * dias


def liquidate(inp: LiquidationInput) -> LiquidationResult:
    """
    Compone todas las prestaciones. Pura y total. Replica el formato real de HG:
      - Cesantías, intereses y prima sobre la base CON auxilio.
      - Vacaciones (ver abajo) sobre la base SIN auxilio.
      - Indemnización aparte (según motivo). El 'total' es la exposición completa.
    """
    base = salario_base_liquidacion(inp.salario_basico, inp.promedio_variable, inp.auxilio_transporte)
    base_ord = salario_base_ordinario(inp.salario_basico, inp.promedio_variable)

    ces = cesantias(base, inp.days_worked)
    int_ces = intereses_cesantias(ces, inp.days_worked)
    pri = prima(base, inp.days_worked)

    # Dos métodos de vacaciones (ambos en el formato real de HG):
    #  - Hay SALDO acumulado no disfrutado (días pendientes) -> base_sin_aux/30 * días.
    #  - No hay saldo -> acumulación proporcional al período liquidado -> base_sin_aux * días/720.
    if inp.dias_pendientes_vacaciones > 0:
        vac = vacaciones_pendientes(base_ord, inp.dias_pendientes_vacaciones)
    else:
        vac = vacaciones(base_ord, inp.days_worked)

    total_prest = ces + int_ces + pri + vac
    ind = indemnizacion(inp)

    return LiquidationResult(
        cesantias=ces,
        intereses_cesantias=int_ces,
        prima=pri,
        vacaciones=vac,
        total_prestaciones=total_prest,
        indemnizacion=ind,
        total=total_prest + ind,
    )
