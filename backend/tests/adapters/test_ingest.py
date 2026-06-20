"""
Tests de M1 ingesta. Contrato: degradación honesta — nunca inventa texto.
Cubre los caminos sin dependencias pesadas (.txt y formato no soportado).
"""
import pytest

from app.adapters.ocr.ingest_pdf import ingest


def test_txt_digital_confianza_alta():
    res = ingest("c1", b"CONTRATO DE TRABAJO A TERMINO FIJO...", "contrato.txt")
    assert res.status == "digital"
    assert res.confidence == 1.0
    assert "CONTRATO" in res.text


def test_escaneo_ilegible_va_a_needs_human_sin_inventar_texto():
    res = ingest("c2", b"[[SCAN_ILEGIBLE]] basura ilegible", "escaneo.txt")
    assert res.status == "needs_human"
    assert res.text == ""               # NO inventa texto
    assert res.confidence < 0.60


def test_formato_no_soportado_lanza():
    with pytest.raises(ValueError):
        ingest("c3", b"...", "imagen.png")


def test_pdf_sin_pymupdf_o_ilegible_no_rompe():
    # Bytes que no son un PDF válido -> needs_human, nunca excepción al usuario.
    res = ingest("c4", b"no soy un pdf", "doc.pdf")
    assert res.status == "needs_human"
    assert res.text == ""
