"""Constantes normativas del proceso disciplinario laboral colombiano. Solo INSERT."""
from __future__ import annotations

NORMAS: dict[str, str] = {
    "CST_115":   "CST art. 115 — Procedimiento para sanciones disciplinarias",
    "CN_29":     "CN art. 29 — Debido proceso",
    "LEY_2466":  "Ley 2466 de 2025 — Reforma laboral (doble instancia disciplinaria)",
    "CIRC_0048": "Circular 0048 de 2026 — Reglamentación Ley 2466",
    "CST_62":    "CST art. 62 — Terminación con justa causa",
    "CST_113":   "CST art. 113 — Prohibición de multas y descuentos no pactados",
}

# Límite legal duro — NO modificar por config de cliente (CST art. 115 + Ley 2466/2025).
DIAS_HABILES_MINIMOS: int = 5
