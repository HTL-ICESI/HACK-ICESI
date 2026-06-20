"""
Tests del adaptador del corpus normativo (source_pack.py).

Verifica:
1. resolve() devuelve el nodo correcto o None.
2. El corpus cargado tiene la estructura esperada.
3. CANARY: todas las normas referenciadas en gap_rules existen en el corpus.
   Si este test falla, hay una regla que prometeria un gap sin respaldo normativo.
"""
from __future__ import annotations

from app.adapters.corpus.source_pack import resolve, load_corpus


# ── resolve() ────────────────────────────────────────────────────────────────

def test_resolve_norma_existente_devuelve_nodo():
    node = resolve("Ley 2101/2021", "art. 3")
    assert node is not None
    assert node["norm_id"] == "Ley 2101/2021"
    assert node["article"] == "art. 3"


def test_resolve_norma_inexistente_devuelve_none():
    assert resolve("Ley 9999/9999", "art. 99") is None


def test_resolve_norm_id_erroneo_devuelve_none():
    """Clave mal formada (solo norm_id sin article) -> None."""
    assert resolve("CST", "art. 999") is None


def test_resolve_nodo_tiene_todos_los_campos_citation():
    """Todo nodo del corpus debe tener los 5 campos de Citation."""
    node = resolve("CST", "art. 64")
    assert node is not None
    for campo in ("norm_id", "article", "title", "url", "verified"):
        assert campo in node, f"Campo '{campo}' ausente en el nodo CST art.64"
    assert isinstance(node["verified"], bool)


def test_resolve_cn_art29_esta_verificado():
    """CN art. 29 es la unica norma verificada=true en el corpus semilla."""
    node = resolve("CN", "art. 29")
    assert node is not None
    assert node["verified"] is True


# ── load_corpus() ─────────────────────────────────────────────────────────────

def test_corpus_tiene_clave_norms():
    corpus = load_corpus()
    assert "norms" in corpus
    assert isinstance(corpus["norms"], dict)


def test_corpus_version_year_2026():
    assert load_corpus().get("version_year") == 2026


def test_corpus_tiene_normas_de_todos_los_modulos():
    """Normas usadas por M3, M4, J3 deben estar presentes."""
    norms = load_corpus()["norms"]
    esperadas = [
        "CST:art. 249", "CST:art. 306", "CST:art. 186",
        "CST:art. 64",  "CST:art. 65",  "CST:art. 115",
        "CN:art. 29",
    ]
    for key in esperadas:
        assert key in norms, f"Norma {key} ausente del corpus"


# ── CANARY: integridad corpus ↔ gap_rules ─────────────────────────────────────

def test_canary_todas_las_normas_de_gap_rules_existen_en_corpus():
    """
    TEST CANARIO — Si falla, hay una regla en gap_rules.py que cita una
    norma que NO existe en el corpus. El gap se emitia sin respaldo → ALUCINACION.

    Actualizar este test cada vez que se agrega una nueva regla en gap_rules.py.
    """
    normas_en_gap_rules = [
        ("Ley 2101/2021", "art. 3"),   # g1 — jornada
        ("Ley 2466/2025", "art. 5"),   # g2 — reclasificacion
        ("CST",           "art. 186"), # g3 — vacaciones
        ("CST",           "art. 46"),  # g4 — vencimiento
        ("Ley 100/1993",  "art. 22"),  # g5 — seguridad social
    ]
    for norm_id, article in normas_en_gap_rules:
        node = resolve(norm_id, article)
        assert node is not None, (
            f"CANARIO ROTO: gap_rules.py referencia '{norm_id} {article}' "
            f"pero esa norma NO existe en source_pack.json. "
            f"Agregar el nodo al corpus antes de que esta regla llegue a produccion."
        )
