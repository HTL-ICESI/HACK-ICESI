"""Excepciones de dominio + handlers. Mantienen el HTTP fuera del dominio."""
from __future__ import annotations


class DomainError(Exception):
    """Base de errores de negocio (no de infraestructura)."""


class NeedsHumanReview(DomainError):
    """El sistema prefiere no afirmar: confianza insuficiente. NO es un fallo."""


class BlockedOutput(DomainError):
    """Salida bloqueada: cifra no coincide con el motor, o nulidad pendiente."""
