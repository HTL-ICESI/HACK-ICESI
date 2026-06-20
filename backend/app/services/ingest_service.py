"""
M1 service — orquesta el adapter de ingesta + persistencia tenant-scoped + audit.
El texto ingerido se guarda namespaced por tenant para que M2 (extractor) lo consuma.
"""
from __future__ import annotations

from app.core.tenancy import TenantContext
from app.core.audit import AuditLog
from app.adapters.ocr.ingest_pdf import ingest, IngestResult
from app.adapters.storage.repository import InMemoryRepository

COLLECTION = "documents"


class IngestService:
    def __init__(self, repo: InMemoryRepository, audit: AuditLog) -> None:
        self._repo = repo
        self._audit = audit

    def ingest_document(self, ctx: TenantContext, doc_id: str, content: bytes, filename: str) -> IngestResult:
        result = ingest(doc_id, content, filename)        # adapter: degradación honesta
        self._repo.put(ctx, COLLECTION, doc_id, result)   # aislado por tenant
        self._audit.record(ctx, "ingest", doc_id, grounding=[f"status={result.status}"])
        return result

    def get_text(self, ctx: TenantContext, doc_id: str) -> IngestResult | None:
        return self._repo.get(ctx, COLLECTION, doc_id)  # type: ignore[return-value]
