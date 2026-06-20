"""
Visualizador del pipeline por MÓDULO. Corre un documento por las etapas construidas
y muestra cada M en su propia sección: qué recibe y qué produce.

- M1 (ingesta): YA construido -> output REAL.
- M2 (extractor): se ejecuta si existe; si no, muestra PENDIENTE + la forma esperada.
- M3 (compliance): se ejecuta si existe (necesita el record de M2); si no, PENDIENTE.

Uso:
    cd cerebro-laboral-hg/backend && source .venv/bin/activate
    python scripts/pipeline.py /tmp/contratos-prueba/contrato_termino_fijo.pdf
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.tenancy import TenantContext              # noqa: E402
from app.core.audit import AuditLog                     # noqa: E402
from app.adapters.storage.repository import InMemoryRepository  # noqa: E402
from app.services.ingest_service import IngestService   # noqa: E402


def banner(m: str, titulo: str, estado: str) -> None:
    print("\n" + "━" * 72)
    print(f"  {m}  ·  {titulo}   [{estado}]")
    print("━" * 72)


def main() -> None:
    if len(sys.argv) < 2:
        print("Uso: python scripts/pipeline.py <archivo>")
        sys.exit(1)
    archivo = Path(sys.argv[1]).expanduser()
    if not archivo.exists():
        print(f"No existe: {archivo}")
        sys.exit(1)

    ctx = TenantContext(tenant_id="empresa-001")
    print(f"\n📂 Documento: {archivo.name}   ·   tenant: {ctx.tenant_id}")

    # ───────────────────────── M1 — INGESTA (REAL) ─────────────────────────
    banner("M1", "INGESTA", "✅ CONSTRUIDO")
    ingest_svc = IngestService(InMemoryRepository(), AuditLog())
    m1 = ingest_svc.ingest_document(ctx, archivo.stem, archivo.read_bytes(), archivo.name)
    print(f"  INPUT : archivo {archivo.suffix} ({archivo.stat().st_size} bytes)")
    print(f"  OUTPUT: status={m1.status}  confianza={m1.confidence}  chars={len(m1.text)}")
    print("  TEXTO EXTRAÍDO:")
    print("    " + m1.text.replace("\n", "\n    ").strip())

    # ──────────────────────── M2 — EXTRACTOR ────────────────────────
    record = None
    try:
        from app.services.extraction_service import ExtractionService  # type: ignore
    except ImportError:
        banner("M2", "EXTRACTOR CON CITA", "⏳ PENDIENTE")
        print("  INPUT : doc_id + text de M1  (arriba)")
        print("  OUTPUT esperado (DocumentRecord — ver contracts.json bloque M2):")
        print("    vinculo_type, base_salary, start_date, end_date, weekly_hours, role,")
        print("    employer  — cada campo con su 'source' (span en el texto).")
        print("  → Constrúyelo con TASKS/M2-extractor.md")
    else:
        banner("M2", "EXTRACTOR CON CITA", "✅ CONSTRUIDO")
        try:
            record = ExtractionService().extract(m1.doc_id, m1.text)  # type: ignore
            print("  INPUT : doc_id + text de M1")
            print("  OUTPUT (DocumentRecord):")
            print("    " + json.dumps(record, ensure_ascii=False, indent=2, default=str).replace("\n", "\n    "))
        except Exception as e:  # construido pero la interfaz no coincide con este runner
            print(f"  ⚠️ M2 existe pero la llamada falló: {type(e).__name__}: {e}")
            print("     Ajusta este runner a la interfaz real de ExtractionService.")

    # ──────────────────────── M3 — COMPLIANCE (GAPS) ────────────────────────
    if record is None:
        _m3_pendiente()
        return
    try:
        from app.services.compliance_service import ComplianceService  # type: ignore
    except ImportError:
        _m3_pendiente()
        return
    banner("M3", "DETECCIÓN DE GAPS", "✅ CONSTRUIDO")
    try:
        gaps = ComplianceService().analyze(record)  # type: ignore
        print("  OUTPUT (gaps):")
        print("    " + json.dumps(gaps, ensure_ascii=False, indent=2, default=str).replace("\n", "\n    "))
    except Exception as e:
        print(f"  ⚠️ M3 existe pero la llamada falló: {type(e).__name__}: {e}")
        print("     Ajusta este runner a la interfaz real de ComplianceService.")


def _m3_pendiente() -> None:
    banner("M3", "DETECCIÓN DE GAPS", "⏳ PENDIENTE (espera el record de M2)")
    print("  INPUT esperado : el DocumentRecord de M2")
    print("  OUTPUT esperado: lista de gaps con su cita. Ej. para jornada 48h:")
    print("    ⚠️ Jornada de 48h excede el máximo de 42h (Ley 2101/2021) -> otrosí")
    print("  → Constrúyelo con TASKS/M3-compliance.md")


if __name__ == "__main__":
    main()
