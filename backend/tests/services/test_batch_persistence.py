"""
Persistencia del lote de compliance: el lote sobrevive a un reinicio del backend.

Se simula el reinicio creando una instancia NUEVA de BatchService (memoria vacía):
debe rehidratar el lote desde la BD (status / latest / result).
"""
from app.core.audit import AuditLog
from app.core.tenancy import TenantContext
from app.db.base import init_db, SessionLocal
from app.db.models import BatchSnapshot
from app.services.batch_service import BatchService

init_db()

TENANT = "empresa-test-persist"


def _svc() -> BatchService:
    # status/latest/result/_persist/_rehydrate no usan los sub-servicios.
    return BatchService(None, None, None, None, None, AuditLog(), None, None)  # type: ignore[arg-type]


def _sample_batch() -> dict:
    return {
        "tenant_id": TENANT, "total": 1, "completed": 1, "order": ["d0"],
        "results": {
            "d0": {
                "doc_id": "d0", "filename": "contrato.pdf", "status": "done",
                "summary": {
                    "worker_name": "Ana Pérez", "employer_name": "X SAS",
                    "risk_level": "alto", "risk_score": 3, "total_exposure": 1000,
                    "gap_count": 1,
                    "gaps": [{"gap_id": "g3", "issue": "x", "severity": "alta",
                              "remedy_type": "otrosi"}],
                },
                "full": {"doc_id": "d0", "filename": "contrato.pdf", "text": "…",
                         "extract": {}, "compliance": {}, "liquidation": {},
                         "remediation": None},
            }
        },
    }


def _clean():
    with SessionLocal() as db:
        db.query(BatchSnapshot).filter_by(tenant_id=TENANT).delete()
        db.commit()


def test_lote_sobrevive_reinicio_del_backend():
    _clean()
    ctx = TenantContext(tenant_id=TENANT)

    # 1) Backend "vivo": procesa y persiste el lote.
    s1 = _svc()
    s1._batches["bx"] = _sample_batch()
    s1._last_by_tenant[TENANT] = "bx"
    s1._persist("bx")

    # 2) "Reinicio": instancia nueva, sin memoria. Debe rehidratar de la BD.
    s2 = _svc()
    st = s2.status(ctx, "bx")
    assert st is not None and st["completed"] == 1
    assert st["results"][0]["summary"]["worker_name"] == "Ana Pérez"

    latest = s2.latest(ctx)
    assert latest is not None and latest["batch_id"] == "bx"

    full = s2.result(ctx, "bx", "d0")
    assert full is not None and full["filename"] == "contrato.pdf"

    _clean()


def test_aislamiento_por_tenant_en_rehidratacion():
    _clean()
    s1 = _svc()
    s1._batches["bx"] = _sample_batch()
    s1._persist("bx")

    # Otro tenant no puede rehidratar el lote ajeno.
    other = _svc()
    assert other.status(TenantContext(tenant_id="otro-tenant"), "bx") is None

    _clean()
