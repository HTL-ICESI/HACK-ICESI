"""
Orquestador de empresa — el pegamento que vuelve la pipeline INTEGRAL.

Recibe un lote de archivos (o un ZIP) de una empresa cliente, los rutea y corre la
pipeline completa por documento:

    PDF/DOCX/TXT  → M1 ingesta → M2 extracción → M3 compliance   (+ M4 si hay nómina)
    XLSX/CSV      → parser de nómina  (Bloque 3 — por ahora se registra, no se parsea)

Luego AGREGA los gaps de todos los contratos y deriva el número mágico REAL con
`ExposureRequest.from_m3_gaps()` (cero valores hardcodeados). Guarda el agregado por
tenant para que el dashboard (M6) lea datos reales, no un demo fijo.

La lógica jurídica NO vive aquí: este service solo coordina M1–M6 + audit.
"""
from __future__ import annotations

import csv
import io
import json
import zipfile
from datetime import date

from app.core.audit import AuditLog
from app.core.tenancy import TenantContext
from app.domain.exposure.alerts import ContractContext
from app.domain.liquidation.engine import LiquidationInput, liquidate
from app.services.ingest_service import IngestService
from app.services.extraction_service import ExtractionService
from app.services.compliance_service import ComplianceService
from app.services.exposure_service import ExposureService, ExposureRequest
from app.db.base import SessionLocal
from app.db.repository import TenantRepository
from app.db import models as dbm

_DOC_EXT = {"pdf", "docx", "txt"}
_NOMINA_EXT = {"csv"}   # CSV poblado (determinista). El FORMATO NÓMINA.xlsx real es plantilla vacía.
_MAX_DIAS_LIQ = 360     # tope conservador: 1 ciclo de prestaciones por trabajador


class CompanyAnalysisStore:
    """Almacén por tenant del último análisis. Persistido en BD: el dashboard lee
    datos reales aunque el backend se reinicie (no cae al demo)."""
    def __init__(self) -> None:
        self._by_tenant: dict[str, ExposureRequest] = {}

    def put(self, tenant_id: str, req: ExposureRequest) -> None:
        self._by_tenant[tenant_id] = req
        self._persist(tenant_id, req)

    def get(self, tenant_id: str) -> ExposureRequest | None:
        cached = self._by_tenant.get(tenant_id)
        if cached is not None:
            return cached
        loaded = self._load(tenant_id)              # tras reinicio: rehidrata de BD
        if loaded is not None:
            self._by_tenant[tenant_id] = loaded
        return loaded

    def clear(self) -> None:
        self._by_tenant.clear()

    # ── Persistencia ──────────────────────────────────────────────────────────
    @staticmethod
    def _persist(tenant_id: str, req: ExposureRequest) -> None:
        try:
            from fastapi.encoders import jsonable_encoder
            data = json.dumps(jsonable_encoder(req))
            with SessionLocal() as db:
                row = db.get(dbm.ExposureSnapshot, tenant_id)
                if row is None:
                    db.add(dbm.ExposureSnapshot(tenant_id=tenant_id, data_json=data))
                else:
                    row.data_json = data
                db.commit()
        except Exception:  # noqa: BLE001 — la persistencia es un extra, no un bloqueo
            pass

    @staticmethod
    def _load(tenant_id: str) -> ExposureRequest | None:
        try:
            with SessionLocal() as db:
                row = db.get(dbm.ExposureSnapshot, tenant_id)
                if row is None:
                    return None
                d = json.loads(row.data_json)
            ref = d.get("reference_date")
            return ExposureRequest(
                company_id=d["company_id"],
                workers_at_risk=d["workers_at_risk"],
                detected_reliquidations=d.get("detected_reliquidations", 0.0),
                total_clauses=d["total_clauses"],
                outdated_clauses=d["outdated_clauses"],
                contracts=[ContractContext(**c) for c in d.get("contracts", [])],
                reference_date=date.fromisoformat(ref) if ref else None,
                year=d.get("year", 2026),
            )
        except Exception:  # noqa: BLE001
            return None


def _ext(filename: str) -> str:
    return filename.lower().rsplit(".", 1)[-1] if "." in filename else ""


def _expand(files: list[tuple[str, bytes]]) -> list[tuple[str, bytes]]:
    """Descomprime cualquier .zip del lote en sus archivos internos (1 nivel)."""
    out: list[tuple[str, bytes]] = []
    for name, content in files:
        if _ext(name) == "zip":
            with zipfile.ZipFile(io.BytesIO(content)) as z:
                for info in z.infolist():
                    if info.is_dir() or info.filename.startswith("__MACOSX"):
                        continue
                    out.append((info.filename.rsplit("/", 1)[-1], z.read(info)))
        else:
            out.append((name, content))
    return out


def _digits(s) -> str:
    return "".join(c for c in str(s) if c.isdigit())


def _money_int(field) -> int:
    v = getattr(field, "value", None)
    if isinstance(v, dict):
        return int(v.get("value") or 0)
    return int(getattr(v, "value", v) or 0) if v is not None else 0


def _date_or_none(field):
    v = getattr(field, "value", None)
    try:
        return date.fromisoformat(v) if isinstance(v, str) and v else None
    except ValueError:
        return None


def _num(row: dict, key: str, default: float = 0.0) -> float:
    try:
        return float(str(row.get(key, "")).strip() or default)
    except (TypeError, ValueError):
        return default


def _parse_nomina_csv(content: bytes) -> dict[str, dict]:
    """Lee una nómina CSV (1 fila/trabajador) → dict por cédula (solo dígitos).
    Columnas: cedula, salario_basico, promedio_variable, auxilio_transporte,
    dias_pendientes_vacaciones, antiguedad_anios, pago_ss_mora, ss_monto_mora, ss_due_date."""
    out: dict[str, dict] = {}
    for row in csv.DictReader(io.StringIO(content.decode("utf-8-sig", "ignore"))):
        ced = _digits(row.get("cedula", ""))
        if ced:
            out[ced] = row
    return out


def _reliquidacion(record, nomina: dict[str, dict], ref: date) -> tuple[float, dict | None]:
    """Si el trabajador del contrato está en la nómina, M4 calcula sus prestaciones
    pendientes (cesantías+intereses+prima+vacaciones, base con el promedio variable
    REAL de la nómina). Devuelve (cop_prestaciones, fila) o (0.0, None) si no hay match."""
    fila = nomina.get(_digits(record.empleado_documento.value or ""))
    if fila is None:
        return 0.0, None

    start = record.start_date.value
    end = record.end_date.value if isinstance(record.end_date.value, str) else None
    days = _MAX_DIAS_LIQ
    if isinstance(start, str):
        try:
            d0 = date.fromisoformat(start)
            d1 = date.fromisoformat(end) if end else ref
            days = max(0, min((d1 - d0).days, _MAX_DIAS_LIQ))
        except ValueError:
            pass

    res = liquidate(LiquidationInput(
        salario_basico=_num(fila, "salario_basico"),
        promedio_variable=_num(fila, "promedio_variable"),
        auxilio_transporte=_num(fila, "auxilio_transporte"),
        days_worked=days,
        dias_pendientes_vacaciones=int(_num(fila, "dias_pendientes_vacaciones")),
        vinculo_type=str(record.vinculo_type.value or "termino_indefinido"),
        termination_cause="renuncia",  # base conservadora: solo prestaciones, sin indemnización
    ))
    return res.total_prestaciones, fila


class CompanyService:
    def __init__(
        self,
        ingest: IngestService,
        extraction: ExtractionService,
        compliance: ComplianceService,
        exposure: ExposureService,
        store: CompanyAnalysisStore,
        audit: AuditLog,
        session_factory=SessionLocal,
    ) -> None:
        self._ingest = ingest
        self._extraction = extraction
        self._compliance = compliance
        self._exposure = exposure
        self._store = store
        self._audit = audit
        self._session_factory = session_factory

    async def analyze_company(
        self, ctx: TenantContext, files: list[tuple[str, bytes]]
    ) -> dict:
        """
        Corre la pipeline sobre todos los archivos, agrega los gaps y deriva el
        número mágico real. Guarda el agregado por tenant. Devuelve el resumen por
        documento + el dashboard recalculado.
        """
        items = _expand(files)
        ref = date.today()

        # ── Pasada 1: parsear nóminas (para cruzar por cédula en la pasada 2) ──
        nomina: dict[str, dict] = {}
        nominas: list[str] = []
        for fname, content in items:
            if _ext(fname) in _NOMINA_EXT:
                nomina.update(_parse_nomina_csv(content))
                nominas.append(fname)

        gap_results: list[dict] = []
        contracts: list[ContractContext] = []
        documents: list[dict] = []
        reliquidaciones = 0.0

        self._ensure_tenant(ctx)
        self._clear_tenant_operational(ctx)   # re-análisis reemplaza, no duplica

        # ── Pasada 2: contratos ──────────────────────────────────────────────
        for i, (fname, content) in enumerate(items):
            ext = _ext(fname)
            doc_id = f"{ctx.tenant_id}-doc-{i+1}"

            if ext in _NOMINA_EXT:
                documents.append({"filename": fname, "tipo": "nomina",
                                  "status": "parseada",
                                  "trabajadores": len(_parse_nomina_csv(content))})
                continue
            if ext not in _DOC_EXT:
                documents.append({"filename": fname, "tipo": "desconocido",
                                  "status": "formato_no_soportado"})
                continue

            ing = self._ingest.ingest_document(ctx, doc_id, content, fname)
            if ing.status == "needs_human":
                documents.append({"filename": fname, "doc_id": doc_id,
                                  "tipo": "contrato", "status": "needs_human",
                                  "confidence": ing.confidence})
                continue

            record = await self._extraction.extract(ctx, doc_id, ing.text)
            analysis = self._compliance.analyze(ctx, doc_id, record, "contrato")
            gap_results.append(analysis)

            # M4: si el trabajador está en la nómina, calcula sus prestaciones reales.
            reliq, fila = _reliquidacion(record, nomina, ref)
            reliquidaciones += reliq

            cc = _contract_context(record, fila)
            if cc is not None:
                contracts.append(cc)

            # Persiste el contrato + sus gaps + su liquidación (BD, scoped por tenant).
            self._persist_contract(ctx, doc_id, fname, ing, record, analysis, reliq)

            documents.append({
                "filename": fname,
                "doc_id": doc_id,
                "tipo": "contrato",
                "status": ing.status,
                "empleado": record.empleado_nombre.value,
                "vinculo": record.vinculo_type.value,
                "gaps": [g["gap_id"] for g in analysis["gaps"]],
                "risk_score": analysis["summary"]["risk_score"],
                "prestaciones_pendientes": round(reliq, 2) if fila else None,
            })

        # ── Agregación → número mágico REAL (gaps + reliquidaciones de M4) ────
        req = ExposureRequest.from_m3_gaps(
            company_id=ctx.tenant_id,
            gap_results=gap_results,
            contracts=contracts,
            detected_reliquidations=reliquidaciones,
        )
        self._store.put(ctx.tenant_id, req)
        dashboard = self._exposure.compute(ctx, req)

        self._audit.record(
            ctx, "company.analyze", ctx.tenant_id,
            grounding=[f"contratos={len(gap_results)}", f"nominas={len(nominas)}"],
        )

        return {
            "company_id": ctx.tenant_id,
            "procesados": {
                "contratos": len(gap_results),
                "nominas": len(nominas),
                "needs_human": sum(1 for d in documents if d["status"] == "needs_human"),
            },
            "documents": documents,
            "dashboard": dashboard,
        }

    # ── Persistencia en BD (scoped por tenant) ───────────────────────────────
    def _ensure_tenant(self, ctx: TenantContext) -> None:
        db = self._session_factory()
        try:
            if db.get(dbm.Tenant, ctx.tenant_id) is None:
                db.add(dbm.Tenant(id=ctx.tenant_id, nombre=ctx.tenant_id))
                db.commit()
        finally:
            db.close()

    def _clear_tenant_operational(self, ctx: TenantContext) -> None:
        """Borra los datos operativos del tenant antes de re-persistir, para que
        re-analizar REEMPLACE (igual que el store del dashboard) y no duplique."""
        db = self._session_factory()
        try:
            tid = ctx.tenant_id
            for model in (dbm.Liquidacion, dbm.Gap, dbm.Alerta, dbm.Contrato,
                          dbm.Empleado, dbm.Documento):
                db.query(model).filter_by(tenant_id=tid).delete()
            db.commit()
        finally:
            db.close()

    def _persist_contract(self, ctx, doc_id, fname, ing, record, analysis, reliq) -> None:
        """Escribe Documento + Empleado + Contrato + Gaps + Liquidación, todo con el
        tenant_id forzado por TenantRepository. Sesión corta por contrato."""
        db = self._session_factory()
        try:
            repo = TenantRepository(db, ctx)
            documento = repo.add(dbm.Documento(
                doc_id=doc_id, filename=fname, tipo_doc="contrato",
                status=ing.status, confidence=ing.confidence, contenido=ing.text,
            ))
            empleado = repo.add(dbm.Empleado(
                nombre=str(record.empleado_nombre.value or ""),
                documento=_digits(record.empleado_documento.value or ""),
                cargo=str(record.role.value or ""),
            ))
            contrato = repo.add(dbm.Contrato(
                empleado_id=empleado.id, documento_id=documento.id,
                tipo_vinculo=str(record.vinculo_type.value or ""),
                salario_base=_money_int(record.base_salary),
                salario_variable=bool(record.salario_variable.value is True),
                auxilio_transporte=_money_int(record.auxilio_transporte),
                jornada_horas_semana=int(record.weekly_hours.value or 0),
                fecha_inicio=_date_or_none(record.start_date),
                fecha_fin=_date_or_none(record.end_date),
            ))
            for g in analysis["gaps"]:
                cit = g.get("citation") or {}
                repo.add(dbm.Gap(
                    contrato_id=contrato.id, tipo=g["gap_id"],
                    descripcion=g["issue"], severidad=g["severity"],
                    norma_ref=f"{cit.get('norm_id','')}:{cit.get('article','')}",
                    remedy_type=g.get("remedy_type", "otrosi"),
                ))
            if reliq > 0:
                repo.add(dbm.Liquidacion(
                    empleado_id=empleado.id, contrato_id=contrato.id,
                    total=int(reliq), es_correcta=False,
                ))
        finally:
            db.close()

    def history(self, ctx: TenantContext) -> dict:
        """Lee de la BD lo persistido para el tenant (prueba persistencia + aislamiento)."""
        db = self._session_factory()
        try:
            repo = TenantRepository(db, ctx)
            contratos = repo.list(dbm.Contrato)
            gaps = repo.list(dbm.Gap)
            empleados = {e.id: e for e in repo.list(dbm.Empleado)}
            return {
                "company_id": ctx.tenant_id,
                "total_contratos": len(contratos),
                "total_gaps": len(gaps),
                "contratos": [
                    {
                        "id": c.id,
                        "empleado": empleados.get(c.empleado_id).nombre if c.empleado_id in empleados else "",
                        "vinculo": c.tipo_vinculo,
                        "salario_base": c.salario_base,
                        "jornada": c.jornada_horas_semana,
                        "gaps": [g.tipo for g in gaps if g.contrato_id == c.id],
                    }
                    for c in contratos
                ],
            }
        finally:
            db.close()


def _contract_context(record, fila: dict | None = None) -> ContractContext | None:
    """Arma el ContractContext para las alertas M6 desde el DocumentRecord de M2 +
    la fila de nómina (mora SS). Solo si hay fecha de inicio válida (las alertas la
    requieren); si no, se omite de alertas (pero sus gaps SÍ entran al número mágico)."""
    start = record.start_date.value
    if not isinstance(start, str) or not start:
        return None
    vinculo = record.vinculo_type.value or "termino_indefinido"
    end = record.end_date.value if isinstance(record.end_date.value, str) else None

    mora_flag = False
    mora_amount = 0.0
    mora_due = None
    if fila is not None:
        mora_flag = str(fila.get("pago_ss_mora", "")).strip().lower() in ("true", "1", "si", "sí")
        mora_amount = _num(fila, "ss_monto_mora")
        mora_due = (fila.get("ss_due_date") or "").strip() or None

    return ContractContext(
        vinculo_type=vinculo,
        start_date=start,
        end_date=end,
        worker_id="***",
        pago_ss_mora=mora_flag,
        ss_amount_cop=mora_amount,
        ss_due_date=mora_due if mora_flag else None,
    )
