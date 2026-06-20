"""
Batch service — procesamiento masivo de contratos (caso real: bufete con 50-500).

Corre la pipeline M1→M2→M3→M4→M5 sobre cada contrato de un lote, de forma asíncrona,
y expone el progreso para que el frontend lo consulte por polling. Estado en memoria
(suficiente para el demo; en producción sería Redis/BD), aislado por tenant.

Reusa los servicios ya probados (ingest, extraction, compliance, liquidation,
remediation). Un error en un contrato NO detiene el lote: ese ítem queda `error` y el
resto continúa. Las cifras siguen siendo deterministas (M4) y las citas del corpus
(M3/M5); el LLM solo redacta prosa en M5.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import date

# Máximo de contratos procesados en paralelo. Limitado por rate-limit de Claude API
# (Haiku/Sonnet tienen ~5 req/s en el tier gratuito). 3 paralelos es seguro.
_CONCURRENCY = 3

from fastapi.encoders import jsonable_encoder

from app.core.tenancy import TenantContext
from app.core.audit import AuditLog
from app.domain.liquidation.engine import LiquidationInput, liquidate
from app.services.ingest_service import IngestService
from app.services.extraction_service import ExtractionService
from app.services.compliance_service import ComplianceService
from app.services.remediation_service import RemediationService
from app.services.exposure_service import ExposureRequest, ExposureService
from app.services.company_service import CompanyAnalysisStore, _contract_context
from app.domain.exposure.alerts import ContractContext


def _record_val(rec, key: str):
    """Lee record[key].value funcione el record como OBJETO (procesamiento vivo) o
    como DICT (lote rehidratado de la BD)."""
    f = rec.get(key) if isinstance(rec, dict) else getattr(rec, key, None)
    if isinstance(f, dict):
        return f.get("value")
    return getattr(f, "value", None)


def _cc_from_record(rec) -> ContractContext | None:
    """ContractContext (alertas M6) desde el record, sea objeto o dict. Sin nómina,
    así que no incluye mora SS (igual que la agregación del lote)."""
    start = _record_val(rec, "start_date")
    if not isinstance(start, str) or not start:
        return None
    end_v = _record_val(rec, "end_date")
    return ContractContext(
        vinculo_type=_record_val(rec, "vinculo_type") or "termino_indefinido",
        start_date=start,
        end_date=end_v if isinstance(end_v, str) else None,
        worker_id="***",
    )

_MAX_DIAS_LIQ = 360


def _num(field, default: float = 0.0) -> float:
    """Lee un campo del record como float, desenvolviendo Field.value y Money.value
    (el salario en M2 es un objeto Money: {value, currency, periodicity})."""
    if field is None:
        return default
    val = getattr(field, "value", field)       # Field.value -> puede ser Money
    val = getattr(val, "value", val)            # Money.value -> float
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _risk_level(summary: dict) -> str:
    if summary.get("by_severity", {}).get("alta", 0) > 0:
        return "alto"
    if summary.get("total_gaps", 0) > 0:
        return "medio"
    return "bajo"


def _liquidation_input(record) -> LiquidationInput:
    """M4 con datos del contrato + defaults operativos razonables (en producción el
    abogado completaría días/causa desde nómina). Termina como `sin_justa_causa` para
    reflejar la exposición económica máxima del contrato."""
    start = getattr(record.start_date, "value", None)
    end = getattr(record.end_date, "value", None)
    days = _MAX_DIAS_LIQ
    antiguedad = 1.0
    if isinstance(start, str):
        try:
            d0 = date.fromisoformat(start)
            d1 = date.fromisoformat(end) if isinstance(end, str) else date.today()
            delta = max(0, (d1 - d0).days)
            days = min(delta, _MAX_DIAS_LIQ)
            antiguedad = max(delta / 365.0, 0.0)
        except ValueError:
            pass
    return LiquidationInput(
        salario_basico=_num(getattr(record, "base_salary", None)),
        promedio_variable=_num(getattr(record, "salario_variable", None)),
        auxilio_transporte=_num(getattr(record, "auxilio_transporte", None)),
        days_worked=days,
        vinculo_type=str(getattr(record.vinculo_type, "value", None) or "termino_indefinido"),
        termination_cause="sin_justa_causa",
        antiguedad_anios=antiguedad,
    )


class BatchService:
    def __init__(self, ingest: IngestService, extraction: ExtractionService,
                 compliance: ComplianceService, liquidation, remediation: RemediationService,
                 audit: AuditLog, store: CompanyAnalysisStore, exposure: ExposureService) -> None:
        self._ingest = ingest
        self._extraction = extraction
        self._compliance = compliance
        self._liquidation = liquidation
        self._remediation = remediation
        self._audit = audit
        self._store = store          # alimenta el dashboard de Inicio (número mágico + alertas)
        self._exposure = exposure
        # batch_id -> {tenant_id, total, completed, results: {doc_id: {...}}, order: [doc_id]}
        self._batches: dict[str, dict] = {}
        # último batch por tenant → permite revisitar el lote sin recordar el id
        self._last_by_tenant: dict[str, str] = {}

    # ── API pública ─────────────────────────────────────────────────────────
    def create_batch(self, ctx: TenantContext, files: list[tuple[str, bytes]]) -> dict:
        batch_id = uuid.uuid4().hex[:8]
        results: dict[str, dict] = {}
        order: list[str] = []
        for i, (fname, _) in enumerate(files):
            doc_id = f"{batch_id}-{i:03d}"
            order.append(doc_id)
            results[doc_id] = {"doc_id": doc_id, "filename": fname, "status": "pending"}
        self._batches[batch_id] = {
            "tenant_id": ctx.tenant_id, "total": len(files),
            "completed": 0, "results": results, "order": order,
        }
        self._last_by_tenant[ctx.tenant_id] = batch_id
        self._audit.record(ctx, "batch.create", batch_id, grounding=[f"total={len(files)}"])
        asyncio.create_task(self._process(batch_id, ctx, files, order))
        return {"batch_id": batch_id, "total": len(files), "files": [f for f, _ in files]}

    def latest(self, ctx: TenantContext) -> dict | None:
        """Último lote analizado por este tenant (para revisitarlo sin recordar el id)."""
        batch_id = self._last_by_tenant.get(ctx.tenant_id) or self._rehydrate_latest(ctx.tenant_id)
        return self.status(ctx, batch_id) if batch_id else None

    def ensure_exposure(self, ctx: TenantContext) -> bool:
        """El dashboard (Inicio) deriva del MISMO lote que Compliance. Si no hay
        exposición para el tenant, la reconstruye desde el último lote persistido
        (cubre lotes procesados antes de existir la persistencia de exposición, y
        reinicios del backend). Devuelve True si quedó poblada."""
        if self._store.get(ctx.tenant_id) is not None:
            return True
        batch_id = self._last_by_tenant.get(ctx.tenant_id) or self._rehydrate_latest(ctx.tenant_id)
        if not batch_id:
            return False
        b = self._batches.get(batch_id) or self._rehydrate(ctx.tenant_id, batch_id)
        if not b:
            return False
        self._aggregate_to_dashboard(ctx, b)   # dict-aware → puebla + persiste exposición
        return self._store.get(ctx.tenant_id) is not None

    def status(self, ctx: TenantContext, batch_id: str) -> dict | None:
        b = self._batches.get(batch_id) or self._rehydrate(ctx.tenant_id, batch_id)
        if b is None or b["tenant_id"] != ctx.tenant_id:   # aislamiento por tenant
            return None
        return {
            "batch_id": batch_id, "total": b["total"], "completed": b["completed"],
            "results": [self._summary_view(b["results"][d]) for d in b["order"]],
        }

    def result(self, ctx: TenantContext, batch_id: str, doc_id: str) -> dict | None:
        b = self._batches.get(batch_id) or self._rehydrate(ctx.tenant_id, batch_id)
        if b is None or b["tenant_id"] != ctx.tenant_id:
            return None
        item = b["results"].get(doc_id)
        if item is None or item["status"] != "done":
            return None
        return item["full"]

    # ── Persistencia en BD (sobrevive reinicios del backend) ──────────────────
    def _persist(self, batch_id: str) -> None:
        """Guarda el snapshot completo del lote (jsonable) en la BD. Best-effort:
        un fallo de BD no interrumpe el procesamiento (el lote sigue en memoria)."""
        b = self._batches.get(batch_id)
        if b is None:
            return
        try:
            from app.db.base import SessionLocal
            from app.db.models import BatchSnapshot
            data = json.dumps(jsonable_encoder(b))
            with SessionLocal() as db:
                row = (db.query(BatchSnapshot)
                       .filter_by(tenant_id=b["tenant_id"], batch_id=batch_id).first())
                if row is None:
                    db.add(BatchSnapshot(tenant_id=b["tenant_id"], batch_id=batch_id,
                                         data_json=data))
                else:
                    row.data_json = data
                db.commit()
        except Exception:  # noqa: BLE001 — la persistencia es un extra, no un bloqueo
            pass

    def _rehydrate(self, tenant_id: str, batch_id: str | None) -> dict | None:
        """Carga un lote desde la BD a memoria si no está (tras reinicio)."""
        if not batch_id:
            return None
        try:
            from app.db.base import SessionLocal
            from app.db.models import BatchSnapshot
            with SessionLocal() as db:
                row = (db.query(BatchSnapshot)
                       .filter_by(tenant_id=tenant_id, batch_id=batch_id).first())
                if row is None:
                    return None
                b = json.loads(row.data_json)
            self._batches[batch_id] = b
            self._last_by_tenant.setdefault(tenant_id, batch_id)
            return b
        except Exception:  # noqa: BLE001
            return None

    def _rehydrate_latest(self, tenant_id: str) -> str | None:
        """Recupera el batch_id del último lote del tenant desde la BD."""
        try:
            from app.db.base import SessionLocal
            from app.db.models import BatchSnapshot
            with SessionLocal() as db:
                row = (db.query(BatchSnapshot)
                       .filter_by(tenant_id=tenant_id)
                       .order_by(BatchSnapshot.updated_at.desc()).first())
                if row is None:
                    return None
                batch_id = row.batch_id
                b = json.loads(row.data_json)
            self._batches[batch_id] = b
            self._last_by_tenant[tenant_id] = batch_id
            return batch_id
        except Exception:  # noqa: BLE001
            return None

    # ── Procesamiento ─────────────────────────────────────────────────────────
    async def _process(self, batch_id: str, ctx: TenantContext,
                       files: list[tuple[str, bytes]], order: list[str]) -> None:
        b = self._batches[batch_id]
        sem = asyncio.Semaphore(_CONCURRENCY)

        async def _run_one(doc_id: str, fname: str, content: bytes) -> None:
            async with sem:
                item = b["results"][doc_id]
                item["status"] = "processing"
                try:
                    item.update(await self._process_one(ctx, doc_id, fname, content))
                    item["status"] = "done"
                except Exception as exc:
                    item["status"] = "error"
                    item["error"] = f"{type(exc).__name__}: {exc}"[:200]
                b["completed"] += 1
                self._persist(batch_id)

        # Todos los contratos en paralelo (acotado por el semáforo).
        await asyncio.gather(*[
            _run_one(doc_id, fname, content)
            for doc_id, (fname, content) in zip(order, files)
        ])

        # ── Agregación → alimenta el dashboard de Inicio (número mágico + alertas) ──
        # El lote completo deriva la exposición REAL de la empresa, igual que el
        # orquestador /company/analyze. Reemplaza (no acumula) por tenant.
        self._aggregate_to_dashboard(ctx, b)
        self._persist(batch_id)                            # snapshot final del lote

    def _aggregate_to_dashboard(self, ctx: TenantContext, b: dict) -> None:
        gap_results: list[dict] = []
        contracts = []
        exposicion_liquidaciones = 0.0   # M4: suma de la exposición económica real del lote
        for doc_id in b["order"]:
            item = b["results"][doc_id]
            if item["status"] != "done":
                continue
            gap_results.append(item["full"]["compliance"])
            cc = _cc_from_record(item["full"]["extract"]["record"])
            if cc is not None:
                contracts.append(cc)
            liq_items = (item["full"].get("liquidation") or {}).get("items") or {}
            try:
                exposicion_liquidaciones += float(liq_items.get("total", 0) or 0)
            except (TypeError, ValueError):
                pass
        if not gap_results:
            return
        # El Inicio muestra la exposición económica REAL del lote (suma de liquidaciones
        # M4) — EXACTAMENTE el total que muestra Compliance, no un demo ni un proxy de
        # sanciones. Por eso workers_at_risk no infla el COP (se pone en 0).
        req = ExposureRequest.from_m3_gaps(
            company_id=ctx.tenant_id,
            gap_results=gap_results,
            contracts=contracts,
            detected_reliquidations=exposicion_liquidaciones,
        )
        req.workers_at_risk = 0   # el COP = liquidaciones, sin sumar × SMLMV encima
        self._store.put(ctx.tenant_id, req)
        self._audit.record(ctx, "batch.aggregate", ctx.tenant_id,
                           grounding=[f"contratos={len(gap_results)}"])

    async def _process_one(self, ctx: TenantContext, doc_id: str,
                           fname: str, content: bytes) -> dict:
        ing = self._ingest.ingest_document(ctx, doc_id, content, fname)        # M1
        record = await self._extraction.extract(ctx, doc_id, ing.text)         # M2
        analysis = self._compliance.analyze(ctx, doc_id, record, "contrato")   # M3
        liq_inp = _liquidation_input(record)
        liq = self._liquidation.compute(ctx, doc_id, liq_inp)                   # M4
        liq_items = liq.__dict__
        # Request EXACTO usado (para re-exportar el Excel HG con cifras idénticas).
        # Datos del trabajador y contrato para el Excel de liquidación.
        emp_obj   = getattr(record, "employer", None)
        emp_val   = getattr(emp_obj, "value", None)
        emp_name  = (emp_val.get("name") if isinstance(emp_val, dict)
                     else getattr(emp_val, "name", None)) or ""
        wk_name   = str(getattr(record.empleado_nombre, "value", None) or "")
        wk_doc_raw = getattr(record, "empleado_doc", None)
        wk_doc    = str(getattr(wk_doc_raw, "value", None) or "")
        if wk_doc and not wk_doc.upper().startswith("C.C"):
            wk_doc = f"C.C. {wk_doc}"
        cargo_val  = getattr(record, "cargo", None)
        cargo_str  = str(getattr(cargo_val, "value", None) or "")
        start_val  = getattr(record, "start_date", None)
        start_str  = str(getattr(start_val, "value", None) or "") or None
        vinculo_v  = str(getattr(getattr(record, "vinculo_type", None), "value", None) or "")
        _vinculo_labels = {
            "termino_indefinido": "Término indefinido",
            "termino_fijo":        "Término fijo",
            "obra_o_labor":        "Obra o labor",
            "prestacion_servicios":"Prestación de servicios",
        }
        fecha_hoy = date.today().isoformat()
        liq_request = {
            "doc_id": doc_id,
            "monthly_salary": liq_inp.salario_basico,
            "days_worked": liq_inp.days_worked,
            "vinculo_type": liq_inp.vinculo_type,
            "promedio_variable": liq_inp.promedio_variable,
            "auxilio_transporte": liq_inp.auxilio_transporte,
            "dias_pendientes_vacaciones": liq_inp.dias_pendientes_vacaciones,
            "termination_cause": liq_inp.termination_cause,
            "months_remaining_fixed": liq_inp.months_remaining_fixed,
            "antiguedad_anios": liq_inp.antiguedad_anios,
            "bonificacion": liq_inp.bonificacion,
            # Datos para el Excel (formato Liquidacion_Andres.xlsx)
            "nombre_trabajador":   wk_name,
            "documento_identidad": wk_doc,
            "cargo":               cargo_str,
            "centro_costos":       "",
            "nombre_empresa":      emp_name,
            "vinculo_type_label":  _vinculo_labels.get(vinculo_v, "Término indefinido"),
            "fecha_inicio":        start_str,
            "fecha_terminacion":   fecha_hoy,
            "motivo_terminacion":  "Sin justa causa",
            "dias_ultimo_periodo": date.today().day,
        }

        remediation = None                                                     # M5 (gap[0])
        gaps = analysis["gaps"]
        if gaps:
            remediation = await self._remediation.generate(
                ctx, doc_id, gaps[0], liq_items,
                doc_type=gaps[0].get("remedy_type", "otrosi"), record=record,
            )

        emp = getattr(record.employer, "value", None)
        employer_name = (emp.get("name") if isinstance(emp, dict)
                         else getattr(emp, "name", None)) or "—"
        summary = {
            "worker_name": str(getattr(record.empleado_nombre, "value", None) or "—"),
            "employer_name": str(employer_name),
            "risk_level": _risk_level(analysis["summary"]),
            "risk_score": analysis["summary"]["risk_score"],
            "total_exposure": liq_items["total"],
            "gap_count": len(gaps),
            "gaps": [{"gap_id": g["gap_id"], "issue": g["issue"],
                      "severity": g["severity"], "remedy_type": g["remedy_type"]} for g in gaps],
        }
        full = {
            "doc_id": doc_id, "filename": fname,
            "text": ing.text,                       # texto completo del contrato (para leerlo/verificarlo)
            "extract": {"doc_id": doc_id, "record": record},
            "compliance": analysis,
            "liquidation": {"doc_id": doc_id, "items": liq_items, "deterministic": True,
                            "request": liq_request},
            "remediation": remediation,
        }
        return {"summary": summary, "full": full}

    @staticmethod
    def _summary_view(item: dict) -> dict:
        out = {"doc_id": item["doc_id"], "filename": item["filename"], "status": item["status"]}
        if "error" in item:
            out["error"] = item["error"]
        if "summary" in item:
            out["summary"] = item["summary"]
        return out
