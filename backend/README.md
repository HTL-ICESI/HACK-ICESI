# Cerebro Laboral HG — Backend

Backend del Reto 4 (ICESI 2026). FastAPI + Python 3.11. Arquitectura **hexagonal por capas**,
**multitenant**, con un **núcleo determinista puro** que es la garantía anti-alucinación.

## Por qué esta arquitectura (la historia para el jurado)

> El conocimiento jurídico vive en el **dominio puro** (`app/domain/`): funciones sin I/O,
> sin LLM, 100% testeables. El LLM y el OCR son **adapters** intercambiables que nunca
> deciden una cifra ni un veredicto. Cada número que sale del sistema lo calculó código
> determinista y trae su fuente citada.

Tres propiedades que el jurado pidió:

| Propiedad | Cómo se logra |
|---|---|
| **Confiabilidad** | El dominio (`domain/`) es puro y determinista. Tests unitarios prueban cada fórmula. El LLM solo redacta; el dominio valida antes de responder. Estados `needs_human` y `blocked` de primera clase. |
| **Multitenant** | Cada empresa cliente es un *tenant*. `TenantContext` se inyecta por dependencia y el `Repository` rechaza cualquier acceso sin `tenant_id`. Aislamiento en dos capas (dependencia + repositorio). |
| **Escalable / limpio** | Capas separadas: `api → services → domain ← adapters`. El dominio no conoce FastAPI ni Claude. Se puede cambiar OCR, LLM o storage sin tocar la lógica jurídica. |
| **Seguridad** | API key por firma, scoping de tenant forzado, datos PII del trabajador marcados y minimizados (Ley 1581). |
| **Rapidez** | Dominio puro es instantáneo; llamadas LLM/OCR async y cacheadas. |

## Capas

```
app/
  api/        ← HTTP (FastAPI routers + DTOs). No tiene lógica jurídica.
  services/   ← Casos de uso. Orquestan dominio + adapters. Impuro.
  domain/     ← NÚCLEO PURO. Derecho laboral como código determinista. Cero I/O.
  adapters/   ← Mundo externo: OCR, Claude, Whisper, storage. Intercambiables (ports).
  core/       ← Transversal: tenancy, security, audit, errores.
```

Regla de oro: **las dependencias apuntan hacia adentro.** `domain` no importa nada de `app`.

## Arrancar

```bash
cd cerebro-laboral-hg/backend
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # poner ANTHROPIC_API_KEY
uvicorn app.main:app --reload # -> http://127.0.0.1:8000/docs
pytest                        # corre el núcleo determinista
```

### OCR (para PDFs escaneados) — opcional pero recomendado
El motor de ingesta (M1) lee PDFs digitales y .docx sin nada extra. Para leer **escaneos**
(PDF-imagen) necesitas el binario Tesseract con español; nuestro adapter lo autodetecta:

```bash
# macOS
brew install tesseract tesseract-lang
tesseract --list-langs   # debe incluir 'spa'
```
Sin Tesseract, los escaneos caen a `needs_human` (degradación honesta, no rompe).

### Probar ingesta con documentos reales
```bash
python scripts/probar_ingesta.py /ruta/a/contrato.pdf   # un archivo o una carpeta
```

## Mapa de módulos → archivos

| Módulo | Dueño | Capa | Archivo |
|---|---|---|---|
| M1 Ingesta | Sara | adapter+service | `adapters/ocr/`, `services/ingest_service.py` |
| M2 Extractor con cita | Sara | service | `services/extraction_service.py` |
| M3 Cerebro/Corpus | Sara | domain+adapter | `domain/compliance/`, `adapters/corpus/` |
| M4 Liquidación | Sara | **domain puro** | `domain/liquidation/` |
| M5 Subsanación | Sara | service | `services/remediation_service.py` |
| M6 Exposición | Sara | **domain puro** | `domain/exposure/` |
| J3 Guardián (joya) | David | **domain puro** | `domain/disciplinary/guardian.py` |
| J2/J4 Descargos | David | service+adapter | `services/disciplinary_service.py`, `adapters/transcription/` |
```
```
