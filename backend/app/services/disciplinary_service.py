"""
Motor 2 — Servicio del proceso disciplinario (J2 transcripción + J3 guardián + J4 docs).

El cerebro es el guardián de 7 garantías (`app.domain.disciplinary.guardian`, art. 115
Ley 2466/2025), determinista. Su veredicto tiene poder de VETO: la **decisión
sancionatoria** se marca BLOQUEADA si el proceso no puede proceder (no se emite una
sanción válida sobre un proceso viciado). La citación y el acta sí se generan siempre.

Forma de salida pensada para el frontend: 3 documentos con `type`/`title`/
`body_markdown`/`citations` (+ `blocked_if_nullity` en la decisión). El esqueleto lleva
las citas inyectadas por código; el LLM solo amplía la prosa y degrada honestamente al
esqueleto si no hay API.

El motor de documentos más rico (con cargos concretos) vive en
`app.domain.disciplinary.pliego` y se usa cuando hay datos de caso; este servicio cubre
el flujo del frontend (payload delgado: estado + transcripción).
"""
from __future__ import annotations

from datetime import date as _date

from app.core.tenancy import TenantContext
from app.core.audit import AuditLog
from app.core.errors import BlockedOutput
from app.domain.disciplinary.guardian import DiligenceState, evaluate
from app.adapters.transcription.whisper_client import transcribe
from app.adapters.llm.claude_client import ClaudeClient
from app.adapters.telephony.elevenlabs_client import ElevenLabsDescargosClient
from app.adapters.telephony import descargos_agent as agent
from app.adapters.telephony.mapping import (
    diligence_state_from_payload,
    diligence_state_from_conversation,
)
from app.adapters.telephony.whatsapp_client import TwilioWhatsAppClient, normalize_co


def _build_evidence_message(
    *, company_name: str, worker_name: str, charges_summary: str,
    evidence_names: list[str], call_date: str | None, call_time: str,
    response_deadline: str, lawyer_name: str = "",
) -> str:
    """Párrafo de contexto que viaja con la evidencia por WhatsApp. Determinista
    (no depende del LLM): es una citación formal, debe ser literal y reproducible."""
    pruebas = "; ".join(evidence_names) if evidence_names else "las que obran en el expediente"
    cita = (f"el {call_date} a las {call_time}" if call_date
            else f"en la fecha que se le indicará, a las {call_time}")
    # Quién lleva el proceso (para que el trabajador sepa con qué abogado trata).
    firma = (f"El proceso es conducido por {lawyer_name}, en representación de {company_name}.\n\n"
             if lawyer_name else "")
    return (
        f"{company_name} — Proceso disciplinario\n\n"
        f"Estimado/a {worker_name}:\n\n"
        f"Le informamos que la empresa inició un proceso disciplinario en su contra por los "
        f"siguientes hechos: {charges_summary}.\n\n"
        f"Adjuntamos la(s) prueba(s) que sustentan los cargos: {pruebas}.\n\n"
        f"Se le cita a una diligencia de descargos que se realizará por llamada telefónica "
        f"{cita}, en la cual podrá ejercer su derecho de defensa y contradicción "
        f"(art. 29 C.N. y art. 115 C.S.T.). Tiene derecho a estar acompañado por un "
        f"representante del sindicato o dos compañeros de trabajo. Dispone de un término de "
        f"{response_deadline} para complementar sus descargos por escrito.\n\n"
        f"{firma}"
        f"Esta comunicación es una citación formal; la llamada será grabada como constancia. "
        f"El tratamiento de sus datos se hace conforme a la ley de habeas data."
    )

_MESES_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
             "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def _fecha_es(d: _date) -> str:
    return f"{d.day} de {_MESES_ES[d.month - 1]} de {d.year}"


# Plantillas DETERMINISTAS, rellenas con la data real del trabajador. Sin LLM:
# la información del empleado queda garantizada y el formato es siempre limpio.
_TPL_CITACION = """\
# CITACIÓN A DILIGENCIA DE DESCARGOS

**{company_name}**
{today}

Señor(a)
**{worker_name}**
C.C. {worker_id}

**Asunto:** Citación a diligencia de descargos — proceso disciplinario

Respetado(a) señor(a):

Por medio de la presente, **{company_name}** le cita formalmente a una diligencia de
descargos, con el fin de que ejerza su derecho de defensa y contradicción frente a los
siguientes hechos que se le imputan:

> {charges}

| | |
|---|---|
| **Fecha y hora de la diligencia** | {diligence_date} |
| **Modalidad** | Llamada telefónica grabada |
| **Término para preparar su defensa** | mínimo cinco (5) días hábiles |

Esta citación se realiza en garantía del **debido proceso** consagrado en el artículo 29
de la Constitución Política y el artículo 115 del Código Sustantivo del Trabajo. Usted
tiene derecho a **estar acompañado** por un representante del sindicato o por dos
compañeros de trabajo, y a presentar las pruebas que considere pertinentes.

Atentamente,

**{lawyer_name}**
En representación de {company_name}
"""

_TPL_ACTA = """\
# ACTA DE DILIGENCIA DE DESCARGOS

**{company_name}**

| | |
|---|---|
| **Trabajador** | {worker_name} |
| **Documento de identidad** | C.C. {worker_id} |
| **Fecha de la diligencia** | {diligence_date} |
| **Conduce la diligencia** | {lawyer_name} |
| **Modalidad** | Llamada telefónica grabada |

**Hechos / cargos formulados:**

> {charges}

**Desarrollo de la diligencia:**

Siendo la fecha y hora señaladas, se dio inicio a la diligencia de descargos. Se leyeron
al trabajador los cargos imputados y se le garantizó el derecho de defensa y
contradicción. A continuación se deja constancia de los descargos rendidos por el
trabajador:

> {transcript}

**Constancia del debido proceso:** se garantizó al trabajador el derecho de audiencia,
defensa y contradicción conforme al artículo 115 del Código Sustantivo del Trabajo y al
artículo 29 de la Constitución Política.

Se da por terminada la diligencia.

___________________________
**{lawyer_name}**
En representación de {company_name}

___________________________
**{worker_name}**
C.C. {worker_id} — Trabajador
"""

_TPL_DECISION = """\
# DECISIÓN FINAL DEL PROCESO DISCIPLINARIO

**{company_name}**
{today}

| | |
|---|---|
| **Trabajador** | {worker_name} |
| **Documento de identidad** | C.C. {worker_id} |
| **Diligencia de descargos** | {diligence_date} |

**Hechos / cargos:**

> {charges}

**CONSIDERACIONES:**

Agotado el debido proceso conforme al artículo 115 del Código Sustantivo del Trabajo y
al artículo 29 de la Constitución Política, habiendo garantizado al trabajador el
derecho de audiencia, defensa y contradicción, y valorados los descargos rendidos, esta
empresa procede a emitir la siguiente decisión:

**DECISIÓN:** _[La empresa expone aquí la sanción o absolución, con los fundamentos de
hecho y de derecho que la sustentan.]_

Contra esta decisión procede el recurso de impugnación (doble instancia) ante un
superior distinto de quien la profirió, dentro de los cinco (5) días hábiles siguientes
a su notificación.

**{lawyer_name}**
En representación de {company_name}
"""

_TPL = {
    "citacion_descargos": _TPL_CITACION,
    "acta_descargos": _TPL_ACTA,
    "decision_final": _TPL_DECISION,
}


def _build_document(doc_type: str, ctx_doc: dict, state: DiligenceState) -> str:
    """Rellena la plantilla del documento con la data real (determinista)."""
    return _TPL[doc_type].format(**ctx_doc)

_DECISION_BLOQUEADA = """\
## Decisión Final — BLOQUEADA por el Guardián

> ⚠️ **El proceso no puede proceder a sanción.** Clasificación del debido proceso:
> **{clasificacion}** ({garantias_ok}/{garantias_total} garantías).

**Vicios detectados:**
{vicios}

Emitir una sanción sobre este proceso la haría **anulable**: si sustenta un despido,
puede convertirse en injustificado (art. 64 CST) con indemnización y salarios.

**Recomendación:** {recomendacion}
"""

_DOC_CITATIONS: dict[str, list[dict]] = {
    "citacion_descargos": [
        {"norm_id": "CST", "article": "art. 115", "title": "Procedimiento disciplinario",
         "url": "https://www.secretariasenado.gov.co/cst-articulo-115", "verified": True},
        {"norm_id": "CN", "article": "art. 29", "title": "Debido proceso",
         "url": "https://www.secretariasenado.gov.co/constitucion-politica/articulo-29", "verified": True},
    ],
    "acta_descargos": [
        {"norm_id": "CST", "article": "art. 115", "title": "Procedimiento disciplinario",
         "url": "https://www.secretariasenado.gov.co/cst-articulo-115", "verified": True},
    ],
    "decision_final": [
        {"norm_id": "CST", "article": "art. 115", "title": "Procedimiento disciplinario",
         "url": "https://www.secretariasenado.gov.co/cst-articulo-115", "verified": True},
        {"norm_id": "CN", "article": "art. 29", "title": "Debido proceso",
         "url": "https://www.secretariasenado.gov.co/constitucion-politica/articulo-29", "verified": True},
    ],
}

_DOC_TITLES = {
    "citacion_descargos": "Citación a descargos",
    "acta_descargos": "Acta de la diligencia de descargos",
    "decision_final": "Decisión final",
}


class DisciplinaryService:
    def __init__(self, llm: ClaudeClient, audit: AuditLog,
                 telephony: ElevenLabsDescargosClient | None = None,
                 whatsapp: TwilioWhatsAppClient | None = None) -> None:
        self._llm = llm
        self._audit = audit
        self._tel = telephony or ElevenLabsDescargosClient()
        self._wa = whatsapp or TwilioWhatsAppClient()

    def transcribe_session(self, ctx: TenantContext, audio: bytes) -> dict:
        t = transcribe(audio)
        return {"transcript": t.text, "segments": t.segments}

    def run_guardian(self, ctx: TenantContext, state: DiligenceState) -> dict:
        verdict = evaluate(state)                       # 7 garantías, dominio puro
        self._audit.record(ctx, "disciplinary.guardian", ctx.tenant_id,
                           grounding=[v.norma for v in verdict.vicios])
        # __dict__ conserva los objetos (vicios/missing_steps) que el router
        # post-procesa con _serialize_step. FastAPI los serializa en la respuesta.
        return verdict.__dict__

    # -- J1: telefonía de descargos (patrón AFFIRMA) --------------------------

    def start_descargos_call(self, ctx: TenantContext, case: agent.DescargosCase,
                             to_number: str) -> dict:
        """Configura el agente para ESTE caso y lanza la llamada al trabajador.
        La llamada solo CONDUCE y CAPTURA; el guardián (código puro) DECIDE."""
        self._tel.configure_agent(case)
        result = self._tel.place_call(to_number)
        self._audit.record(ctx, "disciplinary.call.started", ctx.tenant_id,
                           grounding=[case.session_id])
        return {"session_id": case.session_id, **result}

    def ingest_call_result(self, ctx: TenantContext, payload: dict | None = None,
                           conversation: dict | None = None,
                           term_respected: bool | None = None) -> dict:
        """Post-llamada: arma el DiligenceState (del webhook o de la conversación)
        y corre el GUARDIÁN. El veredicto sale del código puro, no del LLM."""
        src = payload or ((conversation or {}).get("analysis", {}).get("data_collection_results") or {})
        pt = src.get("process_type")
        pt = pt.get("value") if isinstance(pt, dict) else pt
        tipo_actuacion = ("despido_justa_causa"
                          if pt == "garantia_defensa_predespido" else "sancion_disciplinaria")

        if payload:
            state = diligence_state_from_payload(payload, term_respected=term_respected,
                                                 tipo_actuacion=tipo_actuacion)
        elif conversation is not None:
            state = diligence_state_from_conversation(conversation, term_respected=term_respected,
                                                      tipo_actuacion=tipo_actuacion)
        else:
            raise ValueError("Se requiere payload del webhook o la conversación.")
        verdict = self.run_guardian(ctx, state)
        return {"diligence_state": state.__dict__, **verdict}

    def fetch_call_result(self, ctx: TenantContext, conversation_id: str,
                          term_respected: bool | None = None) -> dict:
        """Jala la conversación REAL de ElevenLabs (transcript + data collection),
        arma el descargo y corre el guardián. Port de AFFIRMA `ingest.fetch_conversation`.
        Sin credenciales -> el cliente lanza TelephonyError (el router lo traduce)."""
        conv = self._tel.fetch_conversation(conversation_id)
        status = conv.get("status") or "unknown"
        turns = [t for t in (conv.get("transcript") or []) if (t.get("message") or "").strip()]
        transcript = "\n".join(
            f"[{t.get('role')}] {t.get('message')}" for t in turns
        )
        # Turnos estructurados (rol + mensaje) para renderizar la conversación completa.
        turns_out = [
            {"role": ("trabajador" if t.get("role") == "user" else "agente"),
             "message": (t.get("message") or "").strip()}
            for t in turns
        ]
        dc = ((conv.get("analysis") or {}).get("data_collection_results")) or {}

        def _dcval(k: str):
            v = dc.get(k)
            return v.get("value") if isinstance(v, dict) else v

        # El descargo: el resumen estructurado del agente, o las intervenciones del trabajador.
        descargo = (_dcval("worker_response_summary") or "").strip()
        if not descargo:
            descargo = " ".join(
                (t.get("message") or "") for t in turns if t.get("role") == "user"
            ).strip()

        state = diligence_state_from_conversation(conv, term_respected=term_respected)
        verdict = self.run_guardian(ctx, state)
        self._audit.record(ctx, "disciplinary.call.fetched", ctx.tenant_id,
                           grounding=[conversation_id, status])
        return {
            "conversation_id": conversation_id, "status": status,
            "transcript": transcript, "turns": turns_out, "descargo": descargo,
            "diligence_state": state.__dict__, **verdict,
        }

    # -- J1: WhatsApp de evidencia + contexto ---------------------------------

    def send_evidence_whatsapp(
        self, ctx: TenantContext, *, to_number: str, worker_name: str,
        company_name: str, charges_summary: str,
        evidence_names: list[str] | None = None,
        evidence_urls: list[str] | None = None,
        call_date: str | None = None, call_time: str = "10:00 a.m.",
        response_deadline: str = "cinco (5) días hábiles",
        lawyer_name: str = "",
    ) -> dict:
        """Envía la evidencia + el párrafo de contexto al WhatsApp del trabajador.
        Sin credenciales Twilio: devuelve un PREVIEW (sent=False) — nunca finge."""
        body = _build_evidence_message(
            company_name=company_name, worker_name=worker_name,
            charges_summary=charges_summary, evidence_names=evidence_names or [],
            call_date=call_date, call_time=call_time, response_deadline=response_deadline,
            lawyer_name=lawyer_name,
        )
        to = normalize_co(to_number)
        media = evidence_urls or []
        names = evidence_names or []
        base = {"to": to, "body": body, "media": media,
                "configured": self._wa.configured()}
        if not to:
            return {**base, "sent": False, "error": "Número de WhatsApp inválido."}
        if not self._wa.configured():
            # Demo-safe: el front muestra el mensaje que se enviaría al conectar Twilio.
            return {**base, "sent": False, "preview": True}
        # WhatsApp solo entrega 1 adjunto por mensaje: si hay varias pruebas, se manda
        # un mensaje por cada una (el primero con el cuerpo completo + prueba 1, los
        # siguientes con un encabezado corto "Prueba N/M" + su adjunto).
        try:
            messages: list[dict] = []
            if len(media) <= 1:
                res = self._wa.send(to, body=body, media_urls=media or None)
                messages.append(res)
            else:
                total = len(media)
                for i, url in enumerate(media):
                    if i == 0:
                        msg_body = body
                    else:
                        nombre = names[i] if i < len(names) else f"adjunto {i + 1}"
                        msg_body = f"Prueba {i + 1}/{total}: {nombre}"
                    messages.append(self._wa.send(to, body=msg_body, media_urls=[url]))
            self._audit.record(ctx, "disciplinary.whatsapp.sent", ctx.tenant_id,
                               grounding=[to])
            # Compat: campos del primer mensaje al tope + lista completa en `messages`.
            return {**base, "sent": True, "messages": messages, **messages[0]}
        except Exception as exc:  # noqa: BLE001
            return {**base, "sent": False, "error": str(exc)}

    # -- J1: contraste descargo ↔ cargos (asesor, no decide) ------------------

    async def contrast_descargo(
        self, ctx: TenantContext, *, charges_summary: str,
        evidence_summary: str, descargo_text: str,
    ) -> dict:
        """¿La defensa del trabajador responde a lo que se le imputó? Análisis de
        lenguaje (LLM) que el abogado revisa; NO decide el debido proceso."""
        result = await self._llm.analyze_descargo(
            charges_summary=charges_summary, evidence_summary=evidence_summary,
            descargo_text=descargo_text,
        )
        self._audit.record(ctx, "disciplinary.descargo.contrast", ctx.tenant_id,
                           grounding=[result.get("cobertura", "?"),
                                      result.get("evaluado_por", "?")])
        return result

    async def generate_documents(
        self, ctx: TenantContext, state: DiligenceState, transcript: str,
        lawyer_name: str = "", *,
        worker_name: str = "", worker_id: str = "", company_name: str = "",
        charges: str = "", diligence_date: str = "",
    ) -> dict:
        """Emite SIEMPRE los 3 documentos con la DATA REAL del empleado (deterministas:
        plantilla rellena, sin LLM → info garantizada y formato consistente). La decisión
        se marca BLOQUEADA si el guardián no permite proceder.

        `lawyer_name` firma; worker_name/worker_id/company_name/charges/diligence_date
        son los datos reales del trabajador y el caso."""
        verdict = evaluate(state)

        ctx_doc = {
            "worker_name": worker_name or "[Trabajador sin identificar]",
            "worker_id": worker_id or "—",
            "company_name": company_name or "La empresa",
            "charges": charges or "incumplimiento del reglamento interno de trabajo",
            "diligence_date": diligence_date or "según citación",
            "lawyer_name": lawyer_name or "Recursos Humanos",
            "today": _fecha_es(_date.today()),
            "transcript": transcript.strip() or "(El trabajador no rindió descargos.)",
        }

        documents = []
        for doc_type in ("citacion_descargos", "acta_descargos", "decision_final"):
            if doc_type == "decision_final" and not verdict.can_proceed:
                vicios = "\n".join(
                    f"- **{v.garantia}** ({v.norma}): {v.detalle}" for v in verdict.vicios
                ) or "- Debido proceso incompleto."
                body = _DECISION_BLOQUEADA.format(
                    clasificacion=verdict.clasificacion,
                    garantias_ok=verdict.garantias_ok, garantias_total=verdict.garantias_total,
                    vicios=vicios, recomendacion=verdict.recomendacion,
                )
            else:
                body = _build_document(doc_type, ctx_doc, state)
            documents.append({
                "type": doc_type,
                "title": _DOC_TITLES[doc_type],
                "body_markdown": body,
                "citations": _DOC_CITATIONS[doc_type],
                **({"blocked_if_nullity": True} if doc_type == "decision_final" else {}),
            })

        self._audit.record(ctx, "disciplinary.documents", ctx.tenant_id,
                           grounding=[verdict.clasificacion])
        return {"clasificacion": verdict.clasificacion, "documents": documents}

    async def generate_final_decision(self, ctx: TenantContext, state: DiligenceState) -> dict:
        """VETO duro (contrato histórico del Motor 2): lanza BlockedOutput si el proceso
        no puede proceder. Usado por flujos que exigen la decisión sí o sí."""
        if not evaluate(state).can_proceed:
            raise BlockedOutput("Decisión final bloqueada: hay nulidad pendiente.")
        res = await self.generate_documents(ctx, state, transcript="")
        decision = next(d for d in res["documents"] if d["type"] == "decision_final")
        return {"clasificacion": res["clasificacion"], "documents": [decision]}
