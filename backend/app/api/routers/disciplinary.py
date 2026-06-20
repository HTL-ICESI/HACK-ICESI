"""
Router del proceso disciplinario.

J2 (transcripción) · J3 (guardián) · J4 (documentos) — motor standalone.
J1 (orquestador) — pipeline completo expediente → citación → diligencia → decisión.

El sistema recomienda y documenta; el abogado aprueba y firma. Nunca automatiza sanciones.
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, File, Form, Header, UploadFile
from pydantic import BaseModel, Field

from app.core.security import get_tenant
from app.core.tenancy import TenantContext
from app.config import get_settings
from app.api.deps import get_disciplinary_service, get_pipeline_service
from app.adapters.telephony import descargos_agent as agent
from app.domain.disciplinary.attendees import Attendee
from app.domain.disciplinary.config import DisciplinaryConfig
from app.domain.disciplinary.guardian import DiligenceState, MissingStep
from app.domain.disciplinary.pre_citation_checklist import PreCitationChecklist
from app.domain.disciplinary.signatures import ActaSignatures
from app.domain.disciplinary.state_machine import ProcessState
from app.services.disciplinary_service import DisciplinaryService
from app.services.pipeline_service import PipelineError, PipelineService

router = APIRouter(prefix="/api/disciplinary", tags=["disciplinary"])


# ── Shared helpers (J2/J3/J4) ────────────────────────────────────────────────

class DiligenceStateIn(BaseModel):
    worker_notified_right_to_companion: bool
    charges_read: bool
    evidence_presented: bool
    worker_allowed_to_respond: bool
    term_respected: bool


def _to_domain(s: DiligenceStateIn) -> DiligenceState:
    return DiligenceState(
        falta_tipificada=True,
        comunicacion_apertura_formal=s.charges_read,
        formulacion_cargos_concretos=s.charges_read,
        traslado_pruebas=s.evidence_presented,
        termino_defensa_minimo=s.term_respected,
        oportunidad_descargos=s.worker_allowed_to_respond,
        decision_motivada=True,
        derecho_impugnacion=True,
        derecho_acompanamiento_informado=s.worker_notified_right_to_companion,
    )


_NORM_CITATIONS: dict[str, dict] = {
    "CN art. 29": {
        "norm_id": "CN", "article": "art. 29", "title": "Debido proceso",
        "url": "https://www.secretariasenado.gov.co/constitucion-politica/articulo-29",
        "verified": True,
    },
    "CST art. 115": {
        "norm_id": "CST", "article": "art. 115", "title": "Procedimiento disciplinario",
        "url": "https://www.secretariasenado.gov.co/cst-articulo-115", "verified": True,
    },
    "CST art. 114": {
        "norm_id": "CST", "article": "art. 114", "title": "Tipicidad de la falta",
        "url": "https://www.secretariasenado.gov.co/cst-articulo-114", "verified": True,
    },
    "CN art. 29 · CST art. 115": {
        "norm_id": "CST", "article": "art. 115", "title": "Procedimiento disciplinario",
        "url": "https://www.secretariasenado.gov.co/cst-articulo-115", "verified": True,
    },
    "CST art. 115 num. 5": {
        "norm_id": "CST", "article": "art. 115 num. 5", "title": "Decisión motivada",
        "url": "https://www.secretariasenado.gov.co/cst-articulo-115", "verified": True,
    },
}


def _serialize_step(step: MissingStep) -> dict:
    citation = _NORM_CITATIONS.get(step.norm)
    if citation is None:
        for norma, cita in _NORM_CITATIONS.items():
            if step.norm.startswith(norma):
                citation = cita
                break
    if citation is None:
        citation = {"norm_id": step.norm, "article": "", "title": step.norm,
                    "url": "", "verified": False}
    return {"step": step.step, "citation": citation, "consequence": step.consequence}


def _pipeline_error(exc: PipelineError):
    from fastapi import HTTPException
    raise HTTPException(status_code=422, detail=str(exc))


# ── J2 — POST /api/disciplinary/transcribe ───────────────────────────────────

@router.post("/transcribe")
async def transcribe_session(
    session_id: str = Form(...),
    audio: UploadFile | None = File(default=None),
    file: UploadFile | None = File(default=None),
    ctx: TenantContext = Depends(get_tenant),
    svc: DisciplinaryService = Depends(get_disciplinary_service),
):
    upload = audio or file
    audio_bytes = await upload.read() if upload else b""
    result = svc.transcribe_session(ctx, audio_bytes)
    return {"session_id": session_id, **result}


# ── J3 — POST /api/disciplinary/guardian ────────────────────────────────────

class GuardianRequest(BaseModel):
    session_id: str
    diligence_state: DiligenceStateIn


@router.post("/guardian")
def guardian(
    req: GuardianRequest,
    ctx: TenantContext = Depends(get_tenant),
    svc: DisciplinaryService = Depends(get_disciplinary_service),
):
    state = _to_domain(req.diligence_state)
    verdict = svc.run_guardian(ctx, state)
    return {
        "session_id": req.session_id,
        "nullity_alert": verdict["nullity_alert"],
        "can_proceed": verdict["can_proceed"],
        "clasificacion": verdict["clasificacion"],
        "missing_steps": [_serialize_step(s) for s in verdict["missing_steps"]],
    }


# ── J4 — POST /api/disciplinary/documents ───────────────────────────────────

class DocumentsRequest(BaseModel):
    session_id: str
    diligence_state: DiligenceStateIn
    transcript: str = ""
    lawyer_name: str = ""   # abogado que firma el acta


@router.post("/documents")
async def generate_documents(
    req: DocumentsRequest,
    ctx: TenantContext = Depends(get_tenant),
    svc: DisciplinaryService = Depends(get_disciplinary_service),
):
    state = _to_domain(req.diligence_state)
    result = await svc.generate_documents(ctx, state, req.transcript, lawyer_name=req.lawyer_name)
    return {"session_id": req.session_id, **result}


# ─────────────────────────────────────────────────────────────────────────────
# J1 — Llamada de descargos (ElevenLabs Agents + Twilio, patrón AFFIRMA)
#   La llamada CONDUCE y CAPTURA; el guardián (código puro) DECIDE.
# ─────────────────────────────────────────────────────────────────────────────


class StartCallRequest(BaseModel):
    session_id: str
    to_number: str                     # E.164, el celular del trabajador
    company_name: str
    worker_name: str
    charges_summary: str
    evidence_summary: str
    # Término de defensa que YA transcurrió antes de la diligencia (art. 115 reformado)
    citation_date: str
    diligence_date: str
    defense_term_elapsed: str
    response_deadline: str = "cinco (5) días hábiles"
    process_type: str = "sancion_disciplinaria"   # | "garantia_defensa_predespido"
    worker_is_unionized: bool = False
    instructor_name: str = "Justo"


@router.post("/call")
def start_call(
    req: StartCallRequest,
    ctx: TenantContext = Depends(get_tenant),
    svc: DisciplinaryService = Depends(get_disciplinary_service),
):
    case = agent.DescargosCase(
        session_id=req.session_id, company_name=req.company_name,
        worker_name=req.worker_name, charges_summary=req.charges_summary,
        evidence_summary=req.evidence_summary, response_deadline=req.response_deadline,
        citation_date=req.citation_date, diligence_date=req.diligence_date,
        defense_term_elapsed=req.defense_term_elapsed, process_type=req.process_type,
        worker_is_unionized=req.worker_is_unionized, instructor_name=req.instructor_name,
    )
    try:
        return svc.start_descargos_call(ctx, case, req.to_number)
    except Exception as exc:  # noqa: BLE001 — degradación honesta: sin credenciales, error claro
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=f"Telefonía no disponible: {exc}")


@router.get("/call/result/{conversation_id}")
def get_call_result(
    conversation_id: str,
    ctx: TenantContext = Depends(get_tenant),
    svc: DisciplinaryService = Depends(get_disciplinary_service),
):
    """Trae la transcripción REAL de la llamada de ElevenLabs (transcript + descargo
    + veredicto del guardián). El front la consulta por polling tras lanzar la llamada."""
    try:
        return svc.fetch_call_result(ctx, conversation_id)
    except Exception as exc:  # noqa: BLE001 — sin credenciales / aún sin terminar
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=f"Resultado no disponible: {exc}")


class CallWebhookRequest(BaseModel):
    conversation_id: str | None = None
    session_id: str
    process_type: str = "sancion_disciplinaria"
    worker_full_name: str | None = None
    worker_id_number: str | None = None
    # Paso 1: acompañamiento + renuncia expresa
    right_to_companion_notified: bool = False
    union_representation_notified: bool = False
    worker_waived_companion: bool = False
    # Paso 2: término de defensa previo (-> term_respected del guardián)
    prior_defense_term_respected: bool = True
    # Pasos 3-4
    charges_read: bool = False
    evidence_presented: bool = False
    # Paso 5: descargos + silencio + solicitud de pruebas
    worker_allowed_to_respond: bool = False
    worker_chose_silence: bool = False
    worker_response_summary: str | None = None
    evidence_requested_by_worker: str | None = None
    # Pasos 6-7
    motivated_decision_announced: bool = False
    right_to_appeal_notified: bool = False
    outcome: str | None = None
    # Override determinista opcional (cómputo de fechas en el backend).
    term_respected: bool | None = None


@router.post("/call/webhook")
def call_webhook(
    req: CallWebhookRequest,
    ctx: TenantContext = Depends(get_tenant),
    svc: DisciplinaryService = Depends(get_disciplinary_service),
    x_hg_secret: str | None = Header(default=None),
):
    # El secreto compartido protege el webhook (lo envía el tool del agente).
    expected = (get_settings().hg_backend_token or "").strip()
    if expected and x_hg_secret != expected:
        return {"detail": "secreto inválido", "accepted": False}
    payload = req.model_dump()
    result = svc.ingest_call_result(ctx, payload=payload, term_respected=req.term_respected)
    return {"session_id": req.session_id, "conversation_id": req.conversation_id,
            "outcome": req.outcome, "process_type": req.process_type, **result}


# --- J1: WhatsApp de evidencia (Twilio Messaging) ------------------------------

class EvidenceWhatsAppRequest(BaseModel):
    to_number: str                     # celular del trabajador
    worker_name: str
    company_name: str
    charges_summary: str
    # Si se manda process_id, los adjuntos se arman SOLOS desde la evidencia del
    # expediente (URLs públicas firmadas). evidence_names/urls quedan como override manual.
    process_id: str | None = None
    evidence_names: list[str] = Field(default_factory=list)
    evidence_urls: list[str] = Field(default_factory=list)   # URLs públicas (opcional)
    call_date: str | None = None
    call_time: str = "10:00 a.m."
    response_deadline: str = "cinco (5) días hábiles"
    lawyer_name: str = ""              # abogado que lleva el proceso


@router.post("/evidence/whatsapp")
def evidence_whatsapp(
    req: EvidenceWhatsAppRequest,
    ctx: TenantContext = Depends(get_tenant),
    svc: DisciplinaryService = Depends(get_disciplinary_service),
    pipeline: PipelineService = Depends(get_pipeline_service),
):
    names = list(req.evidence_names)
    urls = list(req.evidence_urls)
    # Auto-armar adjuntos desde el expediente si se indicó el proceso.
    if req.process_id:
        try:
            auto_names, auto_urls = pipeline.build_evidence_media(
                ctx, req.process_id, get_settings().backend_host,
            )
        except PipelineError as exc:
            _pipeline_error(exc)
        names = names or auto_names          # los explícitos mandan; si no, los del expediente
        urls = urls or auto_urls
    return svc.send_evidence_whatsapp(
        ctx, to_number=req.to_number, worker_name=req.worker_name,
        company_name=req.company_name, charges_summary=req.charges_summary,
        evidence_names=names, evidence_urls=urls,
        call_date=req.call_date, call_time=req.call_time,
        response_deadline=req.response_deadline, lawyer_name=req.lawyer_name,
    )


# --- J1: contraste descargo ↔ cargos (asesor, no decide) -----------------------

class ContrastDescargoRequest(BaseModel):
    charges_summary: str
    evidence_summary: str = ""
    descargo_text: str


@router.post("/descargo/contrast")
async def descargo_contrast(
    req: ContrastDescargoRequest,
    ctx: TenantContext = Depends(get_tenant),
    svc: DisciplinaryService = Depends(get_disciplinary_service),
):
    return await svc.contrast_descargo(
        ctx, charges_summary=req.charges_summary,
        evidence_summary=req.evidence_summary, descargo_text=req.descargo_text,
    )


# ─────────────────────────────────────────────────────────────────────────────
# J1 — Pipeline completo
# ─────────────────────────────────────────────────────────────────────────────


# ── POST /api/disciplinary/expediente ────────────────────────────────────────

class ConfigIn(BaseModel):
    min_notice_days: int = 5
    max_rounds: int = 2
    days_between_rounds: int = 5
    decision_deadline_days: int = 15
    internal_regulation_ref: str = "RIT"


class CreateExpedienteRequest(BaseModel):
    worker_name: str
    worker_id: str
    employer_name: str
    contract_type: str
    doc_id: str | None = None
    config: ConfigIn | None = None


@router.post("/expediente")
def create_expediente(
    req: CreateExpedienteRequest,
    ctx: TenantContext = Depends(get_tenant),
    svc: PipelineService = Depends(get_pipeline_service),
):
    config = None
    if req.config:
        try:
            config = DisciplinaryConfig(
                client_id=ctx.tenant_id,
                min_notice_days=req.config.min_notice_days,
                max_rounds=req.config.max_rounds,
                days_between_rounds=req.config.days_between_rounds,
                decision_deadline_days=req.config.decision_deadline_days,
                internal_regulation_ref=req.config.internal_regulation_ref,
            )
        except ValueError as exc:
            from fastapi import HTTPException
            raise HTTPException(status_code=422, detail=str(exc))
    try:
        proc = svc.create_expediente(
            ctx,
            worker_name=req.worker_name,
            worker_id=req.worker_id,
            employer_name=req.employer_name,
            contract_type=req.contract_type,
            doc_id=req.doc_id,
            config=config,
        )
    except PipelineError as exc:
        _pipeline_error(exc)
    return proc.to_dict()


# ── GET /api/disciplinary/{process_id} ───────────────────────────────────────

@router.get("/{process_id}")
def get_process(
    process_id: str,
    ctx: TenantContext = Depends(get_tenant),
    svc: PipelineService = Depends(get_pipeline_service),
):
    try:
        proc = svc.get_process(ctx, process_id)
    except PipelineError as exc:
        _pipeline_error(exc)
    return proc.to_dict()


# ── GET /api/disciplinary (listado) ──────────────────────────────────────────

@router.get("")
def list_processes(
    ctx: TenantContext = Depends(get_tenant),
    svc: PipelineService = Depends(get_pipeline_service),
):
    processes = svc.list_processes(ctx)
    return {"processes": [p.to_dict() for p in processes], "total": len(processes)}


# ── POST /api/disciplinary/{process_id}/evidence ─────────────────────────────

@router.post("/{process_id}/evidence")
async def add_evidence(
    process_id: str,
    file: UploadFile = File(...),
    uploaded_by: str = Form(...),
    is_notification_proof: bool = Form(default=False),
    ctx: TenantContext = Depends(get_tenant),
    svc: PipelineService = Depends(get_pipeline_service),
):
    file_bytes = await file.read()
    filename = file.filename or "evidencia.pdf"
    # Inferir tipo
    ext = filename.rsplit(".", 1)[-1].lower()
    file_type = "eml" if ext == "eml" else "image" if ext in {"jpg", "jpeg", "png"} else "pdf"
    try:
        proc = svc.add_evidence(
            ctx, process_id,
            filename=filename,
            file_type=file_type,
            file_bytes=file_bytes,
            is_notification_proof=is_notification_proof,
        )
    except PipelineError as exc:
        _pipeline_error(exc)
    return proc.to_dict()


# ── POST /api/disciplinary/{process_id}/cite ─────────────────────────────────

class ChecklistIn(BaseModel):
    worker_id_and_contract: bool = False
    facts_and_date: bool = False
    at_least_one_proof: bool = False
    infringed_norm: bool = False


class CiteRequest(BaseModel):
    citation_date: date
    checklist: ChecklistIn | None = None
    notification_proof_id: str | None = None
    override_reason: str | None = None


@router.post("/{process_id}/cite")
def cite(
    process_id: str,
    req: CiteRequest,
    ctx: TenantContext = Depends(get_tenant),
    svc: PipelineService = Depends(get_pipeline_service),
):
    checklist = None
    if req.checklist:
        checklist = PreCitationChecklist(
            worker_id_and_contract=req.checklist.worker_id_and_contract,
            facts_and_date=req.checklist.facts_and_date,
            at_least_one_proof=req.checklist.at_least_one_proof,
            infringed_norm=req.checklist.infringed_norm,
        )
    try:
        proc = svc.cite(
            ctx, process_id,
            citation_date=req.citation_date,
            checklist=checklist,
            notification_proof_id=req.notification_proof_id,
            override_reason=req.override_reason,
        )
    except PipelineError as exc:
        _pipeline_error(exc)
    return proc.to_dict()


# ── POST /api/disciplinary/{process_id}/session ──────────────────────────────

class AttendeeIn(BaseModel):
    name: str
    role: str
    identification: str | None = None


class SessionRequest(BaseModel):
    session_date: date
    attendees: list[AttendeeIn]
    transcript: str = ""
    instructor_signed: bool = True
    worker_signed: bool = False
    worker_refusal: bool = False
    witnesses: list[AttendeeIn] = Field(default_factory=list)
    override_reason: str | None = None


@router.post("/{process_id}/session")
def record_session(
    process_id: str,
    req: SessionRequest,
    ctx: TenantContext = Depends(get_tenant),
    svc: PipelineService = Depends(get_pipeline_service),
):
    attendees = [Attendee(a.name, a.role, a.identification) for a in req.attendees]  # type: ignore[arg-type]
    witnesses = [Attendee(w.name, w.role, w.identification) for w in req.witnesses]  # type: ignore[arg-type]
    signatures = ActaSignatures(
        instructor_signed=req.instructor_signed,
        worker_signed=req.worker_signed,
        worker_refusal=req.worker_refusal,
        witnesses=witnesses,
    )
    try:
        proc = svc.record_session(
            ctx, process_id,
            session_date=req.session_date,
            attendees=attendees,
            transcript=req.transcript,
            signatures=signatures,
            override_reason=req.override_reason,
        )
    except PipelineError as exc:
        _pipeline_error(exc)
    return proc.to_dict()


# ── POST /api/disciplinary/{process_id}/absence ──────────────────────────────

class AbsenceRequest(BaseModel):
    session_date: date
    action: str   # "reschedule" | "proceed_in_absence"
    reason: str


@router.post("/{process_id}/absence")
def record_absence(
    process_id: str,
    req: AbsenceRequest,
    ctx: TenantContext = Depends(get_tenant),
    svc: PipelineService = Depends(get_pipeline_service),
):
    if req.action not in {"reschedule", "proceed_in_absence"}:
        from fastapi import HTTPException
        raise HTTPException(status_code=422,
                            detail="action debe ser 'reschedule' o 'proceed_in_absence'")
    try:
        proc = svc.record_absence(
            ctx, process_id,
            session_date=req.session_date,
            action=req.action,
            reason=req.reason,
        )
    except PipelineError as exc:
        _pipeline_error(exc)
    return proc.to_dict()


# ── POST /api/disciplinary/{process_id}/contrast ─────────────────────────────

class ContrastRequest(BaseModel):
    falta_tipificada: bool = True
    comunicacion_apertura_formal: bool = False
    formulacion_cargos_concretos: bool = False
    traslado_pruebas: bool = False
    termino_defensa_minimo: bool = False
    oportunidad_descargos: bool = False
    decision_motivada: bool = True
    derecho_impugnacion: bool = True
    derecho_acompanamiento_informado: bool = True


@router.post("/{process_id}/contrast")
def contrast(
    process_id: str,
    req: ContrastRequest,
    ctx: TenantContext = Depends(get_tenant),
    svc: PipelineService = Depends(get_pipeline_service),
):
    try:
        proc = svc.contrast(ctx, process_id, req.model_dump())
    except PipelineError as exc:
        _pipeline_error(exc)
    return proc.to_dict()


# ── POST /api/disciplinary/{process_id}/decision ─────────────────────────────

class DecisionRequest(BaseModel):
    falta_level: str   # "leve" | "grave" | "gravisima"
    is_reincidence: bool = False
    chosen_sanction: str
    decision_text: str
    lawyer_id: str


@router.post("/{process_id}/decision")
def decide(
    process_id: str,
    req: DecisionRequest,
    ctx: TenantContext = Depends(get_tenant),
    svc: PipelineService = Depends(get_pipeline_service),
):
    if req.falta_level not in {"leve", "grave", "gravisima"}:
        from fastapi import HTTPException
        raise HTTPException(status_code=422,
                            detail="falta_level debe ser 'leve', 'grave' o 'gravisima'")
    if req.chosen_sanction not in {"llamado_atencion", "suspension", "terminacion_justa_causa"}:
        from fastapi import HTTPException
        raise HTTPException(status_code=422,
                            detail="chosen_sanction inválida")
    try:
        proc = svc.decide(
            ctx, process_id,
            falta_level=req.falta_level,  # type: ignore[arg-type]
            is_reincidence=req.is_reincidence,
            chosen_sanction=req.chosen_sanction,  # type: ignore[arg-type]
            decision_text=req.decision_text,
            lawyer_id=req.lawyer_id,
        )
    except PipelineError as exc:
        _pipeline_error(exc)
    return proc.to_dict()


# ── POST /api/disciplinary/{process_id}/appeal ───────────────────────────────

class AppealRequest(BaseModel):
    appealed_by: str
    resolver_id: str


@router.post("/{process_id}/appeal")
def open_appeal(
    process_id: str,
    req: AppealRequest,
    ctx: TenantContext = Depends(get_tenant),
    svc: PipelineService = Depends(get_pipeline_service),
):
    try:
        proc = svc.open_appeal(
            ctx, process_id,
            appealed_by=req.appealed_by,
            resolver_id=req.resolver_id,
        )
    except PipelineError as exc:
        _pipeline_error(exc)
    return proc.to_dict()


# ── POST /api/disciplinary/{process_id}/close ────────────────────────────────

class CloseRequest(BaseModel):
    reason: str | None = None


@router.post("/{process_id}/close")
def close_process(
    process_id: str,
    req: CloseRequest,
    ctx: TenantContext = Depends(get_tenant),
    svc: PipelineService = Depends(get_pipeline_service),
):
    try:
        proc = svc.close_process(ctx, process_id, reason=req.reason)
    except PipelineError as exc:
        _pipeline_error(exc)
    return proc.to_dict()
