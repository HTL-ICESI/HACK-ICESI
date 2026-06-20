"""
Modelos de dominio (Pydantic). Espejo de contracts.json. Keys en inglés (convención),
valores de dominio en español. Estos tipos NO conocen FastAPI ni el LLM.

Regla: ningún número que alimente una liquidación o el número mágico existe sin un
`Source` (span citado). Sin source -> el campo se marca, no se afirma.
"""
from __future__ import annotations

from enum import Enum
from pydantic import BaseModel


class FieldStatus(str, Enum):
    OK = "ok"
    NEEDS_HUMAN = "needs_human"
    NOT_FOUND = "not_found"


class Periodicity(str, Enum):
    MENSUAL = "mensual"
    QUINCENAL = "quincenal"
    ANUAL = "anual"
    UNICA = "unica"


class VinculoType(str, Enum):
    TERMINO_FIJO = "termino_fijo"
    TERMINO_INDEFINIDO = "termino_indefinido"
    OBRA_LABOR = "obra_labor"
    PRESTACION_SERVICIOS = "prestacion_servicios"


class Money(BaseModel):
    value: float            # en COP
    currency: str = "COP"
    periodicity: Periodicity = Periodicity.MENSUAL


class Source(BaseModel):
    """De dónde salió el dato: span en el documento + confianza."""
    span_start: int
    span_end: int
    text: str
    confidence: float
    doc_id: str


class Citation(BaseModel):
    """Fundamento normativo. `verified=False` => radicado por confirmar antes de citar en sala."""
    norm_id: str
    article: str
    title: str
    url: str
    verified: bool = False


class Field(BaseModel):
    """Valor extraído con su trazabilidad. El bloque de construcción anti-alucinación."""
    value: object | None = None
    source: Source | None = None
    status: FieldStatus = FieldStatus.OK


class DocumentRecord(BaseModel):
    """Salida del extractor (M2). Lo que consumen AMBOS motores. Cada campo con cita."""
    doc_id: str
    # ── Partes del contrato ──────────────────────────────────────────────────
    employer: Field           # empresa que contrata
    empleado_nombre: Field    # nombre completo del trabajador (con cita "Trabajador:")
    empleado_documento: Field # cédula como string normalizado (con cita "C.C.")
    role: Field               # cargo del trabajador
    # ── Condiciones económicas ───────────────────────────────────────────────
    vinculo_type: Field
    base_salary: Field        # salario básico mensual en COP
    auxilio_transporte: Field # None si no aplica (salario > 2 SMLMV)
    salario_variable: Field   # value=True si hay comisiones/HE; False si fijo
    # ── Temporalidad ────────────────────────────────────────────────────────
    start_date: Field
    end_date: Field
    weekly_hours: Field
    # ── Estado del vínculo ───────────────────────────────────────────────────
    # value=True+span → cláusula hallada. value=False → end_date existe sin cláusula
    # (zona gris, M3 chequea si ya venció). not_found → indefinido / sin end_date.
    termination_confirmed: Field = Field(
        value=None, source=None, status=FieldStatus.NOT_FOUND
    )
    # ── Datos operativos de nómina (M4/M5 los proveen, M2 no) ─────────────────
    # Field(value=True)  = mora comprobada en aportes de SS.
    # Field(value=False) = pagos al día (verificado).
    # None = sin datos de nómina disponibles → M3 no afirma el gap de mora (g5).
    pago_ss_mora: Field | None = None
