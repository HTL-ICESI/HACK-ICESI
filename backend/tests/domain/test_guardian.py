"""
Tests del Guardián de debido proceso (J3). La joya, probada como código puro.
Spec: PROCESO-DISCIPLINARIO.md — 7 garantías del art. 115 → CONFORME/PARCIAL/NULO.
100% determinista: mismo estado → mismo veredicto. Cero LLM.
"""
from app.domain.disciplinary.guardian import (
    Clasificacion, DiligenceState, evaluate,
)


def _full_ok() -> DiligenceState:
    return DiligenceState(
        falta_tipificada=True,
        comunicacion_apertura_formal=True, formulacion_cargos_concretos=True,
        traslado_pruebas=True, termino_defensa_minimo=True,
        oportunidad_descargos=True, decision_motivada=True, derecho_impugnacion=True,
    )


def test_diligencia_completa_es_conforme_y_puede_proceder():
    verdict = evaluate(_full_ok())
    assert verdict.clasificacion == Clasificacion.CONFORME
    assert verdict.nullity_alert is False
    assert verdict.can_proceed is True
    assert verdict.vicios == []


def test_falta_oportunidad_descargos_dispara_nulidad():
    # Garantía de severidad ALTA ausente → NULO directo (§8).
    state = DiligenceState(
        falta_tipificada=True,
        comunicacion_apertura_formal=True, formulacion_cargos_concretos=True,
        traslado_pruebas=True, termino_defensa_minimo=True,
        oportunidad_descargos=False, decision_motivada=True, derecho_impugnacion=True,
    )
    verdict = evaluate(state)
    assert verdict.clasificacion == Clasificacion.NULO
    assert verdict.nullity_alert is True
    assert verdict.can_proceed is False
    assert any("oportunidad_descargos" == v.garantia for v in verdict.vicios)


def test_termino_menor_a_5_dias_es_nulo():
    state = DiligenceState(
        falta_tipificada=True,
        comunicacion_apertura_formal=True, formulacion_cargos_concretos=True,
        traslado_pruebas=True, termino_defensa_minimo=False,   # < 5 días hábiles
        oportunidad_descargos=True, decision_motivada=True, derecho_impugnacion=True,
    )
    verdict = evaluate(state)
    assert verdict.clasificacion == Clasificacion.NULO
    assert any("art. 115" in v.norma for v in verdict.vicios)


def test_vicio_subsanable_es_parcial_no_nulo():
    # Solo falta la doble instancia (severidad no fuerza nulidad) → PARCIAL.
    state = DiligenceState(
        falta_tipificada=True,
        comunicacion_apertura_formal=True, formulacion_cargos_concretos=True,
        traslado_pruebas=True, termino_defensa_minimo=True,
        oportunidad_descargos=True, decision_motivada=True, derecho_impugnacion=False,
    )
    verdict = evaluate(state)
    assert verdict.clasificacion == Clasificacion.PARCIAL
    assert verdict.can_proceed is False


def test_falta_no_tipificada_es_nulo_de_origen():
    state = DiligenceState(falta_tipificada=False)  # art. 114
    verdict = evaluate(state)
    assert verdict.clasificacion == Clasificacion.NULO
    assert any("114" in v.norma for v in verdict.vicios)


def test_es_determinista():
    state = DiligenceState(comunicacion_apertura_formal=True)
    assert evaluate(state) == evaluate(state)   # mismo input -> mismo veredicto
