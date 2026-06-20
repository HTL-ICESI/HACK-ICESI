"""
J1 — Orquestador del proceso disciplinario.

Conecta el expediente con J2 (transcripción), J3 (guardián) y J4 (documentos).
Almacena los procesos en memoria (demo). En producción → BD con tenant_id scope.

Regla no negociable: el sistema recomienda y documenta; el abogado aprueba y firma.
Nunca automatiza sanciones. Los nombres de estado y los bloqueos del API lo reflejan.
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import date, datetime

from app.core.audit import AuditLog
from app.core.errors import DomainError
from app.core.tenancy import TenantContext
from app.domain.disciplinary.attendees import Attendee
from app.domain.disciplinary.config import DisciplinaryConfig
from app.domain.disciplinary.evidence import Evidence
from app.domain.disciplinary.models import (
    AbsenceRecord,
    DisciplinaryProcess,
    DisciplinarySession,
)
from app.domain.disciplinary.pre_citation_checklist import PreCitationChecklist
from app.domain.disciplinary.sanction_engine import FaltaLevel, SanctionType, recommend
from app.domain.disciplinary.signatures import ActaSignatures
from app.domain.disciplinary.state_machine import (
    ProcessState,
    TransitionError,
    validate_transition,
    working_days_between,
)
from app.services.disciplinary_service import DisciplinaryService


class PipelineError(DomainError):
    """Error de negocio en el pipeline J1."""


# MIME por extensión (lo que Twilio anuncia al descargar el adjunto de WhatsApp).
_MIME = {
    "pdf": "application/pdf", "png": "image/png", "jpg": "image/jpeg",
    "jpeg": "image/jpeg", "eml": "message/rfc822",
}


def _content_type(filename: str, file_type: str) -> str:
    ext = (filename.rsplit(".", 1)[-1] or "").lower()
    if ext in _MIME:
        return _MIME[ext]
    return {"pdf": "application/pdf", "image": "image/jpeg",
            "eml": "message/rfc822"}.get(file_type, "application/octet-stream")


def _public_base(backend_host: str) -> str:
    """Normaliza BACKEND_HOST a una base https sin barra final."""
    h = (backend_host or "").strip().rstrip("/")
    if h and not h.startswith(("http://", "https://")):
        h = "https://" + h
    return h


class PipelineService:
    """J1 — Orquestador del expediente disciplinario completo."""

    def __init__(self, disciplinary_svc: DisciplinaryService, audit: AuditLog) -> None:
        self._j2j3j4 = disciplinary_svc
        self._audit = audit
        # En demo: dict["{tenant_id}:{process_id}" -> DisciplinaryProcess]
        self._store: dict[str, DisciplinaryProcess] = {}
        # Bytes de cada evidencia, para servirlos por URL pública (WhatsApp/Twilio).
        # dict["{tenant_id}:{evidence_id}" -> {"bytes","content_type","filename"}]
        self._blobs: dict[str, dict] = {}

    # ── store helpers ─────────────────────────────────────────────────────────

    def _key(self, tenant_id: str, process_id: str) -> str:
        return f"{tenant_id}:{process_id}"

    def _put(self, process: DisciplinaryProcess) -> None:
        self._store[self._key(process.tenant_id, process.process_id)] = process

    def _get(self, ctx: TenantContext, process_id: str) -> DisciplinaryProcess:
        proc = self._store.get(self._key(ctx.tenant_id, process_id))
        if proc is None:
            raise PipelineError(f"Expediente {process_id!r} no encontrado.")
        return proc

    def list_processes(self, ctx: TenantContext) -> list[DisciplinaryProcess]:
        prefix = f"{ctx.tenant_id}:"
        return [p for k, p in self._store.items() if k.startswith(prefix)]

    # ── J1 endpoints ──────────────────────────────────────────────────────────

    def create_expediente(
        self,
        ctx: TenantContext,
        worker_name: str,
        worker_id: str,
        employer_name: str,
        contract_type: str,
        doc_id: str | None = None,
        config: DisciplinaryConfig | None = None,
    ) -> DisciplinaryProcess:
        process_id = str(uuid.uuid4())
        cfg = config or DisciplinaryConfig(client_id=ctx.tenant_id)
        proc = DisciplinaryProcess(
            process_id=process_id,
            tenant_id=ctx.tenant_id,
            worker_name=worker_name,
            worker_id=worker_id,
            employer_name=employer_name,
            contract_type=contract_type,
            doc_id=doc_id,
            config=cfg,
        )
        proc.add_audit_entry(
            actor=ctx.actor,
            from_state=None,
            to_state=ProcessState.EVIDENCIAS_PENDIENTES,
            payload=f"Expediente creado: {worker_name} / {employer_name}",
        )
        self._put(proc)
        self._audit.record(ctx, "j1.create_expediente", process_id)
        return proc

    def get_process(self, ctx: TenantContext, process_id: str) -> DisciplinaryProcess:
        return self._get(ctx, process_id)

    def add_evidence(
        self,
        ctx: TenantContext,
        process_id: str,
        filename: str,
        file_type: str,
        file_bytes: bytes,
        is_notification_proof: bool = False,
    ) -> DisciplinaryProcess:
        proc = self._get(ctx, process_id)
        sha = hashlib.sha256(file_bytes).hexdigest()
        evidence_id = str(uuid.uuid4())
        content_type = _content_type(filename, file_type)
        ev = Evidence(
            evidence_id=evidence_id,
            filename=filename,
            file_type=file_type,  # type: ignore[arg-type]
            sha256=sha,
            uploaded_at=datetime.utcnow(),
            uploaded_by=ctx.actor,
            metadata={"size_bytes": len(file_bytes), "content_type": content_type},
        )
        proc.evidences.append(ev)
        # Guardar los bytes para poder servirlos por URL pública (Twilio los descarga).
        self._blobs[f"{ctx.require()}:{evidence_id}"] = {
            "bytes": file_bytes, "content_type": content_type, "filename": filename,
        }
        # Auto-marcar prueba en checklist
        proc.checklist.at_least_one_proof = True
        if is_notification_proof:
            proc.notification_proof_id = ev.evidence_id
        proc.add_audit_entry(
            actor=ctx.actor,
            from_state=proc.state,
            to_state=proc.state,
            payload=f"Evidencia cargada: {filename} (sha256={sha[:12]}...)",
        )
        self._put(proc)
        self._audit.record(ctx, "j1.add_evidence", process_id,
                           grounding=[f"sha256={sha[:12]}"])
        return proc

    # ── media de evidencia (URLs públicas firmadas para Twilio) ───────────────

    def get_evidence_blob(self, ctx: TenantContext, evidence_id: str) -> dict | None:
        """Bytes + content_type de una evidencia, tenant-scoped. None si no existe."""
        return self._blobs.get(f"{ctx.require()}:{evidence_id}")

    def stash_blob(self, ctx: TenantContext, filename: str, file_bytes: bytes,
                   content_type: str) -> str:
        """Guarda un blob suelto (p.ej. un documento generado en PDF) y devuelve su
        id, servible por el mismo endpoint /media/evidence con URL firmada."""
        import uuid as _uuid
        blob_id = str(_uuid.uuid4())
        self._blobs[f"{ctx.require()}:{blob_id}"] = {
            "bytes": file_bytes, "content_type": content_type, "filename": filename,
        }
        return blob_id

    def build_evidence_media(
        self, ctx: TenantContext, process_id: str, backend_host: str,
    ) -> tuple[list[str], list[str]]:
        """(nombres, urls públicas firmadas) de las evidencias del proceso.

        Las URLs solo se construyen si hay BACKEND_HOST (host público que Twilio
        pueda alcanzar) Y bytes guardados. Si falta el host, devuelve urls=[] y el
        WhatsApp sale sin adjuntos (degradación honesta, no un error silencioso)."""
        from app.core.media_token import sign  # import local: evita ciclo en import

        proc = self._get(ctx, process_id)
        base = _public_base(backend_host)
        names: list[str] = []
        urls: list[str] = []
        for ev in proc.evidences:
            names.append(ev.filename)
            if base and f"{ctx.require()}:{ev.evidence_id}" in self._blobs:
                token = sign(ctx.require(), ev.evidence_id)
                urls.append(f"{base}/media/evidence/{ev.evidence_id}?t={token}")
        return names, urls

    def update_checklist(
        self,
        ctx: TenantContext,
        process_id: str,
        checklist: PreCitationChecklist,
    ) -> DisciplinaryProcess:
        proc = self._get(ctx, process_id)
        # at_least_one_proof solo se puede marcar True si hay evidencias reales
        if checklist.at_least_one_proof and not proc.evidences:
            raise PipelineError(
                "No se puede marcar 'at_least_one_proof' sin evidencias cargadas."
            )
        proc.checklist = checklist
        proc.add_audit_entry(
            actor=ctx.actor,
            from_state=proc.state,
            to_state=proc.state,
            payload=f"Checklist actualizado: can_cite={checklist.can_cite}",
        )
        self._put(proc)
        return proc

    def cite(
        self,
        ctx: TenantContext,
        process_id: str,
        citation_date: date,
        checklist: PreCitationChecklist | None = None,
        notification_proof_id: str | None = None,
        override_reason: str | None = None,
    ) -> DisciplinaryProcess:
        proc = self._get(ctx, process_id)

        # Actualizar checklist si se provee
        if checklist:
            if checklist.at_least_one_proof and not proc.evidences:
                raise PipelineError(
                    "No se puede marcar 'at_least_one_proof' sin evidencias cargadas."
                )
            proc.checklist = checklist

        # Registrar comprobante de notificación
        if notification_proof_id:
            proc.notification_proof_id = notification_proof_id

        has_proof = bool(proc.notification_proof_id)

        # Si está en EVIDENCIAS_PENDIENTES → primero transitar a LISTO_PARA_CITAR
        if proc.state == ProcessState.EVIDENCIAS_PENDIENTES:
            try:
                validate_transition(
                    proc.state, ProcessState.LISTO_PARA_CITAR,
                    checklist_complete=proc.checklist.can_cite,
                )
            except TransitionError as exc:
                missing = proc.checklist.missing_items()
                raise PipelineError(
                    f"Checklist incompleto: {exc}. "
                    f"Ítems faltantes: {missing}"
                ) from exc
            old_state = proc.state
            proc.state = ProcessState.LISTO_PARA_CITAR
            proc.add_audit_entry(
                actor=ctx.actor,
                from_state=old_state,
                to_state=proc.state,
                payload="Checklist completo — listo para citar",
            )

        # Transitar a CITADO
        try:
            validate_transition(
                proc.state, ProcessState.CITADO,
                has_notification_proof=has_proof,
                override_reason=override_reason,
            )
        except TransitionError as exc:
            raise PipelineError(str(exc)) from exc

        old_state = proc.state
        proc.state = ProcessState.CITADO
        proc.citation_date = citation_date
        proc.add_audit_entry(
            actor=ctx.actor,
            from_state=old_state,
            to_state=proc.state,
            reason=override_reason,
            payload=f"Citación emitida para {citation_date.isoformat()}",
        )
        self._put(proc)
        self._audit.record(ctx, "j1.cite", process_id)
        return proc

    def record_session(
        self,
        ctx: TenantContext,
        process_id: str,
        session_date: date,
        attendees: list[Attendee],
        transcript: str = "",
        signatures: ActaSignatures | None = None,
        override_reason: str | None = None,
    ) -> DisciplinaryProcess:
        proc = self._get(ctx, process_id)

        # Validar límite de rondas (configurable, con override del abogado)
        rounds_done = len(proc.sessions)
        if rounds_done >= proc.config.max_rounds and not override_reason:
            raise PipelineError(
                f"Se alcanzó el límite de {proc.config.max_rounds} rondas. "
                f"Para autorizar una ronda adicional provea override_reason."
            )

        acta_valid = signatures.is_valid() if signatures else False
        has_attendees = len(attendees) > 0

        try:
            validate_transition(
                proc.state, ProcessState.DILIGENCIA_REALIZADA,
                citation_date=proc.citation_date,
                session_date=session_date,
                min_notice_days=proc.config.min_notice_days,
                acta_attendees_registered=has_attendees,
                acta_signed_valid=acta_valid,
                override_reason=override_reason,
            )
        except TransitionError as exc:
            raise PipelineError(str(exc)) from exc

        session = DisciplinarySession(
            session_id=str(uuid.uuid4()),
            round_number=rounds_done + 1,
            session_date=session_date,
            attendees=[a.to_dict() for a in attendees],
            transcript=transcript,
            signatures=signatures,
        )
        proc.sessions.append(session)
        old_state = proc.state
        proc.state = ProcessState.DILIGENCIA_REALIZADA
        proc.add_audit_entry(
            actor=ctx.actor,
            from_state=old_state,
            to_state=proc.state,
            reason=override_reason,
            payload=f"Diligencia ronda {session.round_number} — {len(attendees)} asistentes",
        )
        self._put(proc)
        self._audit.record(ctx, "j1.record_session", process_id)
        return proc

    def record_absence(
        self,
        ctx: TenantContext,
        process_id: str,
        session_date: date,
        action: str,
        reason: str,
    ) -> DisciplinaryProcess:
        proc = self._get(ctx, process_id)

        # proceed_in_absence solo permitido si ya hubo al menos una reprogramación documentada
        if action == "proceed_in_absence":
            if not proc.absences_with_reschedule():
                raise PipelineError(
                    "No se puede continuar en ausencia en la primera inasistencia. "
                    "Primero reprograme con constancia (action='reschedule')."
                )

        absence = AbsenceRecord(
            absence_id=str(uuid.uuid4()),
            session_date=session_date,
            action=action,
            reason=reason,
            recorded_at=datetime.utcnow(),
        )
        proc.absences.append(absence)
        proc.add_audit_entry(
            actor=ctx.actor,
            from_state=proc.state,
            to_state=proc.state,
            reason=reason,
            payload=f"Inasistencia registrada: action={action}",
        )
        self._put(proc)
        self._audit.record(ctx, "j1.record_absence", process_id)
        return proc

    def contrast(
        self,
        ctx: TenantContext,
        process_id: str,
        diligence_state_in: dict,
    ) -> DisciplinaryProcess:
        """Corre J3 guardián y almacena el resultado. Transita a EN_REVISION."""
        proc = self._get(ctx, process_id)

        from app.domain.disciplinary.guardian import DiligenceState, evaluate
        state = DiligenceState(
            falta_tipificada=diligence_state_in.get("falta_tipificada", True),
            comunicacion_apertura_formal=diligence_state_in.get("comunicacion_apertura_formal", False),
            formulacion_cargos_concretos=diligence_state_in.get("formulacion_cargos_concretos", False),
            traslado_pruebas=diligence_state_in.get("traslado_pruebas", False),
            termino_defensa_minimo=diligence_state_in.get("termino_defensa_minimo", False),
            oportunidad_descargos=diligence_state_in.get("oportunidad_descargos", False),
            decision_motivada=diligence_state_in.get("decision_motivada", True),
            derecho_impugnacion=diligence_state_in.get("derecho_impugnacion", True),
            derecho_acompanamiento_informado=diligence_state_in.get(
                "derecho_acompanamiento_informado", True
            ),
        )
        verdict = evaluate(state)
        proc.guardian_result = verdict.to_dict()

        # Leer estado del acta de la última sesión para validar la transición
        last = proc.last_session()
        acta_has_attendees = bool(last and last.attendees)
        acta_signed_valid = (last.signatures.is_valid() if (last and last.signatures) else False)

        try:
            validate_transition(
                proc.state, ProcessState.EN_REVISION,
                acta_attendees_registered=acta_has_attendees,
                acta_signed_valid=acta_signed_valid,
            )
        except TransitionError as exc:
            raise PipelineError(str(exc)) from exc

        old_state = proc.state
        proc.state = ProcessState.EN_REVISION
        proc.add_audit_entry(
            actor=ctx.actor,
            from_state=old_state,
            to_state=proc.state,
            payload=f"Guardián J3: {verdict.clasificacion} ({verdict.garantias_ok}/{verdict.garantias_total})",
        )
        self._put(proc)
        self._audit.record(ctx, "j1.contrast", process_id,
                           grounding=[verdict.clasificacion])
        return proc

    def decide(
        self,
        ctx: TenantContext,
        process_id: str,
        falta_level: FaltaLevel,
        is_reincidence: bool,
        chosen_sanction: SanctionType,
        decision_text: str,
        lawyer_id: str,
    ) -> DisciplinaryProcess:
        """Abogado aprueba la decisión. J3 debe haber clasificado CONFORME."""
        proc = self._get(ctx, process_id)

        guardian_can = False
        if proc.guardian_result:
            guardian_can = proc.guardian_result.get("can_proceed", False)

        try:
            validate_transition(
                proc.state, ProcessState.DECISION_EMITIDA,
                guardian_can_proceed=guardian_can,
                lawyer_decision_registered=True,
            )
        except TransitionError as exc:
            raise PipelineError(str(exc)) from exc

        rec = recommend(falta_level, is_reincidence, chosen_sanction)
        proc.sanction_recommendation = rec
        proc.lawyer_decision = {
            "falta_level": falta_level,
            "is_reincidence": is_reincidence,
            "chosen_sanction": chosen_sanction,
            "decision_text": decision_text,
            "lawyer_id": lawyer_id,
            "decided_at": datetime.utcnow().isoformat(),
        }
        proc.first_decision_by = lawyer_id

        old_state = proc.state
        proc.state = ProcessState.DECISION_EMITIDA
        proc.add_audit_entry(
            actor=ctx.actor,
            from_state=old_state,
            to_state=proc.state,
            payload=f"Decisión: {chosen_sanction} / falta {falta_level} / firmado por {lawyer_id}",
        )
        self._put(proc)
        self._audit.record(ctx, "j1.decide", process_id,
                           grounding=[chosen_sanction, falta_level])
        return proc

    def open_appeal(
        self,
        ctx: TenantContext,
        process_id: str,
        appealed_by: str,
        resolver_id: str,
    ) -> DisciplinaryProcess:
        """Trabajador impugna — validar que el resolver sea distinto al decisor original."""
        proc = self._get(ctx, process_id)

        if proc.first_decision_by and resolver_id == proc.first_decision_by:
            raise PipelineError(
                f"El perfil que resuelve el recurso ({resolver_id!r}) no puede ser el mismo "
                f"que emitió la primera decisión ({proc.first_decision_by!r}). "
                f"Ley 2466/2025 — doble instancia."
            )

        try:
            validate_transition(proc.state, ProcessState.RECURSO)
        except TransitionError as exc:
            raise PipelineError(str(exc)) from exc

        proc.appeal_opened_by = appealed_by
        proc.appeal_resolver_id = resolver_id
        old_state = proc.state
        proc.state = ProcessState.RECURSO
        proc.add_audit_entry(
            actor=ctx.actor,
            from_state=old_state,
            to_state=proc.state,
            payload=f"Recurso abierto por {appealed_by!r} — resolver: {resolver_id!r}",
        )
        self._put(proc)
        self._audit.record(ctx, "j1.open_appeal", process_id)
        return proc

    def close_process(
        self,
        ctx: TenantContext,
        process_id: str,
        reason: str | None = None,
    ) -> DisciplinaryProcess:
        proc = self._get(ctx, process_id)

        try:
            validate_transition(proc.state, ProcessState.CERRADO)
        except TransitionError as exc:
            raise PipelineError(str(exc)) from exc

        proc.state = ProcessState.CERRADO
        proc.closed_at = datetime.utcnow()
        proc.add_audit_entry(
            actor=ctx.actor,
            from_state=ProcessState(proc.audit_trail[-1].from_state) if proc.audit_trail else None,
            to_state=ProcessState.CERRADO,
            reason=reason,
            payload="Proceso cerrado por el abogado",
        )
        self._put(proc)
        self._audit.record(ctx, "j1.close_process", process_id)
        return proc

    def transition_back(
        self,
        ctx: TenantContext,
        process_id: str,
        target_state: ProcessState,
        reason: str,
    ) -> DisciplinaryProcess:
        """Retrocede el proceso a un estado anterior. Siempre requiere motivo."""
        proc = self._get(ctx, process_id)
        try:
            validate_transition(
                proc.state, target_state, override_reason=reason
            )
        except TransitionError as exc:
            raise PipelineError(str(exc)) from exc

        old_state = proc.state
        proc.state = target_state
        proc.add_audit_entry(
            actor=ctx.actor,
            from_state=old_state,
            to_state=proc.state,
            reason=reason,
            payload=f"Retroceso autorizado: {old_state.value} → {target_state.value}",
        )
        self._put(proc)
        self._audit.record(ctx, "j1.transition_back", process_id, grounding=[reason])
        return proc
