"""
Tests J1 — Pipeline disciplinario.

Todos deterministas: mismo input → mismo output. Sin I/O, sin LLM, sin mocks de red.
Los 12 casos de la spec de aceptación.
"""
from __future__ import annotations

import pytest
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock

from app.core.audit import AuditLog
from app.core.tenancy import TenantContext
from app.domain.disciplinary.config import DisciplinaryConfig
from app.domain.disciplinary.norms import DIAS_HABILES_MINIMOS
from app.domain.disciplinary.pre_citation_checklist import PreCitationChecklist
from app.domain.disciplinary.sanction_engine import recommend
from app.domain.disciplinary.signatures import ActaSignatures
from app.domain.disciplinary.attendees import Attendee
from app.domain.disciplinary.state_machine import (
    ProcessState, TransitionError, validate_transition, working_days_between,
)
from app.services.pipeline_service import PipelineError, PipelineService


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def ctx():
    return TenantContext(tenant_id="empresa-001", actor="abogado@hg.com")


@pytest.fixture
def svc():
    mock_j2j3j4 = MagicMock()
    mock_j2j3j4.run_guardian = MagicMock(return_value={
        "nullity_alert": False, "can_proceed": True,
        "clasificacion": "CONFORME",
        "garantias_ok": 7, "garantias_total": 7,
        "vicios": [], "missing_steps": [],
        "regimen": "completo", "consecuencia": "", "recomendacion": "",
    })
    return PipelineService(disciplinary_svc=mock_j2j3j4, audit=AuditLog())


def _make_full_checklist() -> PreCitationChecklist:
    return PreCitationChecklist(
        worker_id_and_contract=True,
        facts_and_date=True,
        at_least_one_proof=True,
        infringed_norm=True,
    )


def _make_process_with_evidence(svc, ctx):
    """Crea expediente y sube una evidencia (satisface at_least_one_proof)."""
    proc = svc.create_expediente(
        ctx, worker_name="Pedro López", worker_id="CC 123",
        employer_name="Empresa S.A.", contract_type="indefinido",
    )
    svc.add_evidence(
        ctx, proc.process_id,
        filename="correo.eml", file_type="eml",
        file_bytes=b"evidencia",
    )
    return proc


# ── Test 1: expediente → EVIDENCIAS_PENDIENTES ───────────────────────────────

def test_1_create_expediente_initial_state(svc, ctx):
    proc = svc.create_expediente(
        ctx, worker_name="Ana García", worker_id="CC 456",
        employer_name="Empresa S.A.", contract_type="indefinido",
    )
    assert proc.state == ProcessState.EVIDENCIAS_PENDIENTES
    assert proc.tenant_id == "empresa-001"
    assert len(proc.audit_trail) == 1


# ── Test 2: citar sin checklist completo → 422 ───────────────────────────────

def test_2_cite_without_checklist_blocked(svc, ctx):
    proc = svc.create_expediente(
        ctx, worker_name="Carlos Ríos", worker_id="CC 789",
        employer_name="Empresa S.A.", contract_type="fijo",
    )
    incomplete = PreCitationChecklist(
        worker_id_and_contract=True,
        facts_and_date=False,  # faltante
        at_least_one_proof=False,
        infringed_norm=True,
    )
    with pytest.raises(PipelineError, match="Checklist incompleto"):
        svc.cite(
            ctx, proc.process_id,
            citation_date=date.today(),
            checklist=incomplete,
        )


def test_2b_checklist_can_cite_false_when_missing(svc, ctx):
    cl = PreCitationChecklist(
        worker_id_and_contract=True, facts_and_date=False,
        at_least_one_proof=True, infringed_norm=True,
    )
    assert cl.can_cite is False
    assert len(cl.missing_items()) == 1


# ── Test 3: diligencia con < 5 días hábiles → error ─────────────────────────

def test_3_session_too_soon_after_citation(svc, ctx):
    proc = _make_process_with_evidence(svc, ctx)
    citation_date = date(2026, 6, 20)  # viernes
    # Subimos evidencia como comprobante para poder citar
    proc = svc.add_evidence(
        ctx, proc.process_id,
        filename="acuse.pdf", file_type="pdf",
        file_bytes=b"acuse",
        is_notification_proof=True,
    )
    svc.cite(
        ctx, proc.process_id,
        citation_date=citation_date,
        checklist=_make_full_checklist(),
    )
    # Solo 2 días hábiles después (lunes + martes)
    session_date = date(2026, 6, 23)  # martes
    days = working_days_between(citation_date, session_date)
    assert days < DIAS_HABILES_MINIMOS

    with pytest.raises(PipelineError, match=r"día[s]? hábil[es]?"):
        from app.domain.disciplinary.attendees import Attendee
        svc.record_session(
            ctx, proc.process_id,
            session_date=session_date,
            attendees=[Attendee("Instructor", "instructor")],
            signatures=ActaSignatures(
                instructor_signed=True, worker_signed=True, worker_refusal=False,
            ),
        )


# ── Test 4: override de plazo sin motivo → error ─────────────────────────────

def test_4_override_requires_reason():
    with pytest.raises(TransitionError, match="Mínimo legal"):
        validate_transition(
            ProcessState.CITADO, ProcessState.DILIGENCIA_REALIZADA,
            citation_date=date(2026, 6, 20),
            session_date=date(2026, 6, 21),  # 1 día hábil
            min_notice_days=5,
            acta_attendees_registered=True,
            acta_signed_valid=True,
            override_reason=None,
        )


def test_4b_override_with_reason_allowed():
    # Con motivo escrito no lanza
    validate_transition(
        ProcessState.CITADO, ProcessState.DILIGENCIA_REALIZADA,
        citation_date=date(2026, 6, 20),
        session_date=date(2026, 6, 21),
        min_notice_days=5,
        acta_attendees_registered=True,
        acta_signed_valid=True,
        override_reason="Consentimiento expreso del trabajador por escrito",
    )


# ── Test 5: primera inasistencia → proceed_in_absence bloqueado ──────────────

def test_5_first_absence_proceed_blocked(svc, ctx):
    proc = svc.create_expediente(
        ctx, worker_name="Luis Mora", worker_id="CC 111",
        employer_name="Empresa S.A.", contract_type="indefinido",
    )
    with pytest.raises(PipelineError, match="primera inasistencia"):
        svc.record_absence(
            ctx, proc.process_id,
            session_date=date(2026, 6, 25),
            action="proceed_in_absence",
            reason="El trabajador no se presentó",
        )


# ── Test 6: segunda inasistencia (con reprogramación previa) → permitido ─────

def test_6_second_absence_after_reschedule_allowed(svc, ctx):
    proc = svc.create_expediente(
        ctx, worker_name="María Torres", worker_id="CC 222",
        employer_name="Empresa S.A.", contract_type="indefinido",
    )
    # Primera inasistencia: reschedule
    proc = svc.record_absence(
        ctx, proc.process_id,
        session_date=date(2026, 6, 20),
        action="reschedule",
        reason="Trabajador enfermo — reprogramar",
    )
    assert len(proc.absences_with_reschedule()) == 1
    # Segunda inasistencia: proceed_in_absence ya permitido
    proc = svc.record_absence(
        ctx, proc.process_id,
        session_date=date(2026, 6, 27),
        action="proceed_in_absence",
        reason="Segunda inasistencia — se continúa en ausencia",
    )
    assert len(proc.absences) == 2


# ── Test 7: acta sin asistentes → no puede pasar a EN_REVISION ───────────────

def test_7_acta_without_attendees_blocks_revision():
    with pytest.raises(TransitionError, match="asistentes"):
        validate_transition(
            ProcessState.DILIGENCIA_REALIZADA, ProcessState.EN_REVISION,
            acta_attendees_registered=False,
            acta_signed_valid=True,
        )


# ── Test 8: firma negativa con < 2 testigos → is_valid() = False ─────────────

def test_8_refusal_requires_two_witnesses():
    one_witness = ActaSignatures(
        instructor_signed=True,
        worker_signed=False,
        worker_refusal=True,
        witnesses=[Attendee("Testigo 1", "testigo")],
    )
    assert one_witness.is_valid() is False

    two_witnesses = ActaSignatures(
        instructor_signed=True,
        worker_signed=False,
        worker_refusal=True,
        witnesses=[
            Attendee("Testigo 1", "testigo"),
            Attendee("Testigo 2", "testigo"),
        ],
    )
    assert two_witnesses.is_valid() is True


# ── Test 9: recurso resuelto por el mismo abogado → error 422 ────────────────

def test_9_appeal_same_resolver_blocked(svc, ctx):
    proc = svc.create_expediente(
        ctx, worker_name="Sofía Vargas", worker_id="CC 333",
        employer_name="Empresa S.A.", contract_type="indefinido",
    )
    # Simular estado DECISION_EMITIDA directamente
    proc.state = ProcessState.DECISION_EMITIDA
    proc.first_decision_by = "abogado@hg.com"
    svc._put(proc)

    with pytest.raises(PipelineError, match="doble instancia"):
        svc.open_appeal(
            ctx, proc.process_id,
            appealed_by="trabajador@empresa.com",
            resolver_id="abogado@hg.com",  # mismo que emitió la primera decisión
        )


# ── Test 10: sanción con multa → aparece en blocked_options ──────────────────

def test_10_multa_is_blocked():
    rec = recommend("grave", is_reincidence=False)
    blocked_names = [b.split(":")[0] for b in rec.blocked_options]
    assert "multa" in blocked_names
    assert "descuento_salarial" in blocked_names


# ── Test 11: retroceso sin motivo → error ────────────────────────────────────

def test_11_backward_transition_requires_reason():
    with pytest.raises(TransitionError, match="override_reason"):
        validate_transition(
            ProcessState.EN_REVISION,
            ProcessState.EVIDENCIAS_PENDIENTES,
            override_reason=None,
        )


def test_11b_backward_with_reason_generates_audit_entry(svc, ctx):
    proc = svc.create_expediente(
        ctx, worker_name="Diego Herrera", worker_id="CC 444",
        employer_name="Empresa S.A.", contract_type="indefinido",
    )
    proc.state = ProcessState.EN_REVISION
    svc._put(proc)

    proc = svc.transition_back(
        ctx, proc.process_id,
        target_state=ProcessState.DILIGENCIA_REALIZADA,
        reason="Acta incompleta — se retrocede para corregir",
    )
    assert proc.state == ProcessState.DILIGENCIA_REALIZADA
    # El último audit entry debe tener el reason
    last = proc.audit_trail[-1]
    assert last.reason == "Acta incompleta — se retrocede para corregir"
    assert last.from_state is not None


# ── Test 12: determinismo — mismo proceso, mismas entradas, mismo resultado ───

def test_12_determinism_same_inputs_same_state(svc, ctx):
    """Dos procesos con mismos inputs llegan al mismo estado."""
    def _make_and_cite(worker: str) -> str:
        proc = svc.create_expediente(
            ctx, worker_name=worker, worker_id="CC 999",
            employer_name="Empresa S.A.", contract_type="indefinido",
        )
        svc.add_evidence(
            ctx, proc.process_id, filename="ev.pdf", file_type="pdf",
            file_bytes=b"prueba", is_notification_proof=True,
        )
        svc.cite(
            ctx, proc.process_id,
            citation_date=date(2026, 7, 1),
            checklist=_make_full_checklist(),
        )
        return svc.get_process(ctx, proc.process_id).state.value

    state_a = _make_and_cite("Trabajador A")
    state_b = _make_and_cite("Trabajador B")
    assert state_a == state_b == ProcessState.CITADO.value


# ── Test bonus: DisciplinaryConfig rechaza min_notice_days < 5 ───────────────

def test_config_rejects_below_minimum():
    with pytest.raises(ValueError, match="DIAS_HABILES_MINIMOS"):
        DisciplinaryConfig(client_id="x", min_notice_days=3)


def test_config_accepts_exactly_minimum():
    cfg = DisciplinaryConfig(client_id="x", min_notice_days=5)
    assert cfg.min_notice_days == 5
