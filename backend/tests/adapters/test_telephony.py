"""
Prueba aislada de J1 (telefonía de descargos) — SIN red ni credenciales.

Verifica el contrato que importa: que lo capturado en la llamada se convierte en
el DiligenceState (7 garantías) correcto y que el guardián decide la clasificación.
"""
from __future__ import annotations

from app.adapters.telephony import descargos_agent as agent
from app.adapters.telephony.mapping import (
    diligence_state_from_payload,
    diligence_state_from_conversation,
)
from app.domain.disciplinary.guardian import Clasificacion, Severidad, evaluate


def _full_payload(**over) -> dict:
    """Payload de una diligencia completa y conforme."""
    p = {
        "right_to_companion_notified": True,
        "charges_read": True,
        "evidence_presented": True,
        "prior_defense_term_respected": True,
        "worker_allowed_to_respond": True,
        "motivated_decision_announced": True,
        "right_to_appeal_notified": True,
    }
    p.update(over)
    return p


# --- el agente: el flujo y la extracción están bien formados -------------------

def test_data_collection_cubre_las_garantias():
    ids = {item["identifier"] for item in agent.data_collection_schema()}
    assert {
        "right_to_companion_notified", "charges_read", "evidence_presented",
        "prior_defense_term_respected", "worker_allowed_to_respond",
        "motivated_decision_announced", "right_to_appeal_notified",
    } <= ids


def test_resolved_prompt_no_deja_placeholders_de_caso():
    case = agent.sample_case()
    res = agent.resolved_prompts(case)
    assert "{{worker_name}}" not in res["system_prompt"]
    assert "{{charges_summary}}" not in res["system_prompt"]
    assert case.worker_name in res["first_message"]
    tool = agent.submit_descargos_tool()
    assert tool["api_schema"]["request_headers"]["X-HG-Secret"] == "{{secret__backend_token}}"


# --- el mapeo + el guardián: el veredicto es determinista ----------------------

def test_diligencia_completa_es_conforme():
    v = evaluate(diligence_state_from_payload(_full_payload()))
    assert v.clasificacion == Clasificacion.CONFORME
    assert v.can_proceed is True and v.nullity_alert is False


def test_falta_oportunidad_descargos_es_nulo():
    v = evaluate(diligence_state_from_payload(_full_payload(worker_allowed_to_respond=False)))
    assert v.clasificacion == Clasificacion.NULO
    assert v.can_proceed is False


def test_payload_vacio_es_nulo_no_inventa_si():
    # payload vacío -> faltan garantías núcleo (lo seguro), nunca un 'sí' inventado.
    v = evaluate(diligence_state_from_payload({}))
    assert v.clasificacion == Clasificacion.NULO


def test_termino_previo_no_respetado_dispara_nulidad():
    v = evaluate(diligence_state_from_payload(_full_payload(prior_defense_term_respected=False)))
    assert v.clasificacion == Clasificacion.NULO
    assert any("Circular 0048/2026" in vi.norma for vi in v.vicios)


def test_override_determinista_gana_sobre_la_llamada():
    # El backend calculó (fechas) que el término SÍ se respetó: manda sobre lo dicho.
    p = _full_payload(prior_defense_term_respected=False)
    v = evaluate(diligence_state_from_payload(p, term_respected=True))
    assert v.clasificacion == Clasificacion.CONFORME


def test_acompanamiento_omitido_es_parcial():
    # Todo OK menos avisar el acompañante -> vicio MEDIA -> PARCIAL (no NULO).
    v = evaluate(diligence_state_from_payload(_full_payload(right_to_companion_notified=False)))
    assert v.clasificacion == Clasificacion.PARCIAL
    assert any(vi.severidad == Severidad.MEDIA for vi in v.vicios)


def test_mapeo_desde_conversacion_estructurada():
    conv = {"analysis": {"data_collection_results": {
        k: {"value": val} for k, val in _full_payload().items()}}}
    v = evaluate(diligence_state_from_conversation(conv))
    assert v.clasificacion == Clasificacion.CONFORME
