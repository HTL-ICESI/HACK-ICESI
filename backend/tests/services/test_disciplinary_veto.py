"""
El VETO del guardián (la joya): la decisión sancionatoria NO se emite como válida si
hay una nulidad pendiente. Es la demostración de valor del Motor 2.

El service corre sobre el guardián de 7 garantías; el estado entra ya mapeado (5→7 lo
hace el router). `generate_documents` emite siempre los 3 docs y marca la decisión
bloqueada; `generate_final_decision` aplica el VETO duro (lanza BlockedOutput).
"""
import pytest

from app.core.audit import AuditLog
from app.core.errors import BlockedOutput
from app.core.tenancy import TenantContext
from app.adapters.llm.claude_client import ClaudeClient
from app.domain.disciplinary.guardian import DiligenceState
from app.services.disciplinary_service import DisciplinaryService

svc = DisciplinaryService(ClaudeClient(), AuditLog())
A_CTX = TenantContext(tenant_id="empresa-A")

COMPLETA = DiligenceState(
    falta_tipificada=True,
    comunicacion_apertura_formal=True, formulacion_cargos_concretos=True,
    traslado_pruebas=True, termino_defensa_minimo=True,
    oportunidad_descargos=True, decision_motivada=True, derecho_impugnacion=True,
)
INCOMPLETA = DiligenceState(  # falta la oportunidad de descargos (art. 115 CST) → NULO
    falta_tipificada=True,
    comunicacion_apertura_formal=True, formulacion_cargos_concretos=True,
    traslado_pruebas=True, termino_defensa_minimo=True,
    oportunidad_descargos=False, decision_motivada=True, derecho_impugnacion=True,
)


def test_guardian_detecta_nulidad_y_no_puede_proceder():
    out = svc.run_guardian(A_CTX, INCOMPLETA)
    assert out["nullity_alert"] is True
    assert out["can_proceed"] is False


async def test_documents_emite_3_y_marca_decision_bloqueada_si_nulo():
    # generate_documents NO lanza: emite citación + acta + decisión vetada.
    res = await svc.generate_documents(A_CTX, INCOMPLETA, transcript="...")
    tipos = [d["type"] for d in res["documents"]]
    assert tipos == ["citacion_descargos", "acta_descargos", "decision_final"]
    decision = next(d for d in res["documents"] if d["type"] == "decision_final")
    assert decision["blocked_if_nullity"] is True
    assert "BLOQUEADA" in decision["body_markdown"]


async def test_decision_dura_bloqueada_si_hay_nulidad():
    with pytest.raises(BlockedOutput):
        await svc.generate_final_decision(A_CTX, INCOMPLETA)


async def test_decision_se_emite_si_diligencia_completa():
    res = await svc.generate_final_decision(A_CTX, COMPLETA)
    assert res["clasificacion"] == "CONFORME"
    assert res["documents"][0]["type"] == "decision_final"
