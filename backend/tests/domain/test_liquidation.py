"""
Tests del motor de liquidación (M4). Contrato: coincide con el formato REAL de HG.
Valores tomados directo de `icesi-playbook/Liquidación Formato.xlsx` (data_only),
hojas "JOSÉ OSPINO" (renuncia) y "formato" (sin justa causa + indemnización).
"""
import pytest

from app.domain.liquidation.engine import (
    cesantias,
    prima,
    vacaciones,
    vacaciones_pendientes,
    salario_base_liquidacion,
    indemnizacion,
    liquidate,
    LiquidationInput,
)


def test_cesantias_anio_completo_es_un_salario():
    assert cesantias(salary=2_000_000, days=360) == pytest.approx(2_000_000)


def test_prima_semestre_completo():
    assert prima(salary=2_000_000, days_semester=180) == pytest.approx(1_000_000)


def test_vacaciones_anio_completo_es_medio_salario():
    # método de acumulación /720: 360 días -> salario/2
    assert vacaciones(salary=2_000_000, days=360) == pytest.approx(1_000_000)


# ─────────────────────────────────────────────────────────────────────────────
# GOLD 1 — JOSÉ OSPINO (hoja "JOSÉ OSPINO"): renuncia, vacaciones por días
# pendientes. Valores EXACTOS del Excel (promedio = 676.784,614, no redondeado).
# ─────────────────────────────────────────────────────────────────────────────
GOLD_OSPINO = LiquidationInput(
    salario_basico=1_750_905,
    promedio_variable=676_784.614,     # (ENERO 1.353.569,228 + FEBRERO 0) / 2
    auxilio_transporte=249_095,
    days_worked=66,                    # 01 ene – 06 mar 2026
    dias_pendientes_vacaciones=9,      # causados y no disfrutados (tomó 8 antes)
    vinculo_type="termino_indefinido",
    termination_cause="renuncia",
)


def test_gold_ospino_componentes_exactos():
    r = liquidate(GOLD_OSPINO)
    assert r.cesantias == pytest.approx(490_743.846, abs=0.5)
    assert r.intereses_cesantias == pytest.approx(10_796.365, abs=0.5)
    assert r.prima == pytest.approx(490_743.846, abs=0.5)
    assert r.vacaciones == pytest.approx(728_306.884, abs=0.5)   # 2.427.690/30*9
    assert r.indemnizacion == 0.0                                # renuncia


def test_gold_ospino_total_exacto():
    r = liquidate(GOLD_OSPINO)
    # El Excel da 1.720.590,9406 — el motor debe coincidir al centavo.
    assert r.total_prestaciones == pytest.approx(1_720_590.94, abs=0.5)
    assert r.total == pytest.approx(1_720_590.94, abs=0.5)       # sin indemnización


def test_gold_base_se_compone_con_auxilio():
    # 1.750.905 + 676.784,614 + 249.095 = 2.676.784,614
    assert salario_base_liquidacion(1_750_905, 676_784.614, 249_095) == pytest.approx(2_676_784.614, abs=0.01)


# ─────────────────────────────────────────────────────────────────────────────
# GOLD 2 — hoja "formato": sin justa causa, <1 año, vacaciones por ACUMULACIÓN
# (×días/720) + indemnización de 30 días (primer año). Valores EXACTOS del Excel.
# ─────────────────────────────────────────────────────────────────────────────
GOLD_FORMATO = LiquidationInput(
    salario_basico=1_750_905,
    promedio_variable=0,
    auxilio_transporte=249_095,        # base con auxilio = 2.000.000
    days_worked=109,                   # 16 ene – 04 may 2026
    dias_pendientes_vacaciones=0,      # sin saldo -> acumulación proporcional
    vinculo_type="termino_indefinido",
    termination_cause="sin_justa_causa",
    antiguedad_anios=0.3,              # < 1 año
)


def test_gold_formato_componentes_exactos():
    r = liquidate(GOLD_FORMATO)
    assert r.cesantias == pytest.approx(605_555.56, abs=0.5)         # 2.000.000*109/360
    assert r.intereses_cesantias == pytest.approx(22_001.85, abs=0.5)
    assert r.prima == pytest.approx(605_555.56, abs=0.5)
    assert r.vacaciones == pytest.approx(265_067.56, abs=0.5)        # 1.750.905*109/720 (acumulación)


def test_gold_formato_total_prestaciones_excluye_indemnizacion():
    r = liquidate(GOLD_FORMATO)
    # "TOTAL LIQUIDACIÓN" del Excel = solo prestaciones = 1.498.180,53
    assert r.total_prestaciones == pytest.approx(1_498_180.53, abs=0.5)


def test_gold_formato_indemnizacion_30_dias_primer_anio():
    r = liquidate(GOLD_FORMATO)
    # Indemnización art. 64 indefinido <1 año = 30 días = 1 salario básico = 1.750.905
    assert r.indemnizacion == pytest.approx(1_750_905, abs=1)
    # El total general SÍ suma indemnización (exposición económica completa)
    assert r.total == pytest.approx(1_498_180.53 + 1_750_905, abs=1)


# ─────────────────────────────────────────────────────────────────────────────
# Reglas de indemnización y robustez
# ─────────────────────────────────────────────────────────────────────────────
def test_vacaciones_excluye_auxilio_de_transporte():
    con_aux = vacaciones_pendientes(2_676_785, 9)
    sin_aux = vacaciones_pendientes(2_427_690, 9)
    assert sin_aux < con_aux


def test_dos_metodos_de_vacaciones_difieren():
    # Mismo período, con/sin días pendientes -> métodos distintos, resultados distintos.
    con_saldo = liquidate(GOLD_OSPINO).vacaciones
    sin_saldo = liquidate(LiquidationInput(
        salario_basico=1_750_905, promedio_variable=676_784.614, auxilio_transporte=249_095,
        days_worked=66, dias_pendientes_vacaciones=0,
        vinculo_type="termino_indefinido", termination_cause="renuncia",
    )).vacaciones
    assert con_saldo != sin_saldo


def test_termino_fijo_indemnizacion_salarios_faltantes():
    inp = LiquidationInput(
        salario_basico=1_500_000, days_worked=180,
        vinculo_type="termino_fijo", termination_cause="sin_justa_causa",
        months_remaining_fixed=4,
    )
    assert indemnizacion(inp) == pytest.approx(1_500_000 * 4, abs=1)


def test_indefinido_indemnizacion_anios_adicionales():
    # 3 años -> 30 (primer año) + 20*2 (adicionales) = 70 días.
    inp = LiquidationInput(
        salario_basico=2_000_000, days_worked=360,
        vinculo_type="termino_indefinido", termination_cause="sin_justa_causa",
        antiguedad_anios=3,
    )
    assert indemnizacion(inp) == pytest.approx(2_000_000 / 30 * 70, abs=1)


def test_renuncia_no_genera_indemnizacion():
    assert indemnizacion(GOLD_OSPINO) == 0.0


def test_liquidacion_es_determinista():
    assert liquidate(GOLD_OSPINO) == liquidate(GOLD_OSPINO)
    assert liquidate(GOLD_FORMATO) == liquidate(GOLD_FORMATO)


# ─────────────────────────────────────────────────────────────────────────────
# Casos borde y robustez del motor
# ─────────────────────────────────────────────────────────────────────────────
from app.domain.liquidation.engine import intereses_cesantias


def test_cesantias_incluye_auxilio_en_la_base():
    # Base CON auxilio: 1.000.000 básico + 200.000 auxilio = 1.200.000.
    r = liquidate(LiquidationInput(
        salario_basico=1_000_000, auxilio_transporte=200_000, days_worked=360,
        vinculo_type="termino_indefinido", termination_cause="renuncia"))
    assert r.cesantias == pytest.approx(1_200_000, abs=1)   # 1.200.000 * 360/360
    assert r.prima == pytest.approx(1_200_000, abs=1)


def test_dias_cero_prestaciones_en_cero():
    r = liquidate(LiquidationInput(
        salario_basico=2_000_000, days_worked=0,
        vinculo_type="termino_indefinido", termination_cause="renuncia"))
    assert r.cesantias == 0 and r.prima == 0 and r.vacaciones == 0
    assert r.total_prestaciones == 0
    assert r.total == 0


def test_total_es_prestaciones_mas_indemnizacion():
    r = liquidate(LiquidationInput(
        salario_basico=2_000_000, days_worked=180,
        vinculo_type="termino_indefinido", termination_cause="sin_justa_causa",
        antiguedad_anios=2))
    assert r.total == pytest.approx(r.total_prestaciones + r.indemnizacion, abs=0.01)


def test_intereses_cesantias_es_12pct_proporcional():
    # 1.000.000 de cesantías por 360 días -> 12% = 120.000.
    assert intereses_cesantias(1_000_000, 360) == pytest.approx(120_000, abs=1)


@pytest.mark.parametrize("cause", ["justa_causa", "mutuo_acuerdo", "renuncia"])
def test_causas_sin_indemnizacion(cause):
    inp = LiquidationInput(
        salario_basico=2_000_000, days_worked=180,
        vinculo_type="termino_indefinido", termination_cause=cause, antiguedad_anios=5)
    assert indemnizacion(inp) == 0.0


def test_transaccion_indemnizacion_es_la_bonificacion():
    r = liquidate(LiquidationInput(
        salario_basico=2_000_000, days_worked=180,
        vinculo_type="termino_indefinido", termination_cause="transaccion",
        bonificacion=5_000_000))
    assert r.indemnizacion == 5_000_000
    assert r.total == pytest.approx(r.total_prestaciones + 5_000_000, abs=0.01)


def test_indemnizacion_primer_anio_exacto_30_dias():
    # Indefinido, antigüedad exacta de 1 año -> 30 días = 1 salario.
    inp = LiquidationInput(
        salario_basico=3_000_000, days_worked=360,
        vinculo_type="termino_indefinido", termination_cause="sin_justa_causa",
        antiguedad_anios=1)
    assert indemnizacion(inp) == pytest.approx(3_000_000, abs=1)


def test_indemnizacion_crece_con_antiguedad():
    def ind(a):
        return indemnizacion(LiquidationInput(
            salario_basico=2_000_000, days_worked=360, vinculo_type="termino_indefinido",
            termination_cause="sin_justa_causa", antiguedad_anios=a))
    assert ind(1) < ind(2) < ind(5)


def test_vacaciones_pendientes_escala_lineal():
    assert vacaciones_pendientes(3_000_000, 10) == pytest.approx(
        2 * vacaciones_pendientes(3_000_000, 5), abs=1)


def test_solo_basico_sin_variable_ni_auxilio():
    # Sin promedio ni auxilio, la base es el básico puro.
    r = liquidate(LiquidationInput(
        salario_basico=1_500_000, days_worked=360,
        vinculo_type="termino_indefinido", termination_cause="renuncia"))
    assert r.cesantias == pytest.approx(1_500_000, abs=1)
