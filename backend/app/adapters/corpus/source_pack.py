"""
M3 (datos) — Corpus normativo. Carga el source-pack (CST, Ley 2101, Ley 2466, circulares
Mintrabajo) y resuelve cada cita a un nodo real. Patrón tomado de Due-Legal/data/sources.

El corpus es por-versión-de-año para soportar el cambio normativo (el "cerebro vivo").
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

CORPUS_PATH = Path(__file__).resolve().parents[3] / "data" / "corpus" / "source_pack.json"


@lru_cache
def load_corpus() -> dict:
    """Carga el source-pack. TODO(David): poblar con normas reales + radicados CSJ."""
    if not CORPUS_PATH.exists():
        return {"norms": {}, "_note": "TODO: poblar data/corpus/source_pack.json"}
    return json.loads(CORPUS_PATH.read_text(encoding="utf-8"))


def resolve(norm_id: str, article: str) -> dict | None:
    """Resuelve una cita a su nodo real. Sin nodo -> la cita no se afirma."""
    return load_corpus().get("norms", {}).get(f"{norm_id}:{article}")
