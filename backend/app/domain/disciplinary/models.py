"""Agregado DisciplinaryProcess — expediente disciplinario completo.

Es el modelo de dominio central de J1. Contiene el estado del proceso,
evidencias, sesiones, firmas y el audit trail inmutable.
No hace I/O: el servicio (PipelineService) lo persiste en memoria.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime

from app.domain.disciplinary.audit_trail import PipelineAuditEntry
from app.domain.disciplinary.config import DisciplinaryConfig
from app.domain.disciplinary.evidence import Evidence
from app.domain.disciplinary.pre_citation_checklist import PreCitationChecklist
from app.domain.disciplinary.sanction_engine import SanctionRecommendation
from app.domain.disciplinary.signatures import ActaSignatures
from app.domain.disciplinary.state_machine import ProcessState


@dataclass
class DisciplinarySession:
    session_id: str
    round_number: int
    session_date: date
    attendees: list[dict]
    transcript: str = ""
    signatures: ActaSignatures | None = None

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "round_number": self.round_number,
            "session_date": self.session_date.isoformat(),
            "attendees": self.attendees,
            "transcript": self.transcript,
            "signatures": self.signatures.to_dict() if self.signatures else None,
        }


@dataclass
class AbsenceRecord:
    absence_id: str
    session_date: date
    action: str
    reason: str
    recorded_at: datetime

    def to_dict(self) -> dict:
        return {
            "absence_id": self.absence_id,
            "session_date": self.session_date.isoformat(),
            "action": self.action,
            "reason": self.reason,
            "recorded_at": self.recorded_at.isoformat(),
        }


@dataclass
class DisciplinaryProcess:
    process_id: str
    tenant_id: str
    worker_name: str
    worker_id: str
    employer_name: str
    contract_type: str
    doc_id: str | None = None
    state: ProcessState = ProcessState.EVIDENCIAS_PENDIENTES
    created_at: datetime = field(default_factory=datetime.utcnow)
    config: DisciplinaryConfig = field(default_factory=lambda: DisciplinaryConfig(client_id="default"))
    checklist: PreCitationChecklist = field(default_factory=PreCitationChecklist)
    evidences: list[Evidence] = field(default_factory=list)
    notification_proof_id: str | None = None   # evidence_id del comprobante de citación
    citation_date: date | None = None
    sessions: list[DisciplinarySession] = field(default_factory=list)
    absences: list[AbsenceRecord] = field(default_factory=list)
    guardian_result: dict | None = None
    sanction_recommendation: SanctionRecommendation | None = None
    lawyer_decision: dict | None = None
    first_decision_by: str | None = None
    appeal_opened_by: str | None = None
    appeal_resolver_id: str | None = None
    closed_at: datetime | None = None
    audit_trail: list[PipelineAuditEntry] = field(default_factory=list)

    # ── helpers ──────────────────────────────────────────────────────────────

    def last_session(self) -> DisciplinarySession | None:
        return self.sessions[-1] if self.sessions else None

    def absences_with_reschedule(self) -> list[AbsenceRecord]:
        return [a for a in self.absences if a.action == "reschedule"]

    def add_audit_entry(
        self,
        actor: str,
        from_state: ProcessState | None,
        to_state: ProcessState,
        reason: str | None = None,
        payload: str = "",
    ) -> None:
        entry = PipelineAuditEntry(
            entry_id=str(uuid.uuid4()),
            process_id=self.process_id,
            timestamp=datetime.utcnow(),
            actor=actor,
            from_state=from_state.value if from_state else None,
            to_state=to_state.value,
            reason=reason,
            payload_summary=payload,
        )
        self.audit_trail.append(entry)

    def to_dict(self) -> dict:
        last = self.last_session()
        return {
            "process_id": self.process_id,
            "tenant_id": self.tenant_id,
            "doc_id": self.doc_id,
            "worker_name": self.worker_name,
            "worker_id": self.worker_id,
            "employer_name": self.employer_name,
            "contract_type": self.contract_type,
            "state": self.state.value,
            "created_at": self.created_at.isoformat(),
            "config": self.config.to_dict(),
            "checklist": self.checklist.to_dict(),
            "evidences": [e.to_dict() for e in self.evidences],
            "notification_proof_id": self.notification_proof_id,
            "citation_date": self.citation_date.isoformat() if self.citation_date else None,
            "sessions": [s.to_dict() for s in self.sessions],
            "absences": [a.to_dict() for a in self.absences],
            "guardian_result": self.guardian_result,
            "sanction_recommendation": (
                self.sanction_recommendation.to_dict() if self.sanction_recommendation else None
            ),
            "lawyer_decision": self.lawyer_decision,
            "first_decision_by": self.first_decision_by,
            "appeal_opened_by": self.appeal_opened_by,
            "appeal_resolver_id": self.appeal_resolver_id,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "audit_trail": [e.to_dict() for e in self.audit_trail],
            "rounds_completed": len(self.sessions),
            "last_session_date": last.session_date.isoformat() if last else None,
        }
