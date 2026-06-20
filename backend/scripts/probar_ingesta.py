"""
Debugger de M1: prueba la ingesta con documentos REALES y muestra TODO — diagnóstico
de motores, logs paso a paso, el texto extraído completo, y el traceback si algo falla.

Uso:
    cd cerebro-laboral-hg/backend
    source .venv/bin/activate
    python scripts/probar_ingesta.py /ruta/a/tu/contrato.pdf
    python scripts/probar_ingesta.py /ruta/a/carpeta/          # procesa todos
    python scripts/probar_ingesta.py contrato.pdf --full       # imprime TODO el texto

Qué verás:
  - Estado de los motores (PyMuPDF, Tesseract, idiomas).
  - Logs DEBUG del adapter: cuántos chars de capa de texto, si entró al OCR, confianza, etc.
  - El JSON tal como lo devuelve POST /api/ingest.
  - Si un archivo falla: el traceback completo (no se traga el error).
"""
from __future__ import annotations

import json
import logging
import shutil
import sys
import time
import traceback
from pathlib import Path

# Permite ejecutar desde la raíz del backend sin instalar el paquete
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# --- Logging VERBOSO: muestra todo lo que registra el adapter ---
logging.basicConfig(
    level=logging.DEBUG,
    format="  %(levelname)-7s %(name)s | %(message)s",
)

from app.adapters.ocr import ingest_pdf as M  # noqa: E402

SUPPORTED = (".txt", ".pdf", ".docx", ".docm")


def diagnostico() -> None:
    print("=" * 72)
    print("DIAGNÓSTICO DE MOTORES")
    print("=" * 72)
    print(f"  PyMuPDF (PDF)     : {'✅ OK' if M._HAS_FITZ else '❌ NO instalado'}")
    tess = shutil.which('tesseract')
    print(f"  Tesseract (OCR)   : {'✅ OK' if M._HAS_OCR else '❌ NO instalado'}"
          + (f'  [{tess}]' if tess else ''))
    if M._HAS_OCR:
        import subprocess
        try:
            langs = subprocess.run(['tesseract', '--list-langs'], capture_output=True, text=True)
            tiene_spa = 'spa' in langs.stdout
            print(f"  Idioma español    : {'✅ spa disponible' if tiene_spa else '❌ falta spa'}")
        except Exception:
            print("  Idioma español    : ? (no se pudo consultar)")
    print(f"  Umbral confianza  : {M.CONFIDENCE_THRESHOLD}")
    print(f"  Umbral 'digital'  : {M.MIN_TEXTLAYER_CHARS} chars de capa de texto")
    print()


def probar_archivo(path: Path, full: bool) -> None:
    print("=" * 72)
    print(f"📄 ARCHIVO: {path.name}  ({path.stat().st_size} bytes)")
    print("-" * 72)
    t0 = time.perf_counter()
    try:
        content = path.read_bytes()
        print("  [logs del adapter]")
        res = M.ingest(path.stem, content, path.name)
    except Exception:
        print("\n  ❌ FALLÓ con excepción (traceback completo):\n")
        traceback.print_exc()
        return
    ms = (time.perf_counter() - t0) * 1000

    icono = {"digital": "✅", "ocr": "✅", "needs_human": "⚠️"}.get(res.status, "❓")
    print()
    print(f"  RESULTADO {icono}")
    print(f"    status     : {res.status}")
    print(f"    confianza  : {res.confidence}")
    print(f"    caracteres : {len(res.text)}")
    print(f"    tiempo     : {ms:.0f} ms")
    print()
    print("  TEXTO EXTRAÍDO:")
    texto = res.text if full else res.text[:500]
    print("    " + (texto.replace("\n", "\n    ") if texto else "(vacío)"))
    if not full and len(res.text) > 500:
        print(f"    … (+{len(res.text) - 500} chars; usa --full para ver todo)")
    print()
    print("  JSON que recibe el frontend (POST /api/ingest):")
    payload = {"doc_id": res.doc_id, "status": res.status,
               "confidence": res.confidence, "text_len": len(res.text)}
    print("    " + json.dumps(payload, ensure_ascii=False))
    print()


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    full = "--full" in sys.argv

    diagnostico()

    if not args:
        print("Uso: python scripts/probar_ingesta.py <archivo-o-carpeta> [--full]")
        sys.exit(1)

    target = Path(args[0]).expanduser()
    if not target.exists():
        print(f"❌ No existe: {target}")
        sys.exit(1)

    if target.is_dir():
        archivos = sorted(p for p in target.iterdir() if p.suffix.lower() in SUPPORTED)
        if not archivos:
            print(f"No hay archivos soportados ({', '.join(SUPPORTED)}) en {target}")
            return
        print(f"Procesando {len(archivos)} archivo(s) de {target}\n")
        for p in archivos:
            probar_archivo(p, full)
    else:
        probar_archivo(target, full)


if __name__ == "__main__":
    main()
