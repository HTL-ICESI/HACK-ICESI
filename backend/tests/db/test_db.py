"""
Tests de la BD: el esquema se crea, se puede escribir/leer, y el aislamiento por
tenant se mantiene a nivel de base de datos (un tenant no ve filas de otro).
Usa una BD SQLite en memoria, aislada por test.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.tenancy import TenantContext, TenantViolation
from app.db.base import Base
from app.db import models as m
from app.db.repository import TenantRepository


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    db.add_all([m.Tenant(id="empresa-A", nombre="A"), m.Tenant(id="empresa-B", nombre="B")])
    db.commit()
    yield db
    db.close()


def test_esquema_se_crea_y_persiste(session):
    repo = TenantRepository(session, TenantContext(tenant_id="empresa-A"))
    emp = repo.add(m.Empleado(nombre="Juan Pérez", documento="123", cargo="Asesor"))
    assert emp.id is not None
    assert repo.get(m.Empleado, emp.id).nombre == "Juan Pérez"


def test_aislamiento_por_tenant_en_bd(session):
    repo_a = TenantRepository(session, TenantContext(tenant_id="empresa-A"))
    repo_b = TenantRepository(session, TenantContext(tenant_id="empresa-B"))
    emp = repo_a.add(m.Empleado(nombre="Confidencial A"))

    assert repo_a.get(m.Empleado, emp.id) is not None     # A sí lo ve
    assert repo_b.get(m.Empleado, emp.id) is None          # B NO lo ve
    assert repo_a.list(m.Empleado) and not repo_b.list(m.Empleado)


def test_add_fuerza_el_tenant_del_contexto(session):
    # Aunque el objeto traiga otro tenant_id, el repo lo sobreescribe con el del contexto.
    repo_a = TenantRepository(session, TenantContext(tenant_id="empresa-A"))
    emp = repo_a.add(m.Empleado(tenant_id="empresa-B", nombre="Intruso"))
    assert emp.tenant_id == "empresa-A"


def test_assert_owned_lanza_para_otro_tenant(session):
    repo_a = TenantRepository(session, TenantContext(tenant_id="empresa-A"))
    repo_b = TenantRepository(session, TenantContext(tenant_id="empresa-B"))
    emp = repo_a.add(m.Empleado(nombre="x"))
    with pytest.raises(TenantViolation):
        repo_b.assert_owned(m.Empleado, emp.id)
