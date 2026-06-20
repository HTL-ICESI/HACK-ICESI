"""
Tests del motor de alertas M6 (alerts.py). Función pura — mismo input → mismas alertas.
REF fija para que los tests no dependan de date.today().
"""
from datetime import date, timedelta

import pytest

from app.domain.exposure.alerts import ContractContext, Alert, compute_alerts

REF = date(2026, 6, 18)


# ── Alerta vencimiento_contrato ───────────────────────────────────────────────

def test_termino_fijo_14_dias_genera_alerta_alta():
    ctx = ContractContext(
        vinculo_type="termino_fijo",
        start_date="2025-07-01",
        end_date=(REF + timedelta(days=14)).isoformat(),
    )
    alerts = compute_alerts([ctx], reference_date=REF)
    a = next((a for a in alerts if a.type == "vencimiento_contrato"), None)
    assert a is not None
    assert a.severity == "alta"
    assert a.days_left == 14
    assert a.due_date == (REF + timedelta(days=14)).isoformat()


def test_termino_fijo_30_dias_exactos_es_alta():
    """Límite exacto de 30 días → alta."""
    ctx = ContractContext(
        vinculo_type="termino_fijo",
        start_date="2025-01-01",
        end_date=(REF + timedelta(days=30)).isoformat(),
    )
    alerts = compute_alerts([ctx], reference_date=REF)
    a = next((a for a in alerts if a.type == "vencimiento_contrato"), None)
    assert a is not None
    assert a.severity == "alta"


def test_termino_fijo_45_dias_genera_alerta_media():
    ctx = ContractContext(
        vinculo_type="termino_fijo",
        start_date="2025-01-01",
        end_date=(REF + timedelta(days=45)).isoformat(),
    )
    alerts = compute_alerts([ctx], reference_date=REF)
    a = next((a for a in alerts if a.type == "vencimiento_contrato"), None)
    assert a is not None
    assert a.severity == "media"


def test_termino_fijo_91_dias_no_genera_alerta_vencimiento():
    """Fuera del umbral de 90 días → no hay alerta."""
    ctx = ContractContext(
        vinculo_type="termino_fijo",
        start_date="2025-01-01",
        end_date=(REF + timedelta(days=91)).isoformat(),
    )
    alerts = compute_alerts([ctx], reference_date=REF)
    assert all(a.type != "vencimiento_contrato" for a in alerts)


def test_termino_indefinido_con_end_date_no_genera_vencimiento():
    """Solo termino_fijo genera alerta de vencimiento."""
    ctx = ContractContext(
        vinculo_type="termino_indefinido",
        start_date="2025-01-01",
        end_date=(REF + timedelta(days=14)).isoformat(),
    )
    alerts = compute_alerts([ctx], reference_date=REF)
    assert all(a.type != "vencimiento_contrato" for a in alerts)


def test_termino_fijo_ya_vencido_no_genera_alerta_vencimiento():
    """Ya vencido (days_left < 0) → M3 g4 lo cubre; aquí no se duplica."""
    ctx = ContractContext(
        vinculo_type="termino_fijo",
        start_date="2024-01-01",
        end_date="2025-01-01",
    )
    alerts = compute_alerts([ctx], reference_date=REF)
    assert all(a.type != "vencimiento_contrato" for a in alerts)


# ── Alerta vacaciones_vencidas ────────────────────────────────────────────────

def test_vacaciones_400_dias_genera_alerta_media():
    ctx = ContractContext(
        vinculo_type="termino_indefinido",
        start_date=(REF - timedelta(days=400)).isoformat(),
        end_date=None,
    )
    alerts = compute_alerts([ctx], reference_date=REF)
    a = next((a for a in alerts if a.type == "vacaciones_vencidas"), None)
    assert a is not None
    assert a.severity == "media"
    assert a.accrued_days == 400


def test_vacaciones_exacto_365_dias_no_genera_alerta():
    """365 días exactos no supera el umbral (> 365)."""
    ctx = ContractContext(
        vinculo_type="termino_indefinido",
        start_date=(REF - timedelta(days=365)).isoformat(),
        end_date=None,
    )
    alerts = compute_alerts([ctx], reference_date=REF)
    assert all(a.type != "vacaciones_vencidas" for a in alerts)


def test_vacaciones_con_end_date_pasado_usa_end_date():
    """Contrato cerrado: accrued = end_date - start_date."""
    ctx = ContractContext(
        vinculo_type="termino_fijo",
        start_date="2024-01-01",
        end_date="2025-06-01",   # 517 días desde start
    )
    alerts = compute_alerts([ctx], reference_date=REF)
    a = next((a for a in alerts if a.type == "vacaciones_vencidas"), None)
    assert a is not None
    assert a.accrued_days == (date(2025, 6, 1) - date(2024, 1, 1)).days


# ── Alerta seguridad_social_mora ──────────────────────────────────────────────

def test_ss_mora_true_genera_alerta_alta_con_monto():
    ctx = ContractContext(
        vinculo_type="termino_indefinido",
        start_date="2025-01-01",
        end_date=None,
        pago_ss_mora=True,
        ss_amount_cop=480_000.0,
        ss_due_date="2026-06-23",
    )
    alerts = compute_alerts([ctx], reference_date=REF)
    a = next((a for a in alerts if a.type == "seguridad_social_mora"), None)
    assert a is not None
    assert a.severity == "alta"
    assert a.amount == {"value": 480_000.0, "currency": "COP"}
    assert a.due_date == "2026-06-23"


def test_ss_mora_false_no_genera_alerta():
    ctx = ContractContext(
        vinculo_type="termino_indefinido",
        start_date="2025-01-01",
        end_date=None,
        pago_ss_mora=False,
        ss_amount_cop=480_000.0,
        ss_due_date="2026-06-23",
    )
    alerts = compute_alerts([ctx], reference_date=REF)
    assert all(a.type != "seguridad_social_mora" for a in alerts)


def test_ss_mora_true_sin_due_date_no_genera_alerta():
    """Mora comprobada pero sin fecha límite → no se emite (dato incompleto)."""
    ctx = ContractContext(
        vinculo_type="termino_indefinido",
        start_date="2025-01-01",
        end_date=None,
        pago_ss_mora=True,
        ss_amount_cop=480_000.0,
        ss_due_date=None,
    )
    alerts = compute_alerts([ctx], reference_date=REF)
    assert all(a.type != "seguridad_social_mora" for a in alerts)


# ── Determinismo + estructura ────────────────────────────────────────────────

def test_determinismo_mismo_input_mismo_output():
    ctx = ContractContext(
        vinculo_type="termino_fijo",
        start_date="2025-01-01",
        end_date=(REF + timedelta(days=14)).isoformat(),
        pago_ss_mora=True,
        ss_amount_cop=500_000,
        ss_due_date="2026-06-25",
    )
    a = compute_alerts([ctx], reference_date=REF)
    b = compute_alerts([ctx], reference_date=REF)
    assert a == b


def test_alert_ids_son_secuenciales_sin_gaps():
    """Los IDs son a1, a2, a3... sin saltos aunque vengan de contratos distintos."""
    contracts = [
        ContractContext(
            vinculo_type="termino_fijo",
            start_date="2025-01-01",
            end_date=(REF + timedelta(days=14)).isoformat(),
        ),
        ContractContext(
            vinculo_type="termino_indefinido",
            start_date=(REF - timedelta(days=400)).isoformat(),
            end_date=None,
        ),
        ContractContext(
            vinculo_type="termino_indefinido",
            start_date="2025-01-01",
            end_date=None,
            pago_ss_mora=True,
            ss_amount_cop=480_000,
            ss_due_date="2026-06-25",
        ),
    ]
    alerts = compute_alerts(contracts, reference_date=REF)
    for i, a in enumerate(alerts, 1):
        assert a.alert_id == f"a{i}"


def test_sin_contratos_retorna_lista_vacia():
    assert compute_alerts([], reference_date=REF) == []


def test_to_dict_excluye_campos_none():
    """La serialización de Alert omite campos None para shape HTTP limpia."""
    a = Alert(alert_id="a1", type="vencimiento_contrato", severity="alta",
               worker="***", due_date="2026-07-01", days_left=13)
    d = a.to_dict()
    assert "accrued_days" not in d
    assert "amount" not in d
    assert d["days_left"] == 13
