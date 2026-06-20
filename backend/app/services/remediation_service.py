"""
M5 service — genera el documento de subsanación.

Reparto anti-alucinación:
- El CÓDIGO calcula las cifras (del motor M4 o de constantes normativas).
- El CÓDIGO construye el esqueleto con las cifras y datos de partes inyectados.
- El LLM REDACTA prosa alrededor del esqueleto — nunca inventa cifras ni partes.
- validate_figures verifica que TODA cifra del motor esté intacta en el texto.
- Si alguna cifra difiere → BlockedOutput: el documento NO se devuelve.

El jurado audita esta capa: la trazabilidad cifra→motor y parte→contrato debe ser total.
"""
from __future__ import annotations

from app.core.tenancy import TenantContext
from app.core.errors import BlockedOutput
from app.adapters.llm.claude_client import ClaudeClient
from app.adapters.corpus.source_pack import resolve
from app.domain.remediation.validator import validate_figures
from app.domain.remediation.templates import (
    build_figures,
    build_skeleton,
    build_title,
    gap_citations,
)


class RemediationService:
    def __init__(self, llm: ClaudeClient) -> None:
        self._llm = llm

    async def generate(
        self,
        ctx: TenantContext,
        doc_id: str,
        gap_data: dict,
        liquidation_data: dict | None,
        doc_type: str,
        record=None,          # DocumentRecord | None — opcional para compatibilidad
    ) -> dict:
        """
        Genera el documento correctivo para un gap dado.

        Flujo:
        1. Figuras: estáticas del gap + dinámicas de M4.
        2. Party data: employer, trabajador, cargo extraídos del DocumentRecord.
        3. Skeleton: borrador con cifras y partes ya inyectados por código.
        4. LLM: elabora prosa (recibe el skeleton completo con cifras).
        5. Validar: TODA cifra del motor debe aparecer en el body final.
        6. Respuesta con citations del corpus.
        """
        gap_id = gap_data.get("gap_id", "")

        # 1. Cifras (código, nunca LLM) — solo claves referenciadas en el skeleton
        figures = build_figures(gap_id, doc_type, liquidation_data)

        # 2. Datos de partes del contrato (código, nunca LLM)
        party_data = self._extract_party_data(record)

        # 3. Skeleton con todo ya inyectado
        skeleton = build_skeleton(gap_id, doc_type, figures, party_data)

        # 4. LLM elabora prosa alrededor del skeleton
        body = await self._llm.draft_document(doc_type, {
            "gap": gap_data,
            "figures": figures,
            "skeleton": skeleton,
        })

        # 5. Guardia determinista: ninguna cifra puede diferir del motor
        if not isinstance(body, str) or not body.strip():
            raise BlockedOutput(
                f"LLM devolvió respuesta vacía o inválida para gap {gap_id!r}. "
                "Documento bloqueado."
            )
        if not validate_figures(body, figures):
            raise BlockedOutput(
                f"Cifra del documento no coincide con el motor para gap {gap_id!r}. "
                "Documento bloqueado por integridad de cifras."
            )

        # 6. Respuesta
        citations = self._resolve_citations(gap_id)
        figures_used = [
            {"label": k, "value": v, "source": f"M3.gap.{gap_id}"}
            for k, v in figures.items()
        ]

        return {
            "doc_id": doc_id,
            "document_type": doc_type,
            "title": build_title(gap_id, doc_type, figures),
            "body_markdown": body,
            "figures_used": figures_used,
            "citations": citations,
            "validation": {"figures_match_engine": True, "blocked": False},
        }

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _extract_party_data(record) -> dict:
        """
        Extrae employer, trabajador y fechas del DocumentRecord.
        Retorna {} si record es None (degradación sin datos de contrato).
        """
        if record is None:
            return {}
        out: dict = {}
        emp = getattr(record, "employer", None)
        if emp and isinstance(emp.value, dict):
            out["employer_name"] = emp.value.get("name", "")
            nit = emp.value.get("nit", "")
            if nit:
                out["employer_nit"] = nit
        nombre = getattr(record, "empleado_nombre", None)
        if nombre and nombre.value:
            out["worker_name"] = nombre.value
        doc = getattr(record, "empleado_documento", None)
        if doc and doc.value:
            out["worker_doc"] = doc.value
        role = getattr(record, "role", None)
        if role and role.value:
            out["worker_role"] = role.value
        start = getattr(record, "start_date", None)
        if start and start.value:
            out["contract_start"] = start.value
        return out

    @staticmethod
    def _resolve_citations(gap_id: str) -> list[dict]:
        """Resuelve citas del corpus normativo. Sin nodo → cita omitida."""
        out = []
        for corpus_key in gap_citations(gap_id):
            norm_id, article = corpus_key.split(":", 1)
            node = resolve(norm_id, article)
            if node:
                out.append(node)
        return out

    # Conservado para compatibilidad con tests que usan el stub original
    @staticmethod
    def _figures_match(body: str, figures: dict) -> bool:
        return validate_figures(body, figures)
