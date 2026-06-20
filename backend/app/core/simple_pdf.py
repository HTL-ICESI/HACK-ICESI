"""
Generador de PDF mínimo SIN dependencias (PDF es un formato de texto).

Suficiente para documentos legales de una a varias páginas: texto plano con
saltos de línea, fuente Helvetica, paginación automática. No pretende ser un
motor completo — solo producir un PDF válido que Twilio pueda adjuntar y que
WhatsApp muestre como documento descargable.
"""
from __future__ import annotations

import re

_PAGE_W, _PAGE_H = 612, 792          # Carta (puntos)
_MARGIN = 54
_LEADING = 15
_FONT_SIZE = 11
_MAX_CHARS = 92                       # ancho aprox. a Helvetica 11pt


def _strip_md(text: str) -> list[str]:
    """Markdown → líneas de texto plano (quita #, *, _, ` y viñetas)."""
    out: list[str] = []
    for raw in text.replace("\r\n", "\n").split("\n"):
        line = raw.rstrip()
        line = re.sub(r"^#{1,6}\s*", "", line)          # encabezados
        line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)    # negrita
        line = re.sub(r"\*(.+?)\*", r"\1", line)        # itálica
        line = re.sub(r"`(.+?)`", r"\1", line)          # code
        line = re.sub(r"^\s*[-*]\s+", "•  ", line)      # viñetas
        out.append(line)
    return out


def _wrap(lines: list[str]) -> list[str]:
    """Envuelve líneas largas a _MAX_CHARS, conservando líneas en blanco."""
    wrapped: list[str] = []
    for line in lines:
        if not line:
            wrapped.append("")
            continue
        words = line.split(" ")
        cur = ""
        for w in words:
            if len(cur) + len(w) + 1 <= _MAX_CHARS:
                cur = f"{cur} {w}".strip()
            else:
                if cur:
                    wrapped.append(cur)
                cur = w
        wrapped.append(cur)
    return wrapped


def _esc(s: str) -> bytes:
    """Escapa y codifica en Windows-1252 (lo que Helvetica/WinAnsiEncoding espera).
    Los caracteres fuera de ese set (p.ej. emoji) se reemplazan, no rompen el PDF."""
    s = s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return s.encode("cp1252", errors="replace")


def markdown_to_pdf(title: str, body_markdown: str) -> bytes:
    """Devuelve los bytes de un PDF con el título + el cuerpo del documento."""
    lines = _wrap([title, ""] + _strip_md(body_markdown))
    usable_h = _PAGE_H - 2 * _MARGIN
    per_page = int(usable_h // _LEADING)
    pages = [lines[i:i + per_page] for i in range(0, len(lines), per_page)] or [[""]]

    # Construye los objetos del PDF.
    objs: list[bytes] = []

    def add(obj: bytes) -> int:
        objs.append(obj)
        return len(objs)  # número de objeto (1-based)

    font_obj = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
                   b"/Encoding /WinAnsiEncoding >>")
    page_obj_ids: list[int] = []
    content_obj_ids: list[int] = []

    # Reservamos el id del Pages (lo conocemos: será el siguiente tras fuente).
    # Para mantenerlo simple, primero creamos contenidos y páginas, luego Pages y Catalog.
    for pg in pages:
        y = _PAGE_H - _MARGIN
        parts = [b"BT", f"/F1 {_FONT_SIZE} Tf".encode(), f"{_LEADING} TL".encode(),
                 f"{_MARGIN} {y} Td".encode()]
        first = True
        for ln in pg:
            if first:
                parts.append(b"(" + _esc(ln) + b") Tj")
                first = False
            else:
                parts.append(b"T* (" + _esc(ln) + b") Tj")
        parts.append(b"ET")
        stream = b"\n".join(parts)
        cid = add(b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream))
        content_obj_ids.append(cid)

    pages_obj_id = len(objs) + len(pages) + 1  # se conocerá; lo fijamos abajo
    # Crear los objetos Page (referencian Pages y su contenido).
    for cid in content_obj_ids:
        pid = add(
            b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 %d %d] "
            b"/Resources << /Font << /F1 %d 0 R >> >> /Contents %d 0 R >>"
            % (pages_obj_id, _PAGE_W, _PAGE_H, font_obj, cid)
        )
        page_obj_ids.append(pid)

    kids = b" ".join(b"%d 0 R" % pid for pid in page_obj_ids)
    pages_id = add(b"<< /Type /Pages /Count %d /Kids [%s] >>" % (len(page_obj_ids), kids))
    # pages_obj_id que usamos arriba debe coincidir:
    assert pages_id == pages_obj_id, (pages_id, pages_obj_id)
    catalog_id = add(b"<< /Type /Catalog /Pages %d 0 R >>" % pages_id)

    # Ensamblar el archivo con tabla xref.
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objs, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + obj + b"\nendobj\n"
    xref_pos = len(out)
    n = len(objs) + 1
    out += b"xref\n0 %d\n" % n
    out += b"0000000000 65535 f \n"
    for off in offsets[1:]:
        out += b"%010d 00000 n \n" % off
    out += b"trailer\n<< /Size %d /Root %d 0 R >>\n" % (n, catalog_id)
    out += b"startxref\n%d\n%%%%EOF" % xref_pos
    return bytes(out)
