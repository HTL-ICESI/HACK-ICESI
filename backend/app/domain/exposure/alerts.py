"""
M6 — Motor de alertas determinista. Calendarios de riesgo derivados de datos documentales.

Función pura: mismo set de contratos + reference_date → mismas alertas. Sin LLM, sin I/O.
Cada alerta tiene tipo, severidad, fecha límite y días restantes. El código decide, no el LLM.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ContractContext:
    """Contexto mínimo de un contrato para generación de alertas."""
    vinculo_type: str            # termino_fijo | termino_indefinido | obra_labor | prestacion_servicios
    start_date: str              # ISO "YYYY-MM-DD"
    end_date: str | None         # ISO, None si indefinido
    worker_id: str = "***"       # anonimizado por defecto
    pago_ss_mora: bool = False   # True = mora SS comprobada (datos operativos de nómina)
    ss_amount_cop: float = 0.0   # monto en mora (COP)
    ss_due_date: str | None = None   # fecha límite de pago SS en mora
    # Liquidación pendiente: trabajador con contrato terminado sin pago de prestaciones
    liquidacion_pendiente: bool = False   # True = liquidación no pagada tras terminación
    liquidacion_monto_cop: float = 0.0   # monto estimado de la liquidación (COP)
    liquidacion_dias_mora: int = 0       # días desde la terminación sin pago


@dataclass(frozen=True)
class Alert:
    alert_id: str
    type: str       # vencimiento_contrato | vacaciones_vencidas | seguridad_social_mora | liquidacion_pendiente
    severity: str   # alta | media | baja
    worker: str = "***"
    due_date: str | None = None
    days_left: int | None = None
    accrued_days: int | None = None           # solo vacaciones_vencidas
    amount: dict | None = None                # seguridad_social_mora / liquidacion_pendiente: {"value":…,"currency":"COP"}
    dias_mora: int | None = None              # solo liquidacion_pendiente: días sin pago

    def to_dict(self) -> dict:
        """Serializa excluyendo campos None para shape limpia en la respuesta HTTP."""
        return {k: v for k, v in dataclasses.asdict(self).items() if v is not None}


def _vencimiento_alert(
    alert_id: str,
    end_date_iso: str,
    ref: date,
    worker_id: str,
) -> Alert | None:
    """
    Alerta de vencimiento próximo (≤ 90 días restantes).
    - ≤ 30 días → alta
    - ≤ 90 días → media
    Fuera del umbral o ya vencido → None (lo cubre g4 de M3).
    """
    try:
        end_dt = date.fromisoformat(end_date_iso)
    except ValueError:
        return None
    days_left = (end_dt - ref).days
    if days_left < 0 or days_left > 90:
        return None
    severity = "alta" if days_left <= 30 else "media"
    return Alert(
        alert_id=alert_id,
        type="vencimiento_contrato",
        severity=severity,
        worker=worker_id,
        due_date=end_date_iso,
        days_left=days_left,
    )


def _vacaciones_alert(
    alert_id: str,
    start_date_iso: str,
    end_date_iso: str | None,
    ref: date,
    worker_id: str,
) -> Alert | None:
    """
    Alerta si la duración del vínculo supera 365 días sin evidencia de vacaciones (CST art. 186).
    accrued_days = días calendario totales trabajados.
    """
    try:
        start_dt = date.fromisoformat(start_date_iso)
        end_dt = date.fromisoformat(end_date_iso) if end_date_iso else ref
    except ValueError:
        return None
    accrued = (end_dt - start_dt).days
    if accrued <= 365:
        return None
    return Alert(
        alert_id=alert_id,
        type="vacaciones_vencidas",
        severity="media",
        worker=worker_id,
        accrued_days=accrued,
    )


def _ss_mora_alert(
    alert_id: str,
    amount_cop: float,
    due_date_iso: str,
    worker_id: str,
) -> Alert:
    """Alerta alta de mora SS comprobada — monto y fecha límite explícitos."""
    return Alert(
        alert_id=alert_id,
        type="seguridad_social_mora",
        severity="alta",
        worker=worker_id,
        due_date=due_date_iso,
        amount={"value": amount_cop, "currency": "COP"},
    )


def _liquidacion_alert(
    alert_id: str,
    monto_cop: float,
    dias_mora: int,
    worker_id: str,
) -> Alert:
    """
    Alerta de liquidación de prestaciones sociales no pagada tras terminación
    del contrato (CST art. 65: sanción moratoria por pago tardío).
    - días_mora > 30 → alta (riesgo de sanción moratoria a diario)
    - días_mora > 0  → media (recién vencido)
    """
    severity = "alta" if dias_mora > 30 else "media"
    return Alert(
        alert_id=alert_id,
        type="liquidacion_pendiente",
        severity=severity,
        worker=worker_id,
        amount={"value": monto_cop, "currency": "COP"} if monto_cop > 0 else None,
        dias_mora=dias_mora,
    )


def compute_alerts(
    contracts: list[ContractContext],
    *,
    reference_date: date | None = None,
) -> list[Alert]:
    """
    Aplica todos los generadores de alertas sobre un conjunto de contratos.
    Función pura: mismo input → mismas alertas, reproducible y auditable en sala.
    Sin I/O. Sin LLM.
    """
    ref = reference_date or date.today()
    alerts: list[Alert] = []
    counter = 1

    for ctx in contracts:
        # Alerta de vencimiento (solo término fijo con end_date)
        if ctx.vinculo_type == "termino_fijo" and ctx.end_date:
            alert = _vencimiento_alert(f"a{counter}", ctx.end_date, ref, ctx.worker_id)
            if alert:
                alerts.append(alert)
                counter += 1

        # Alerta de vacaciones acumuladas > 1 año
        vac = _vacaciones_alert(f"a{counter}", ctx.start_date, ctx.end_date, ref, ctx.worker_id)
        if vac:
            alerts.append(vac)
            counter += 1

        # Alerta de mora SS comprobada
        if ctx.pago_ss_mora and ctx.ss_due_date:
            alerts.append(_ss_mora_alert(f"a{counter}", ctx.ss_amount_cop, ctx.ss_due_date, ctx.worker_id))
            counter += 1

        # Alerta de liquidación pendiente (CST art. 65 — sanción moratoria)
        if ctx.liquidacion_pendiente:
            alerts.append(_liquidacion_alert(
                f"a{counter}", ctx.liquidacion_monto_cop, ctx.liquidacion_dias_mora, ctx.worker_id
            ))
            counter += 1

    return alerts
