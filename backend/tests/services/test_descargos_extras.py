"""
J1 extras: WhatsApp de evidencia (Twilio) + contraste descargo↔cargos.

Sin red: el cliente de WhatsApp se inyecta como stub y el LLM como stub, para
verificar la degradación honesta y la forma de salida (no la API real).
"""
import pytest

from app.core.audit import AuditLog
from app.core.tenancy import TenantContext
from app.adapters.llm.claude_client import ClaudeClient
from app.services.disciplinary_service import (
    DisciplinaryService,
    _build_evidence_message,
)

A_CTX = TenantContext(tenant_id="empresa-A")


class _WAUnconfigured:
    def configured(self) -> bool:
        return False

    def send(self, *a, **k):  # pragma: no cover - no debe llamarse
        raise AssertionError("no debe enviarse sin credenciales")


class _WASent:
    def configured(self) -> bool:
        return True

    def send(self, to, *, body=None, media_urls=None):
        return {"sid": "SM123", "status": "queued", "to": to}


def _svc(whatsapp=None):
    return DisciplinaryService(ClaudeClient(), AuditLog(), whatsapp=whatsapp)


def test_build_evidence_message_incluye_citacion_y_pruebas():
    msg = _build_evidence_message(
        company_name="Empresa SAS", worker_name="Juan Ospino",
        charges_summary="Ausencias los días 3, 4 y 5.",
        evidence_names=["registro.pdf", "reporte.pdf"],
        call_date="24 de junio de 2026", call_time="10:00 a.m.",
        response_deadline="cinco (5) días hábiles",
    )
    assert "Juan Ospino" in msg
    assert "registro.pdf" in msg and "reporte.pdf" in msg
    assert "24 de junio de 2026" in msg and "10:00 a.m." in msg
    assert "art. 115" in msg and "art. 29" in msg  # debido proceso citado


def test_whatsapp_sin_credenciales_devuelve_preview():
    out = _svc(_WAUnconfigured()).send_evidence_whatsapp(
        A_CTX, to_number="3001234567", worker_name="Ana",
        company_name="Empresa SAS", charges_summary="Falta grave.",
        evidence_names=["a.pdf"], call_date="24 jun",
    )
    assert out["sent"] is False and out["preview"] is True
    assert out["to"] == "+573001234567"
    assert out["body"]


def test_whatsapp_numero_invalido_no_envia():
    out = _svc(_WASent()).send_evidence_whatsapp(
        A_CTX, to_number="", worker_name="Ana",
        company_name="Empresa SAS", charges_summary="x",
    )
    assert out["sent"] is False and "error" in out


def test_whatsapp_configurado_envia():
    out = _svc(_WASent()).send_evidence_whatsapp(
        A_CTX, to_number="3001234567", worker_name="Ana",
        company_name="Empresa SAS", charges_summary="x", evidence_names=["a.pdf"],
    )
    assert out["sent"] is True and out["sid"] == "SM123"


class _LLMStub(ClaudeClient):
    async def analyze_descargo(self, charges_summary, evidence_summary, descargo_text):
        return {"responde": True, "cobertura": "parcial",
                "puntos_respondidos": ["ausencia día 3"],
                "puntos_sin_responder": ["días 4 y 5"],
                "contradice_evidencia": False,
                "resumen": "Justifica solo una de las ausencias.",
                "evaluado_por": "llm"}


async def test_contrast_descargo_devuelve_estructura():
    svc = DisciplinaryService(_LLMStub(), AuditLog())
    out = await svc.contrast_descargo(
        A_CTX, charges_summary="Ausencias 3, 4 y 5",
        evidence_summary="registro", descargo_text="Estuve incapacitado el día 3.",
    )
    assert out["cobertura"] == "parcial" and out["responde"] is True
    assert "días 4 y 5" in out["puntos_sin_responder"]
