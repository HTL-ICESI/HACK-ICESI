"""
M3 (datos) — Corpus normativo. Resuelve cada cita a un nodo real.

Fuente primaria: el CORPUS VERIFICADO (David) en data/corpus/verified/normas/*.json
— cada norma con texto literal, vigencia, fuente oficial y `texto_verificado`. Si
una norma no está ahí, cae al source_pack.json semilla (marcado `verified: false`),
para no romper reglas cuya norma aún no se curó (p.ej. Ley 100/1993).

El identificador de las reglas (gap_rules) se normaliza a la convención de David:
  "Ley 2101/2021" + "art. 2"  →  clave "L2101/2021:2"
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_DATA = Path(__file__).resolve().parents[3] / "data" / "corpus"
CORPUS_PATH = _DATA / "source_pack.json"                 # seed (fallback)
VERIFIED_DIR = _DATA / "verified" / "normas"             # corpus verificado de David

# Convención del motor (gap_rules) → norma_id del corpus de David.
_NORM_ID_MAP = {
    "CST": "CST",
    # CN (debido proceso art. 29) se deja al seed verificado; no se mapea a CP.
    "Ley 2101/2021": "L2101/2021",
    "Ley 2466/2025": "L2466/2025",
    "Ley 100/1993": "L100/1993",
    "Ley 52/1975": "L52/1975",
}


def _art_num(article: str) -> str:
    """'art. 186' → '186'  ·  'art 24' → '24'  ·  '186' → '186'."""
    return (article or "").replace("art.", "").replace("art ", "").strip()


def _key(norm_id: str, article: str) -> str:
    return f"{_NORM_ID_MAP.get(norm_id, norm_id)}:{_art_num(article)}"


@lru_cache
def load_corpus() -> dict:
    """Seed (fallback) — title/url/verified por cita."""
    if not CORPUS_PATH.exists():
        return {"norms": {}}
    return json.loads(CORPUS_PATH.read_text(encoding="utf-8"))


@lru_cache
def load_verified() -> dict:
    """Índice del corpus verificado de David: 'norma_id:articulo' → nodo enriquecido."""
    index: dict[str, dict] = {}
    if not VERIFIED_DIR.exists():
        return index
    for fp in sorted(VERIFIED_DIR.glob("*.json")):
        try:
            records = json.loads(fp.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for r in records:
            nid = r.get("norma_id")
            art = r.get("articulo")
            if not nid or art in (None, ""):
                continue
            index[f"{nid}:{_art_num(str(art))}"] = r
    return index


def resolve(norm_id: str, article: str) -> dict | None:
    """Resuelve una cita a su nodo. Prioriza el corpus verificado de David; si no
    está, cae al seed. Sin nodo en ninguno -> la cita no se afirma (regla de oro)."""
    key = _key(norm_id, article)
    node = load_verified().get(key)
    if node is not None:
        return {
            "norm_id": norm_id,
            "article": article,
            "title": node.get("epigrafe") or node.get("norma") or "",
            "url": node.get("fuente_url") or node.get("url") or "",
            "verified": bool(node.get("texto_verificado")),
            "texto_literal": node.get("texto_literal") or "",
            "vigencia": node.get("vigencia") or "",
            "fuente": node.get("fuente") or "",
            "fecha_consulta": node.get("fecha_consulta") or "",
        }
    # Fallback: seed semilla (sin verificar)
    seed = load_corpus().get("norms", {}).get(f"{norm_id}:{article}")
    return seed
