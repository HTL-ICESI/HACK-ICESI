"""
M2 — Núcleo determinista de extracción.

Lógica de extracción por **regex** para los campos de formato predecible (salario,
fechas, jornada). Puro: stdlib únicamente, sin I/O, sin LLM y sin importar nada de
`app/`. Cada extracción devuelve su `Span` (offset citado) o `None` si no aparece.

Regla anti-alucinación: lo que no se encuentra NO se inventa -> el orquestador lo
marca `not_found`. Ningún número se afirma sin span.
"""
from __future__ import annotations

from .regex_rules import (
    Span,
    Extraction,
    extract_vinculo_type,
    extract_employer,
    extract_role,
    extract_salary,
    extract_start_date,
    extract_end_date,
    extract_weekly_hours,
    extract_termination,
    extract_employee_name,
    extract_employee_doc,
    extract_auxilio_transporte,
    extract_salario_variable,
)

__all__ = [
    "Span",
    "Extraction",
    "extract_vinculo_type",
    "extract_employer",
    "extract_role",
    "extract_salary",
    "extract_start_date",
    "extract_end_date",
    "extract_weekly_hours",
    "extract_termination",
    "extract_employee_name",
    "extract_employee_doc",
    "extract_auxilio_transporte",
    "extract_salario_variable",
]
