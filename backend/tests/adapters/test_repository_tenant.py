"""
Aislamiento multitenant (la afirmación de seguridad ante el jurado): un tenant NUNCA
puede leer datos de otro. Prueba la segunda capa de defensa (el repositorio).
"""
import pytest

from app.core.tenancy import TenantContext, TenantViolation
from app.adapters.storage.repository import InMemoryRepository

A = TenantContext(tenant_id="empresa-A")
B = TenantContext(tenant_id="empresa-B")


def test_un_tenant_no_ve_los_datos_de_otro():
    repo = InMemoryRepository()
    repo.put(A, "documents", "doc1", "CONTRATO CONFIDENCIAL DE EMPRESA A")

    assert repo.get(A, "documents", "doc1") == "CONTRATO CONFIDENCIAL DE EMPRESA A"
    assert repo.get(B, "documents", "doc1") is None          # B NO ve el doc de A


def test_assert_owned_bloquea_acceso_cruzado():
    repo = InMemoryRepository()
    repo.put(A, "documents", "doc1", "x")
    repo.assert_owned(A, "documents", "doc1")                 # A sí es dueño
    with pytest.raises(TenantViolation):
        repo.assert_owned(B, "documents", "doc1")            # B no -> excepción


def test_lista_esta_namespaced_por_tenant():
    repo = InMemoryRepository()
    repo.put(A, "documents", "d1", "a1")
    repo.put(B, "documents", "d2", "b1")
    assert repo.list(A, "documents") == ["a1"]
    assert repo.list(B, "documents") == ["b1"]


def test_operacion_sin_tenant_id_es_denegada():
    with pytest.raises(PermissionError):
        TenantContext(tenant_id="").require()
