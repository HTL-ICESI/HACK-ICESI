"""
Convierte el resultado de UNA llamada de descargos en el `DiligenceState` (las 7
garantías) que evalúa el guardián (J3). Port de AFFIRMA `src/ingest.py`.

Camino limpio: usa el Data Collection estructurado del agente.
Fallback: heurística determinista sobre la transcripción. NUNCA inventa un "sí":
ante la duda, la garantía se asume ausente (lo seguro → el guardián la marca).

Notas de mapeo (llamada → 7 garantías del art. 115):
  charges_read                 -> formulacion_cargos_concretos (G2)
  evidence_presented           -> traslado_pruebas             (G3)
  prior_defense_term_respected -> termino_defensa_minimo        (G4)  [override determinista posible]
  worker_allowed_to_respond    -> oportunidad_descargos         (G5)
  motivated_decision_announced -> decision_motivada             (G6)
  right_to_appeal_notified     -> derecho_impugnacion           (G7)
  right_to_companion_notified  -> derecho_acompanamiento_informado (vicio MEDIA)

G1 (comunicación formal de apertura) la diligencia la presupone; el backend puede
fijarla con el documento de citación real. Por defecto True salvo override.
"""

from __future__ import annotations

import re

from app.domain.disciplinary.guardian import DiligenceState

_AFFIRM = re.compile(r"\b(s[ií]|claro|correcto|de acuerdo|as[ií] es|entend[íi])\b", re.I)


def _truthy(v) -> bool:
    if isinstance(v, dict):
        v = v.get("value")
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in {"true", "verdadero", "sí", "si", "yes"}
    return False


def diligence_state_from_payload(
    payload: dict, *,
    term_respected: bool | None = None,
    tipo_actuacion: str = "sancion_disciplinaria",
    num_trabajadores: int = 50,
    falta_tipificada: bool = True,
    comunicacion_apertura_formal: bool = True,
    worker_is_unionized: bool | None = None,
) -> DiligenceState:
    """Construye el DiligenceState (7 garantías) desde lo capturado en la llamada.

    `term_respected` (G4) prioridad: override determinista del backend (cómputo de
    fechas) > lo confirmado por el trabajador (`prior_defense_term_respected`) > True.
    Los campos de contexto (tipo_actuacion, num_trabajadores, falta_tipificada) los
    decide el backend, no la llamada.
    """
    if term_respected is None:
        term_respected = (_truthy(payload["prior_defense_term_respected"])
                          if "prior_defense_term_respected" in payload else True)
    if worker_is_unionized is None:
        worker_is_unionized = _truthy(payload.get("union_representation_notified")) or \
            _truthy(payload.get("worker_is_unionized"))

    return DiligenceState(
        falta_tipificada=falta_tipificada,
        tipo_actuacion=tipo_actuacion,
        comunicacion_apertura_formal=comunicacion_apertura_formal,
        formulacion_cargos_concretos=_truthy(payload.get("charges_read")),
        traslado_pruebas=_truthy(payload.get("evidence_presented")),
        termino_defensa_minimo=bool(term_respected),
        oportunidad_descargos=_truthy(payload.get("worker_allowed_to_respond")),
        decision_motivada=_truthy(payload.get("motivated_decision_announced")),
        derecho_impugnacion=_truthy(payload.get("right_to_appeal_notified")),
        num_trabajadores=num_trabajadores,
        worker_is_unionized=bool(worker_is_unionized),
        derecho_acompanamiento_informado=_truthy(payload.get("right_to_companion_notified")),
    )


def diligence_state_from_conversation(conv: dict, **kwargs) -> DiligenceState:
    """Desde la conversación de ElevenLabs (Data Collection estructurado y, si falta,
    heurística sobre la transcripción)."""
    dc = ((conv.get("analysis") or {}).get("data_collection_results")) or {}
    if dc:
        return diligence_state_from_payload(dc, **kwargs)

    # Fallback: heurística determinista sobre la transcripción.
    turns = [t for t in (conv.get("transcript") or []) if (t.get("message") or "").strip()]

    def next_user(i: int) -> str:
        for t in turns[i + 1:]:
            if t.get("role") == "user":
                return (t.get("message") or "").strip()
        return ""

    f = {"companion": False, "charges": False, "evidence": False,
         "respond": False, "motivada": False, "impugnar": False}
    for i, t in enumerate(turns):
        if t.get("role") != "agent":
            continue
        low = (t.get("message") or "").lower()
        if any(w in low for w in ["acompañad", "acompanad", "sindicato", "abogado de su confianza"]):
            f["companion"] = True
        if any(w in low for w in ["cargos", "se le imputa", "los hechos"]):
            f["charges"] = True
        if "prueba" in low:
            f["evidence"] = True
        if "descargos" in low and any(w in low for w in ["la palabra", "su versión", "su version"]):
            if _AFFIRM.search(next_user(i)) or len(next_user(i)) > 20:
                f["respond"] = True
        if "motivada" in low or "por escrito" in low:
            f["motivada"] = True
        if "impugnar" in low or "recurso" in low or "apelación" in low or "apelacion" in low:
            f["impugnar"] = True

    payload = {
        "right_to_companion_notified": f["companion"],
        "charges_read": f["charges"],
        "evidence_presented": f["evidence"],
        "worker_allowed_to_respond": f["respond"],
        "motivated_decision_announced": f["motivada"],
        "right_to_appeal_notified": f["impugnar"],
    }
    return diligence_state_from_payload(payload, **kwargs)
