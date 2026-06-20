"""
El dashboard (exposición) sobrevive a un reinicio del backend: el agregado por
empresa se persiste en BD y un store NUEVO (memoria vacía) lo rehidrata — en vez de
caer al dataset demo.
"""
from app.db.base import init_db, SessionLocal
from app.db import models as dbm
from app.domain.exposure.alerts import ContractContext
from app.services.company_service import CompanyAnalysisStore
from app.services.exposure_service import ExposureRequest

init_db()

TENANT = "empresa-test-exposure"


def _clean():
    with SessionLocal() as db:
        row = db.get(dbm.ExposureSnapshot, TENANT)
        if row:
            db.delete(row)
            db.commit()


def test_exposicion_sobrevive_reinicio():
    _clean()
    req = ExposureRequest(
        company_id=TENANT, workers_at_risk=4, detected_reliquidations=5_694_000.0,
        total_clauses=30, outdated_clauses=7,
        contracts=[ContractContext(vinculo_type="termino_fijo",
                                   start_date="2025-01-01", end_date="2026-07-03",
                                   worker_id="***", pago_ss_mora=True,
                                   ss_amount_cop=480_000.0)],
    )
    CompanyAnalysisStore().put(TENANT, req)        # backend "vivo"

    fresh = CompanyAnalysisStore()                 # "reinicio": memoria vacía
    got = fresh.get(TENANT)
    assert got is not None
    assert got.workers_at_risk == 4
    assert got.detected_reliquidations == 5_694_000.0
    assert len(got.contracts) == 1 and got.contracts[0].pago_ss_mora is True
    _clean()


def test_sin_analisis_no_hay_exposicion():
    _clean()
    assert CompanyAnalysisStore().get(TENANT) is None
