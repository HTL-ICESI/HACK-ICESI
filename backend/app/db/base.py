"""
Motor de base de datos. UNA sola BD global (SQLite en demo, Postgres en prod) con
aislamiento por `tenant_id`. Cambiar de motor es cambiar DATABASE_URL — el ORM y el
resto del código no se tocan.
"""
from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Demo: archivo SQLite local. Prod: poner DATABASE_URL=postgresql://...
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./cerebro_laboral.db")

# check_same_thread solo aplica a SQLite (FastAPI usa varios hilos)
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base declarativa de todos los modelos ORM."""


def init_db() -> None:
    """Crea todas las tablas si no existen. Idempotente."""
    from app.db import models  # noqa: F401  (registra los modelos)
    Base.metadata.create_all(bind=engine)


def get_session():
    """Dependencia/contexto de sesión. Cierra siempre."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
