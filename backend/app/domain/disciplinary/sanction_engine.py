"""Motor de recomendación de sanciones. DETERMINISTA. Sin I/O, sin LLM.

El motor clasifica la falta y filtra las sanciones aplicables. El abogado
elige, modifica o rechaza — el motor nunca decide solo.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

FaltaLevel = Literal["leve", "grave", "gravisima"]
SanctionType = Literal["llamado_atencion", "suspension", "terminacion_justa_causa"]

# Sanciones válidas por nivel de falta (CST art. 115)
_ALLOWED_BY_LEVEL: dict[str, set[str]] = {
    "leve":      {"llamado_atencion"},
    "grave":     {"llamado_atencion", "suspension"},
    "gravisima": {"llamado_atencion", "suspension", "terminacion_justa_causa"},
}

# Sanciones PROHIBIDAS — nunca válidas (el sistema las bloquea con motivo)
_BLOCKED: dict[str, str] = {
    "multa":             "Multas económicas no autorizadas por el CST (art. 113)",
    "descuento_salarial": "Descuentos salariales no pactados están prohibidos (CST art. 113)",
    "rebaja_categoria":  "Degradación de categoría sin base normativa es sanción inválida",
    "suspension_salario": "Suspender el pago del salario es ilegal durante proceso disciplinario",
}

_LEGAL_BASIS: dict[str, dict] = {
    "llamado_atencion": {
        "norm_id": "CST", "article": "art. 115",
        "title": "Procedimiento disciplinario", "verified": True,
        "url": "https://www.secretariasenado.gov.co/cst-articulo-115",
    },
    "suspension": {
        "norm_id": "CST", "article": "art. 115",
        "title": "Suspensión — máx 8 días (60 días si reincidencia)", "verified": True,
        "url": "https://www.secretariasenado.gov.co/cst-articulo-115",
    },
    "terminacion_justa_causa": {
        "norm_id": "CST", "article": "art. 62",
        "title": "Terminación con justa causa", "verified": True,
        "url": "https://www.secretariasenado.gov.co/cst-articulo-62",
    },
}

# Días máximos de suspensión (CST art. 115)
_MAX_SUSPENSION_DAYS: dict[bool, int] = {False: 8, True: 60}


@dataclass
class SanctionRecommendation:
    recommended: SanctionType
    max_days: int | None
    is_reincidence: bool
    legal_basis: dict
    blocked_options: list[str]
    approved_by: str | None = None
    approved_at: datetime | None = None

    def to_dict(self) -> dict:
        return {
            "recommended": self.recommended,
            "max_days": self.max_days,
            "is_reincidence": self.is_reincidence,
            "legal_basis": self.legal_basis,
            "blocked_options": self.blocked_options,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
        }


def recommend(
    falta_level: FaltaLevel,
    is_reincidence: bool = False,
    requested_sanction: SanctionType | None = None,
) -> SanctionRecommendation:
    """Dado el nivel de falta, devuelve la sanción recomendada y las opciones bloqueadas.

    El abogado puede sobrescribir `recommended` siempre que la sanción esté en el
    conjunto permitido para ese nivel. Las opciones de `_BLOCKED` nunca están disponibles.
    """
    allowed = _ALLOWED_BY_LEVEL.get(falta_level, _ALLOWED_BY_LEVEL["leve"])

    # Opciones prohibidas con motivo de bloqueo
    blocked = [f"{s}: {r}" for s, r in _BLOCKED.items()]

    # Recomendación por defecto: la sanción más severa permitida para el nivel
    default_map: dict[str, SanctionType] = {
        "leve": "llamado_atencion",
        "grave": "suspension",
        "gravisima": "terminacion_justa_causa",
    }
    rec: SanctionType = default_map[falta_level]

    # Honrar la elección del abogado si está dentro de lo permitido
    if requested_sanction and requested_sanction in allowed:
        rec = requested_sanction

    max_days = _MAX_SUSPENSION_DAYS[is_reincidence] if rec == "suspension" else None

    return SanctionRecommendation(
        recommended=rec,
        max_days=max_days,
        is_reincidence=is_reincidence,
        legal_basis=_LEGAL_BASIS[rec],
        blocked_options=blocked,
    )
