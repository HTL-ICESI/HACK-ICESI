"""Máquina de estados del proceso disciplinario. PURO. Sin I/O, sin LLM.

Todas las transiciones son deterministas: dado el estado actual + condiciones → resultado reproducible.
Los retrocesos siempre están permitidos si hay motivo escrito (audit trail).
"""
from __future__ import annotations

from datetime import date, timedelta
from enum import Enum


class ProcessState(str, Enum):
    EVIDENCIAS_PENDIENTES  = "EVIDENCIAS_PENDIENTES"
    LISTO_PARA_CITAR       = "LISTO_PARA_CITAR"
    CITADO                 = "CITADO"
    DILIGENCIA_REALIZADA   = "DILIGENCIA_REALIZADA"
    EN_REVISION            = "EN_REVISION"
    DECISION_EMITIDA       = "DECISION_EMITIDA"
    RECURSO                = "RECURSO"
    CERRADO                = "CERRADO"


_FORWARD_ORDER = [
    ProcessState.EVIDENCIAS_PENDIENTES,
    ProcessState.LISTO_PARA_CITAR,
    ProcessState.CITADO,
    ProcessState.DILIGENCIA_REALIZADA,
    ProcessState.EN_REVISION,
    ProcessState.DECISION_EMITIDA,
    ProcessState.RECURSO,
    ProcessState.CERRADO,
]


class TransitionError(Exception):
    """Transición de estado inválida — motivo en el mensaje."""


def working_days_between(start: date, end: date) -> int:
    """Cuenta días hábiles (lun-vie) entre start y end, ambos inclusive."""
    if end < start:
        return 0
    days = 0
    current = start
    while current <= end:
        if current.weekday() < 5:
            days += 1
        current += timedelta(days=1)
    return days


def validate_transition(
    current_state: ProcessState,
    new_state: ProcessState,
    *,
    # EVIDENCIAS_PENDIENTES → LISTO_PARA_CITAR
    checklist_complete: bool = False,
    # LISTO_PARA_CITAR → CITADO
    has_notification_proof: bool = False,
    # CITADO → DILIGENCIA_REALIZADA
    citation_date: date | None = None,
    session_date: date | None = None,
    min_notice_days: int = 5,
    # DILIGENCIA_REALIZADA → EN_REVISION
    acta_attendees_registered: bool = False,
    acta_signed_valid: bool = False,
    # EN_REVISION → DECISION_EMITIDA
    guardian_can_proceed: bool = False,
    lawyer_decision_registered: bool = False,
    # Override para cualquier bloqueo de plazo (requiere motivo escrito)
    override_reason: str | None = None,
) -> None:
    """Valida la transición. Lanza TransitionError si no está permitida.

    Retrocesos: siempre permitidos con override_reason (proceso puede corregirse).
    Saltos de estado: nunca permitidos.
    """
    try:
        curr_idx = _FORWARD_ORDER.index(current_state)
        new_idx = _FORWARD_ORDER.index(new_state)
    except ValueError as exc:
        raise TransitionError(f"Estado desconocido: {exc}") from exc

    if new_idx == curr_idx:
        raise TransitionError(f"El proceso ya está en estado {current_state.value}.")

    # Retroceso — siempre permitido con motivo
    if new_idx < curr_idx:
        if not override_reason:
            raise TransitionError(
                f"Retroceder de {current_state.value} → {new_state.value} "
                f"requiere motivo escrito (override_reason)."
            )
        return

    # No se permiten saltos de estado
    if new_idx > curr_idx + 1:
        raise TransitionError(
            f"No se puede saltar de {current_state.value} a {new_state.value}. "
            f"Estado intermedio requerido: {_FORWARD_ORDER[curr_idx + 1].value}."
        )

    # Reglas por transición específica
    if (current_state == ProcessState.EVIDENCIAS_PENDIENTES
            and new_state == ProcessState.LISTO_PARA_CITAR):
        if not checklist_complete:
            raise TransitionError(
                "El checklist pre-cita tiene ítems incompletos. "
                "Todos deben ser True antes de emitir la citación."
            )

    elif (current_state == ProcessState.LISTO_PARA_CITAR
            and new_state == ProcessState.CITADO):
        if not has_notification_proof:
            raise TransitionError(
                "Se requiere comprobante de entrega de la citación "
                "(acuse de recibo email/WhatsApp Business/constancia física)."
            )

    elif (current_state == ProcessState.CITADO
            and new_state == ProcessState.DILIGENCIA_REALIZADA):
        if citation_date and session_date:
            days = working_days_between(citation_date, session_date)
            if days < min_notice_days:
                if not override_reason:
                    raise TransitionError(
                        f"Solo han transcurrido {days} días hábiles desde la citación. "
                        f"Mínimo legal: {min_notice_days} (CST art. 115 + Ley 2466/2025). "
                        f"Para hacer override provea override_reason con el motivo escrito."
                    )

    elif (current_state == ProcessState.DILIGENCIA_REALIZADA
            and new_state == ProcessState.EN_REVISION):
        if not acta_attendees_registered:
            raise TransitionError(
                "El acta debe registrar la lista de asistentes antes de pasar a revisión."
            )
        if not acta_signed_valid:
            raise TransitionError(
                "El acta debe estar firmada por el instructor + trabajador, "
                "o registrar negativa del trabajador con al menos 2 testigos."
            )

    elif (current_state == ProcessState.EN_REVISION
            and new_state == ProcessState.DECISION_EMITIDA):
        if not guardian_can_proceed:
            raise TransitionError(
                "El Guardián (J3) indica que el proceso NO puede proceder. "
                "Resuelva los vicios de debido proceso antes de emitir la decisión."
            )
        if not lawyer_decision_registered:
            raise TransitionError(
                "El abogado debe registrar y firmar la decisión antes de emitirla."
            )

    # DECISION_EMITIDA → RECURSO, DECISION_EMITIDA/RECURSO → CERRADO:
    # sin condiciones bloqueantes en la máquina de estados (validaciones adicionales en service).
