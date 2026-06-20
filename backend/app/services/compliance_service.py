"""
M3 service — orquesta: record -> detect_gaps -> resolver citas -> respuesta estructurada.

La capa de servicio NO contiene logica juridica. Solo coordina dominio + adaptadores.
Regla: sin nodo en corpus -> el gap no se emite (anti-alucinacion).
"""
from __future__ import annotations

from app.core.tenancy import TenantContext
from app.core.audit import AuditLog
from app.domain.models import DocumentRecord
from app.domain.compliance.gap_rules import detect_gaps
from app.adapters.corpus.source_pack import resolve


class ComplianceService:
    def __init__(self, audit: AuditLog) -> None:
        self._audit = audit

    def analyze(
        self,
        ctx: TenantContext,
        doc_id: str,
        record: DocumentRecord,
        doc_type: str,
    ) -> dict:
        """
        Analiza un DocumentRecord contra el corpus normativo.
        Devuelve la shape exacta del contrato M3.
        """
        raw_gaps = detect_gaps(record)
        gaps_out = []

        for gap in raw_gaps:
            node = resolve(gap.norm_id, gap.article)
            if node is None:
                # Sin nodo en corpus -> no se afirma el gap (regla de oro)
                continue

            citation = {
                "norm_id": node["norm_id"],
                "article": node["article"],
                "title": node["title"],
                "url": node["url"],
                "verified": node["verified"],
            }

            # Source: span del campo del record que disparo el gap
            source = None
            if gap.source_field:
                field_obj = getattr(record, gap.source_field, None)
                if field_obj is not None and field_obj.source is not None:
                    source = field_obj.source.model_dump()

            gaps_out.append({
                "gap_id": gap.gap_id,
                "issue": gap.issue,
                "severity": gap.severity,
                "citation": citation,
                "source": source,
                "remedy_type": gap.remedy_type,
            })

        applicable_norms = self._applicable_norms()

        self._audit.record(
            ctx,
            "compliance.analyze",
            doc_id,
            grounding=[g["citation"]["norm_id"] for g in gaps_out],
        )

        summary = self._compute_summary(gaps_out)

        return {
            "doc_id": doc_id,
            "gaps": gaps_out,
            "applicable_norms": applicable_norms,
            "summary": summary,
        }

    def _applicable_norms(self) -> list[dict]:
        """Normas de referencia del CST siempre presentes en cualquier analisis laboral."""
        keys = [("CST", "art. 64"), ("CST", "art. 65")]
        return [node for norm_id, article in keys if (node := resolve(norm_id, article))]

    def _compute_summary(self, gaps: list[dict]) -> dict:
        """
        Resumen ejecutivo del analisis. Alimenta el numero magico de M6
        y el semaforo del dashboard del frontend.
        risk_score: alta=3pts, media=2pts, baja=1pt (ponderado por severidad).
        """
        counts: dict[str, int] = {"alta": 0, "media": 0, "baja": 0}
        for g in gaps:
            counts[g["severity"]] = counts.get(g["severity"], 0) + 1
        score = counts["alta"] * 3 + counts["media"] * 2 + counts["baja"] * 1
        return {
            "total_gaps": len(gaps),
            "by_severity": counts,
            "risk_score": score,
            "has_blocking_issues": counts["alta"] > 0,
        }
