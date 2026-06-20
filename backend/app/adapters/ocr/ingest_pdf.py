"""
M1 — Adapter de ingesta. Portado de Hackathon-Due-Legal/src/ingest.py.

Degradación honesta (la garantía anti-alucinación de la ingesta):
  1. .txt / .docx          -> texto digital, confianza alta.
  2. .pdf con capa de texto -> 'digital' (minuta digital).
  3. .pdf escaneado         -> OCR (Tesseract spa) con su confianza -> 'ocr'.
  4. Ilegible / conf < umbral -> 'needs_human' (NUNCA inventa texto).

PyMuPDF y pytesseract son opcionales: si no están, los PDF/escaneos caen a
'needs_human' en vez de romper. El .txt y .docx siempre funcionan (sin deps).
"""
from __future__ import annotations

import io
import logging
import os
import shutil
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("cerebro.ingesta")

CONFIDENCE_THRESHOLD = 0.60
MIN_TEXTLAYER_CHARS = 200
OCR_DPI = 200
OCR_LANG = "spa"
SCAN_MARKER = "[[SCAN_ILEGIBLE]]"   # permite simular un escaneo ilegible en .txt de demo

# --- PyMuPDF (opcional) ---
try:
    import fitz  # type: ignore
    _HAS_FITZ = True
except Exception:  # pragma: no cover
    _HAS_FITZ = False

# --- OCR (opcional, autodetectado) ---
_TESS_CMD = os.environ.get("TESSERACT_CMD") or shutil.which("tesseract") or ""
try:
    import pytesseract  # type: ignore
    if _TESS_CMD and Path(_TESS_CMD).exists():
        pytesseract.pytesseract.tesseract_cmd = _TESS_CMD
    _HAS_OCR = bool(_TESS_CMD and Path(_TESS_CMD).exists())
except Exception:  # pragma: no cover
    _HAS_OCR = False


@dataclass(frozen=True)
class IngestResult:
    doc_id: str
    text: str
    confidence: float
    status: str   # digital | ocr | needs_human


def _finalize(doc_id: str, text: str, conf: float, scanned: bool) -> IngestResult:
    """Decide el status con la regla de degradación honesta."""
    if conf >= CONFIDENCE_THRESHOLD and text.strip():
        status = "ocr" if scanned else "digital"
        logger.info("[%s] -> %s (conf=%.3f, %d chars)", doc_id, status, conf, len(text))
        return IngestResult(doc_id, text, round(conf, 3), status)
    logger.warning("[%s] -> needs_human (conf=%.3f < %.2f o texto vacío; NO se inventa texto)",
                   doc_id, conf, CONFIDENCE_THRESHOLD)
    return IngestResult(doc_id, "", round(conf, 3), "needs_human")


def _ocr_pdf(doc) -> tuple[str, float]:
    """Renderiza cada página y la pasa por Tesseract. Devuelve (texto, confianza 0-1)."""
    page_texts: list[str] = []
    confs: list[float] = []
    matrix = fitz.Matrix(OCR_DPI / 72, OCR_DPI / 72)
    for page in doc:
        pix = page.get_pixmap(matrix=matrix)
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp.close()
        try:
            pix.save(tmp.name)
            data = pytesseract.image_to_data(tmp.name, lang=OCR_LANG,
                                              output_type=pytesseract.Output.DICT)
        finally:
            os.unlink(tmp.name)
        for w, c in zip(data["text"], data["conf"]):
            try:
                cf = float(c)
            except (TypeError, ValueError):
                cf = -1.0
            if w.strip() and cf >= 0:
                page_texts.append(w)
                confs.append(cf)
    text = " ".join(page_texts)
    conf = (sum(confs) / len(confs) / 100.0) if confs else 0.0
    return text, conf


def _ingest_pdf(doc_id: str, content: bytes) -> IngestResult:
    if not _HAS_FITZ:
        logger.warning("[%s] PyMuPDF (fitz) no instalado -> no se puede leer el PDF", doc_id)
        return _finalize(doc_id, "", 0.0, True)
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp.write(content)
    tmp.close()
    try:
        doc = fitz.open(tmp.name)
        if getattr(doc, "needs_pass", False):   # PDF protegido sin clave
            logger.warning("[%s] PDF protegido con contraseña -> needs_human", doc_id)
            doc.close()
            return _finalize(doc_id, "", 0.0, True)
        text = "\n".join(page.get_text() for page in doc)
        n = len(text.strip())
        logger.debug("[%s] %d páginas, %d chars en capa de texto (umbral digital=%d)",
                     doc_id, doc.page_count, n, MIN_TEXTLAYER_CHARS)
        if n >= MIN_TEXTLAYER_CHARS:
            doc.close()
            return _finalize(doc_id, text, 0.98, False)   # minuta digital
        if _HAS_OCR:
            logger.info("[%s] sin capa de texto suficiente -> intentando OCR (Tesseract spa)", doc_id)
            try:
                otext, oconf = _ocr_pdf(doc)
                logger.debug("[%s] OCR devolvió %d chars, conf media=%.3f", doc_id, len(otext), oconf)
            except Exception:
                logger.exception("[%s] OCR falló (excepción Tesseract/render)", doc_id)
                otext, oconf = "", 0.0
            doc.close()
            return _finalize(doc_id, otext, oconf, True)
        logger.warning("[%s] escaneo sin texto y Tesseract no instalado -> needs_human", doc_id)
        doc.close()
        return _finalize(doc_id, "", 0.0, True)
    except Exception:
        logger.exception("[%s] no se pudo abrir/leer el PDF (¿corrupto?) -> needs_human", doc_id)
        return _finalize(doc_id, "", 0.0, True)
    finally:
        os.unlink(tmp.name)


_DOCX_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _ingest_docx(doc_id: str, content: bytes) -> IngestResult:
    """.docx es un zip con XML; texto digital (conf 1.0). Corrupto -> needs_human."""
    tmp = tempfile.NamedTemporaryFile(suffix=".docx", delete=False)
    tmp.write(content)
    tmp.close()
    try:
        with zipfile.ZipFile(tmp.name) as z:
            root = ET.fromstring(z.read("word/document.xml"))
        paragraphs = ["".join(t.text for t in p.iter(f"{_DOCX_NS}t") if t.text)
                      for p in root.iter(f"{_DOCX_NS}p")]
        return _finalize(doc_id, "\n".join(paragraphs), 1.0, False)
    except Exception:
        logger.exception("[%s] .docx ilegible/corrupto -> needs_human", doc_id)
        return _finalize(doc_id, "", 0.0, False)
    finally:
        os.unlink(tmp.name)


def _ingest_xlsx(doc_id: str, content: bytes) -> IngestResult:
    """.xlsx → texto estructurado por hojas. Requiere openpyxl (opcional).
    Cada hoja se convierte en sección de texto con sus celdas separadas por tabulador.
    Útil para nóminas, RITs, contratos en tabla y matrices de personal."""
    try:
        import openpyxl  # type: ignore
        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        parts: list[str] = []
        for sheet in wb.worksheets:
            rows: list[str] = []
            for row in sheet.iter_rows(values_only=True):
                cells = [str(c).strip() for c in row if c is not None and str(c).strip()]
                if cells:
                    rows.append("\t".join(cells))
            if rows:
                parts.append(f"[Hoja: {sheet.title}]\n" + "\n".join(rows))
        wb.close()
        text = "\n\n".join(parts)
        return _finalize(doc_id, text, 1.0, False)
    except ImportError:
        logger.warning("[%s] openpyxl no instalado -> needs_human (pip install openpyxl)", doc_id)
        return _finalize(doc_id, "", 0.0, False)
    except Exception:
        logger.exception("[%s] .xlsx ilegible/corrupto -> needs_human", doc_id)
        return _finalize(doc_id, "", 0.0, False)


def ingest(doc_id: str, content: bytes, filename: str) -> IngestResult:
    """Punto de entrada del adapter. Despacha por extensión. Nunca inventa texto."""
    suffix = Path(filename).suffix.lower()
    logger.debug("[%s] ingesta de '%s' (%s, %d bytes)", doc_id, filename, suffix, len(content))
    if suffix == ".txt":
        text = content.decode("utf-8", errors="replace")
        if text.strip().upper().startswith(SCAN_MARKER):
            return _finalize(doc_id, "", 0.25, True)        # escaneo ilegible simulado
        return _finalize(doc_id, text, 1.0, False)
    if suffix == ".pdf":
        return _ingest_pdf(doc_id, content)
    if suffix in (".docx", ".docm"):
        return _ingest_docx(doc_id, content)
    if suffix in (".xlsx", ".xls"):
        return _ingest_xlsx(doc_id, content)
    raise ValueError(f"Formato no soportado: {suffix}")
