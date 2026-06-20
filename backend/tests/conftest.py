"""
Configuración global de la suite.

Los tests corren SIEMPRE offline y deterministas: nunca pegan al LLM real
(TotalGPT/Anthropic), aunque exista un .env con una API key. Las pruebas de
extracción validan la shape del contrato y los campos DUROS (regex); los campos
blandos quedan en not_found sin red. El LLM real se prueba aparte con los
scripts E2E (scripts/e2e_*.py), no en la suite.
"""
import os

# Anular cualquier key del entorno/.env ANTES de que se construya Settings.
os.environ["INFERMATIC_API_KEY"] = ""
os.environ["ANTHROPIC_API_KEY"] = ""
# BD de test AISLADA (no toca cerebro_laboral.db real). Debe fijarse antes de
# importar app.db.base, que crea el engine al importarse.
os.environ["DATABASE_URL"] = "sqlite:///./test_cerebro.db"
# Dos tenants para probar aislamiento multitenant.
os.environ["API_KEYS"] = "demo-hg-key:empresa-001,demo-key-2:empresa-002"

from app.config import get_settings  # noqa: E402

# Si algo ya cacheó settings con la key, invalidar el cache.
get_settings.cache_clear()

import pytest  # noqa: E402
from app.api.deps import company_store, batch_service  # noqa: E402
from app.db.base import init_db, SessionLocal  # noqa: E402
from app.db import models as _models  # noqa: E402

init_db()


def _clear_singletons() -> None:
    """Limpia el estado en memoria de los singletons (sobreviven entre tests)."""
    company_store.clear()
    batch_service._batches.clear()
    batch_service._last_by_tenant.clear()


@pytest.fixture(autouse=True)
def _reset_state():
    """Aísla cada test: limpia los singletons en memoria y las tablas de la BD de test."""
    _clear_singletons()
    db = SessionLocal()
    try:
        for table in reversed(_models.Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.commit()
    finally:
        db.close()
    yield
    _clear_singletons()
