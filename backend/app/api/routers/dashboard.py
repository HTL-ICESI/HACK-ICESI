"""
GET /api/dashboard/exposure — M6. Número mágico + alertas para el dashboard del jurado.

El dataset demo de empresa-001 usa reference_date fija para reproducibilidad
(los días restantes se calculan siempre desde la misma fecha de referencia demo).
"""
from __future__ import annotations

from datetime import date, timedelta, datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.core.security import get_tenant
from app.core.tenancy import TenantContext
from app.api.deps import get_exposure_service, get_company_store, get_batch_service
from app.services.exposure_service import ExposureRequest, ExposureService
from app.services.company_service import CompanyAnalysisStore
from app.services.batch_service import BatchService
from app.domain.exposure.alerts import ContractContext
from app.adapters.telephony.whatsapp_client import TwilioWhatsAppClient, normalize_co

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

# Fecha de referencia: hoy, para que los días restantes sean siempre correctos.
_DEMO_REF = date.today()
_DEMO_COMPANY = "empresa-001"


def _demo_request() -> ExposureRequest:
    """
    Dataset demo: 50 trabajadores, 7 cláusulas obsoletas, 3 contratos con alertas reales.
    Reliquidaciones detectadas = 0 (M4 integra cuando esté listo; el COP sube al llegar).
    Estos números reproducen exactamente el response_example de contracts.json (bloque M6).
    """
    ref = _DEMO_REF
    return ExposureRequest(
        company_id=_DEMO_COMPANY,
        workers_at_risk=50,
        detected_reliquidations=0.0,
        total_clauses=30,
        outdated_clauses=7,
        reference_date=ref,
        year=2026,
        contracts=[
            # a1: término fijo vence en 14 días → alerta alta.
            # start < 365 días atrás → no dispara vacaciones.
            ContractContext(
                vinculo_type="termino_fijo",
                start_date=(ref - timedelta(days=200)).isoformat(),
                end_date=(ref + timedelta(days=14)).isoformat(),
                worker_id="***",
            ),
            # a2: trabajador con 400 días sin vacaciones → alerta media
            ContractContext(
                vinculo_type="termino_indefinido",
                start_date=(ref - timedelta(days=400)).isoformat(),
                end_date=None,
                worker_id="***",
            ),
            # a3: mora SS comprobada $480,000 COP → alerta alta.
            # start < 365 días atrás → no dispara vacaciones.
            ContractContext(
                vinculo_type="termino_indefinido",
                start_date=(ref - timedelta(days=169)).isoformat(),
                end_date=None,
                worker_id="***",
                pago_ss_mora=True,
                ss_amount_cop=480_000.0,
                ss_due_date=(ref + timedelta(days=5)).isoformat(),
            ),
        ],
    )


@router.get("/exposure")
def exposure_dashboard(
    company_id: str = Query(..., description="ID de la empresa cliente"),
    ctx: TenantContext = Depends(get_tenant),
    svc: ExposureService = Depends(get_exposure_service),
    store: CompanyAnalysisStore = Depends(get_company_store),
    batch_svc: BatchService = Depends(get_batch_service),
):
    """
    Número mágico (COP de exposición + % desactualización) + calendario de alertas.

    Prioridad de la fuente:
      1. Datos REALES del último análisis de la empresa (POST /api/company/analyze).
      2. Dataset demo de empresa-001 (solo si nunca se analizó nada).
      3. Empresa sin datos → exposición en cero (honesto, no inventa).
    """
    real = store.get(ctx.tenant_id)
    if real is None:
        # El Inicio deriva del MISMO lote que Compliance: si no hay exposición,
        # se reconstruye desde el último lote persistido (no se cae al demo).
        batch_svc.ensure_exposure(ctx)
        real = store.get(ctx.tenant_id)
    if real is not None:
        return svc.compute(ctx, real)
    if company_id == _DEMO_COMPANY:
        return svc.compute(ctx, _demo_request())
    return svc.compute(ctx, ExposureRequest(
        company_id=company_id,
        workers_at_risk=0,
        detected_reliquidations=0.0,
        total_clauses=1,
        outdated_clauses=0,
    ))


# ── Notificación de vacaciones por vencer (WhatsApp) ─────────────────────────

class VacacionesNotifyRequest(BaseModel):
    to_number: str
    worker_names: list[str]
    company_name: str = ""


def _vacation_message(worker_names: list[str], company_name: str) -> str:
    if len(worker_names) == 1:
        names_str = worker_names[0]
        plural = "tiene vacaciones próximas a vencer"
    else:
        names_str = ", ".join(worker_names[:-1]) + f" y {worker_names[-1]}"
        plural = "tienen vacaciones próximas a vencer"
    empresa = f" en {company_name}" if company_name else ""
    return (
        f"Hola 👋 Le informamos desde Cerebro Laboral HG que {names_str}"
        f"{empresa} {plural} (art. 186 CST).\n\n"
        "¿Desea programar sus vacaciones? Por favor responda a este mensaje "
        "o comuníquese con el área de RRHH para coordinar las fechas.\n\n"
        "— Cerebro Laboral · Hurtado Gandini Abogados"
    )


@router.post("/notify-vacations")
def notify_vacations(
    req: VacacionesNotifyRequest,
    ctx: TenantContext = Depends(get_tenant),
):
    """Envía WhatsApp al número indicado notificando vacaciones por vencer."""
    message = _vacation_message(req.worker_names, req.company_name)
    wa = TwilioWhatsAppClient()
    if not wa.configured():
        return {"sent": False, "preview": message, "to": req.to_number,
                "note": "Twilio no configurado — este es el mensaje que se enviaría."}
    to_e164 = normalize_co(req.to_number)
    result = wa.send(to_e164, body=message)
    return {"sent": True, "preview": message, **result}
