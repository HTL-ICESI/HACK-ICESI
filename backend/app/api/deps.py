"""
Dependencias FastAPI: inyectan TenantContext + servicios. Wiring central de la app.
"""
from __future__ import annotations

from app.core.audit import AuditLog
from app.adapters.llm.claude_client import ClaudeClient
from app.adapters.storage.repository import repository
from app.services.ingest_service import IngestService
from app.services.extraction_service import ExtractionService
from app.services.liquidation_service import LiquidationService
from app.services.remediation_service import RemediationService
from app.services.disciplinary_service import DisciplinaryService
from app.services.pipeline_service import PipelineService
from app.services.compliance_service import ComplianceService
from app.services.exposure_service import ExposureService
from app.services.company_service import CompanyService, CompanyAnalysisStore
from app.services.batch_service import BatchService

# Singletons de proceso (en prod -> contenedor DI por request)
audit_log = AuditLog()
_claude = ClaudeClient()

ingest_service = IngestService(repository, audit_log)
extraction_service = ExtractionService(repository, audit_log, _claude)
liquidation_service = LiquidationService(audit_log)
remediation_service = RemediationService(_claude)
disciplinary_service = DisciplinaryService(_claude, audit_log)
pipeline_service = PipelineService(disciplinary_service, audit_log)
compliance_service = ComplianceService(audit_log)
exposure_service = ExposureService(audit_log)

# Store del orquestador (Bloque 2 -> BD). Compartido entre /company y /dashboard.
company_store = CompanyAnalysisStore()
company_service = CompanyService(
    ingest_service, extraction_service, compliance_service,
    exposure_service, company_store, audit_log,
)

# Batch (procesamiento masivo) — reusa los servicios ya probados y alimenta el
# mismo company_store que lee el dashboard de Inicio.
batch_service = BatchService(
    ingest_service, extraction_service, compliance_service,
    liquidation_service, remediation_service, audit_log,
    company_store, exposure_service,
)


def get_ingest_service() -> IngestService:
    return ingest_service


def get_extraction_service() -> ExtractionService:
    return extraction_service


def get_liquidation_service() -> LiquidationService:
    return liquidation_service


def get_disciplinary_service() -> DisciplinaryService:
    return disciplinary_service


def get_compliance_service() -> ComplianceService:
    return compliance_service


def get_exposure_service() -> ExposureService:
    return exposure_service


def get_remediation_service() -> RemediationService:
    return remediation_service


def get_pipeline_service() -> PipelineService:
    return pipeline_service


def get_company_service() -> CompanyService:
    return company_service


def get_company_store() -> CompanyAnalysisStore:
    return company_store


def get_batch_service() -> BatchService:
    return batch_service
