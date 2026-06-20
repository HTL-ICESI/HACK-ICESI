"""
Test de OCR real: genera un PDF 'escaneado' (imagen sin capa de texto) y verifica
que Tesseract (spa) lo lee -> status='ocr'. Se omite si PyMuPDF o Tesseract no están.
"""
import pytest

fitz = pytest.importorskip("fitz")

from app.adapters.ocr.ingest_pdf import ingest, _HAS_OCR

pytestmark = pytest.mark.skipif(not _HAS_OCR, reason="Tesseract no instalado")


def _make_scanned_pdf(text: str) -> bytes:
    """Rasteriza texto a imagen y lo mete en un PDF -> escaneo sin capa de texto."""
    src = fitz.open(); page = src.new_page()
    page.insert_text((50, 100), text, fontsize=16)
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
    src.close()
    scan = fitz.open(); spage = scan.new_page(width=pix.width, height=pix.height)
    spage.insert_image(spage.rect, pixmap=pix)
    data = scan.tobytes(); scan.close()
    return data


def test_pdf_escaneado_se_lee_por_ocr():
    pdf = _make_scanned_pdf("CONTRATO DE TRABAJO\nSalario mensual: 2.500.000\nJornada: 48 horas")
    res = ingest("scan", pdf, "contrato_escaneado.pdf")
    assert res.status == "ocr"
    assert res.confidence >= 0.60
    assert "CONTRATO" in res.text.upper()
