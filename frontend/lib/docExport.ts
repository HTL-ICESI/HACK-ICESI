/**
 * Exportación de documentos correctivos a Word (.doc) y PDF (vía impresión),
 * sin dependencias externas. Convierte el markdown de los esqueletos M5/J4
 * (encabezados, negritas, tablas, listas, citas) a HTML y lo empaqueta.
 */

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

/** Negritas **texto** -> <strong>. (El resto del inline se deja literal.) */
function inline(s: string): string {
  return escapeHtml(s).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
}

function isTableRow(line: string): boolean {
  return /^\s*\|.*\|\s*$/.test(line);
}
function isTableDivider(line: string): boolean {
  return /^\s*\|?[\s:|-]+\|?\s*$/.test(line) && line.includes("-");
}
function cells(line: string): string[] {
  return line.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
}

/** Markdown acotado (el que producen las plantillas) -> HTML. */
export function markdownToHtml(md: string): string {
  const lines = md.replace(/\r\n/g, "\n").split("\n");
  const out: string[] = [];
  let i = 0;
  let inList = false;
  const closeList = () => {
    if (inList) {
      out.push("</ul>");
      inList = false;
    }
  };

  while (i < lines.length) {
    const line = lines[i];

    // Tabla: fila de encabezado + divisor + filas
    if (isTableRow(line) && i + 1 < lines.length && isTableDivider(lines[i + 1])) {
      closeList();
      const header = cells(line);
      i += 2;
      const rows: string[][] = [];
      while (i < lines.length && isTableRow(lines[i])) {
        rows.push(cells(lines[i]));
        i++;
      }
      out.push("<table border='1' cellspacing='0' cellpadding='6' style='border-collapse:collapse;width:100%'>");
      out.push("<tr>" + header.map((h) => `<th align='left'>${inline(h)}</th>`).join("") + "</tr>");
      for (const r of rows) {
        out.push("<tr>" + r.map((c) => `<td>${inline(c)}</td>`).join("") + "</tr>");
      }
      out.push("</table>");
      continue;
    }

    const h = line.match(/^(#{1,4})\s+(.*)$/);
    if (h) {
      closeList();
      const level = h[1].length; // # -> h1 (título), ## -> h2, ### -> h3
      out.push(`<h${level}>${inline(h[2])}</h${level}>`);
      i++;
      continue;
    }

    if (/^\s*>\s?/.test(line)) {
      closeList();
      out.push(`<blockquote style='border-left:3px solid #999;margin:0;padding-left:12px;color:#444'>${inline(line.replace(/^\s*>\s?/, ""))}</blockquote>`);
      i++;
      continue;
    }

    if (/^\s*[-*]\s+/.test(line)) {
      if (!inList) {
        out.push("<ul>");
        inList = true;
      }
      out.push(`<li>${inline(line.replace(/^\s*[-*]\s+/, ""))}</li>`);
      i++;
      continue;
    }

    if (/^\s*-{3,}\s*$/.test(line)) {
      closeList();
      out.push("<hr/>");
      i++;
      continue;
    }

    if (line.trim() === "") {
      closeList();
      i++;
      continue;
    }

    closeList();
    out.push(`<p>${inline(line)}</p>`);
    i++;
  }
  closeList();
  return out.join("\n");
}

function slugify(s: string): string {
  return s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "").slice(0, 60) || "documento";
}

const PRINT_CSS =
  // Fuerza tema CLARO: sin esto, el PDF hereda el dark mode del navegador y sale negro.
  ":root{color-scheme:light}" +
  "html,body{background:#ffffff!important;color:#1a1a2e!important}" +
  "body{font-family:Georgia,'Times New Roman',serif;max-width:720px;margin:32px auto;line-height:1.6;padding:0 24px}" +
  "h1{font-family:Arial,sans-serif;color:#11113a;font-size:20px;text-align:center;letter-spacing:.3px;margin:0 0 18px;border-bottom:2px solid #801817;padding-bottom:10px}" +
  "h2,h3,h4{font-family:Arial,sans-serif;color:#11113a;margin-top:18px}" +
  "p{margin:.6em 0}" +
  "strong{color:#11113a}" +
  "table{margin:14px 0;width:100%;border-collapse:collapse}" +
  "th,td{border:1px solid #cfcabf;padding:7px 10px;text-align:left;vertical-align:top}" +
  "th{background:#f3f1ef}" +
  "blockquote{font-style:italic;border-left:3px solid #801817;margin:12px 0;padding:4px 14px;color:#33302c;background:#faf8f6}" +
  "hr{border:none;border-top:1px solid #ccc;margin:18px 0}" +
  "ul,ol{margin:.5em 0 .5em 1.2em}";

/**
 * Descarga el borrador como .docx (Word XML en HTML-in-Word, compatible con
 * Microsoft Word ≥2007 y Google Docs). Es el formato de mayor compatibilidad
 * sin dependencias externas. La extensión .docx hace que Word lo reconozca
 * directamente; internamente es MHTML con namespace Word.
 */
export function downloadAsWord(title: string, markdown: string): void {
  const html =
    `<html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>` +
    `<head><meta charset='utf-8'><title>${escapeHtml(title)}</title><style>${PRINT_CSS}</style></head>` +
    `<body>${markdownToHtml(markdown)}</body></html>`;
  const blob = new Blob(["﻿", html], { type: "application/msword" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${slugify(title)}.docx`;
  a.click();
  URL.revokeObjectURL(url);
}

/** Abre una ventana de impresión con el documento → el usuario guarda como PDF. */
export function downloadAsPdf(title: string, markdown: string): void {
  const win = window.open("", "_blank", "width=800,height=900");
  if (!win) return;
  win.document.write(
    `<html><head><meta charset='utf-8'><title>${escapeHtml(title)}</title><style>${PRINT_CSS}` +
    `@media print{@page{margin:18mm}}</style></head><body>${markdownToHtml(markdown)}` +
    `<script>window.onload=function(){setTimeout(function(){window.print();},250);}<\/script></body></html>`,
  );
  win.document.close();
}
