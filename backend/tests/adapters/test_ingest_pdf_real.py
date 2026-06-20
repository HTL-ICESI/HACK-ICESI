"""
Tests de M1 con PDFs REALES (genera el PDF con PyMuPDF). Cubre el camino de PDF
digital (capa de texto) que los tests de .txt no ejercen. Se omiten si fitz no está.
"""
import pytest

fitz = pytest.importorskip("fitz")  # skip limpio si PyMuPDF no está instalado

from app.adapters.ocr.ingest_pdf import ingest


def _make_pdf(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), text, fontsize=11)
    data = doc.tobytes()
    doc.close()
    return data


def test_pdf_digital_con_capa_de_texto():
    pdf = _make_pdf("CONTRATO DE TRABAJO\nSalario mensual: 2.500.000\nJornada: 48 horas " * 5)
    res = ingest("c-pdf", pdf, "contrato.pdf")
    assert res.status == "digital"
    assert res.confidence >= 0.9
    assert "CONTRATO" in res.text and "2.500.000" in res.text


def test_pdf_sin_texto_sin_ocr_va_a_needs_human():
    doc = fitz.open(); doc.new_page(); empty = doc.tobytes(); doc.close()
    res = ingest("vacio", empty, "vacio.pdf")
    # Sin capa de texto y sin Tesseract -> needs_human, nunca inventa.
    assert res.status == "needs_human"
    assert res.text == ""
