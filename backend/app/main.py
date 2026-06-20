"""
App factory de FastAPI. Registra routers, CORS (para el front de Juanes) y handlers
de errores de dominio. La lógica jurídica NO vive aquí.
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.errors import NeedsHumanReview, BlockedOutput
from app.core.tenancy import TenantViolation
from app.api.routers import (
    ingest, extraction, liquidation, disciplinary, compliance, dashboard, remediation, company,
    batch, workers, media,
)


def create_app() -> FastAPI:
    app = FastAPI(title="Cerebro Laboral HG", version="0.1.0")

    # Crea las tablas de la BD si no existen (idempotente).
    from app.db.base import init_db
    init_db()

    app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
    )

    app.include_router(ingest.router)
    app.include_router(extraction.router)
    app.include_router(liquidation.router)
    app.include_router(disciplinary.router)
    app.include_router(compliance.router)
    app.include_router(dashboard.router)
    app.include_router(remediation.router)
    app.include_router(company.router)
    app.include_router(batch.router)
    app.include_router(workers.router)
    app.include_router(media.router)

    @app.exception_handler(NeedsHumanReview)
    async def _needs_human(_: Request, exc: NeedsHumanReview):
        return JSONResponse(status_code=200, content={"status": "needs_human", "detail": str(exc)})

    @app.exception_handler(BlockedOutput)
    async def _blocked(_: Request, exc: BlockedOutput):
        return JSONResponse(status_code=409, content={"blocked": True, "detail": str(exc)})

    @app.exception_handler(TenantViolation)
    async def _tenant(_: Request, exc: TenantViolation):
        return JSONResponse(status_code=403, content={"detail": "Acceso entre tenants denegado."})

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()
