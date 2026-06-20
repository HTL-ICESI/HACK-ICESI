"""
M5 — Plantillas de documentos correctivos por tipo de gap.

Responsabilidades de esta capa (dominio puro):
- `build_figures`: devuelve las cifras estáticas conocidas para cada gap_id,
  más las cifras dinámicas de M4 (si la liquidación fue provista).
- `build_skeleton`: construye el borrador con las cifras y datos de las partes
  ya inyectados. El LLM recibe este borrador y SOLO elabora prosa adicional.
- `build_title`: título del documento por tipo.
- `gap_citations`: claves de corpus normativo para cada gap_id.

Regla: las cifras van en el skeleton ANTES de llamar al LLM. validate_figures
verifica que el LLM no las haya eliminado ni alterado.

# ADR-M5-001 — Inyección de datos de partes en el documento
Fecha: 2026-06-18
Decisión: `build_skeleton` recibe `party_data` (employer, trabajador, etc.)
extraído del DocumentRecord antes de llamar al LLM.
Razón: sin estos datos el documento producido es genérico — no identifica a
las partes firmantes y no puede usarse como instrumento legal real. Un otrosí
colombiano debe tener: identificación de partes, referencia al contrato original
y bloque de firmas. Los skeletons ahora incluyen encabezado de partes y pie de
firmas interpolados desde `party_data`.
Impacto: `generate()` en RemediationService recibe `record: DocumentRecord | None`;
el router acepta `record` como campo opcional en el request body.
Autor: Sara (instancia M5) — revisado en prueba gold case José Ospino.
"""
from __future__ import annotations

import re

from app.domain.liquidation.constants import JORNADA_MAX_2026

# ────────────────────────────────────────────────────────────────────────────
# Figuras estáticas por gap_id (conocidas por el código, no por el LLM)
# ────────────────────────────────────────────────────────────────────────────
_STATIC_FIGURES: dict[str, dict] = {
    "g1": {"jornada_nueva": JORNADA_MAX_2026},   # 42 — constante normativa
    "g2": {},
    "g3": {},
    "g4": {},
    "g5": {},
}

# ────────────────────────────────────────────────────────────────────────────
# Citas por gap_id — claves del corpus en formato {norm_id}:{article}
# ────────────────────────────────────────────────────────────────────────────
_CITATION_KEYS: dict[str, list[str]] = {
    "g1": ["Ley 2101/2021:art. 3"],
    "g2": ["Ley 2466/2025:art. 5"],
    "g3": ["CST:art. 186"],
    "g4": ["CST:art. 46"],
    "g5": ["Ley 100/1993:art. 22"],
}

# ────────────────────────────────────────────────────────────────────────────
# Títulos por (gap_id, remedy_type)
# ────────────────────────────────────────────────────────────────────────────
_TITLES: dict[tuple[str, str], str] = {
    ("g1", "otrosi"):             "Otrosí No. 1 — Ajuste de jornada laboral a {jornada_nueva} horas",
    ("g2", "contrato_corregido"): "Contrato Corregido — Regularización de vínculo laboral",
    ("g3", "instruccion_nomina"): "Instrucción a Nómina — Liquidación de vacaciones acumuladas",
    ("g4", "acta_terminacion"):   "Acta de Terminación — Contrato a Término Fijo",
    ("g5", "instruccion_nomina"): "Instrucción a Nómina — Regularización de seguridad social",
}

# ────────────────────────────────────────────────────────────────────────────
# Esqueletos (cifras y partes ya inyectados vía .format_map)
# ────────────────────────────────────────────────────────────────────────────

_SKELETONS: dict[str, str] = {

    "g1_otrosi": """\
## Otrosí No. 1 al Contrato Individual de Trabajo — Ajuste de Jornada

**Entre:**
- **EMPLEADOR:** {employer_name}{employer_nit_sfx}
- **TRABAJADOR:** {worker_name}{worker_doc_sfx}
- **CARGO:** {worker_role}
- **CONTRATO ORIGINAL DEL:** {contract_start}

Con fundamento en la **Ley 2101 de 2021, artículo 3**, que establece la reducción \
de la jornada máxima legal ordinaria a **{jornada_nueva} horas semanales** con vigencia \
plena a partir del 1.° de julio de 2026, las partes de común acuerdo suscriben el \
presente otrosí:

**PRIMERO — MODIFICACIÓN DE JORNADA:** La cláusula de jornada del contrato queda \
modificada: la jornada ordinaria de trabajo será de **{jornada_nueva} horas semanales**, \
distribuidas según lo acuerden las partes, sin sobrepasar el límite legal.

**SEGUNDO — FUNDAMENTO NORMATIVO:** Esta modificación da cumplimiento a la Ley 2101 \
de 2021 (reducción progresiva de jornada), cuya vigencia plena rige desde el \
1.° de julio de 2026.

**TERCERO — VIGENCIA:** El presente otrosí entra en vigor a partir del 1.° de julio \
de 2026.

**CUARTO — PERMANENCIA:** Las demás cláusulas y condiciones del contrato individual \
de trabajo permanecen inalteradas.

En la ciudad de {city}, a los ___ días del mes de ___ de 2026.

___________________________          ___________________________
**EMPLEADOR**                        **TRABAJADOR**
{employer_name}                      {worker_name}
{employer_nit_sfx_plain}             {worker_doc_sfx_plain}
""",

    "g2_contrato_corregido": """\
## Contrato de Trabajo — Versión Corregida (Regularización del Vínculo Laboral)

**Entre:**
- **EMPLEADOR:** {employer_name}{employer_nit_sfx}
- **TRABAJADOR:** {worker_name}{worker_doc_sfx}
- **CARGO:** {worker_role}

Con fundamento en la **Ley 2466 de 2025, artículo 5**, que establece indicios de \
subordinación en contratos de prestación de servicios, y en los indicios detectados en \
el vínculo actual, las partes acuerdan formalizar la relación como contrato de trabajo:

**PRIMERO — VÍNCULO:** Este instrumento reemplaza el contrato de prestación de servicios \
y constituye un contrato individual de trabajo a términos del Código Sustantivo del Trabajo.

**SEGUNDO — DERECHOS:** El trabajador tendrá derecho a todas las prestaciones sociales \
de ley: cesantías, prima, vacaciones, seguridad social y auxilio de transporte si aplica.

**TERCERO — VIGENCIA:** Rige desde la fecha de suscripción.

En la ciudad de {city}, a los ___ días del mes de ___ de 2026.

___________________________          ___________________________
**EMPLEADOR**                        **TRABAJADOR**
{employer_name}                      {worker_name}
{employer_nit_sfx_plain}             {worker_doc_sfx_plain}
""",

    "g3_instruccion_nomina": """\
## Instrucción a Nómina — Liquidación de Vacaciones Acumuladas

**Trabajador:** {worker_name}{worker_doc_sfx}
**Cargo:** {worker_role}
**Empleador:** {employer_name}{employer_nit_sfx}

Con fundamento en el **Código Sustantivo del Trabajo, artículo 186**, se instruye al \
área de nómina:

**PRIMERO — ACCIÓN:** Liquidar y pagar las vacaciones acumuladas al trabajador, \
calculadas sobre el salario promedio de los últimos seis (6) meses.

**SEGUNDO — PLAZO:** El pago deberá efectuarse en el próximo período de nómina.

**TERCERO — SOPORTE:** Registrar el egreso con referencia al artículo 186 del CST.

Fecha de instrucción: ___________________________
Responsable de nómina: ___________________________
""",

    "g4_acta_terminacion": """\
## Acta de Terminación de Contrato a Término Fijo

**Entre:**
- **EMPLEADOR:** {employer_name}{employer_nit_sfx}
- **TRABAJADOR:** {worker_name}{worker_doc_sfx}
- **CARGO:** {worker_role}
- **CONTRATO DEL:** {contract_start}

Con fundamento en el **Código Sustantivo del Trabajo, artículo 46**, las partes dejan \
constancia de la terminación del contrato individual de trabajo a término fijo.

**PRIMERO — TERMINACIÓN:** El contrato termina por vencimiento del plazo pactado.

**SEGUNDO — LIQUIDACIÓN DE PRESTACIONES SOCIALES:**
Las siguientes cifras fueron calculadas por el motor determinista (M4):

| Concepto                         | Valor (COP)              |
|----------------------------------|--------------------------|
| Cesantías                        | $ {cesantias}            |
| Intereses s/cesantías (12% a.)   | $ {intereses_cesantias}  |
| Prima de servicios               | $ {prima}                |
| Vacaciones                       | $ {vacaciones}           |

**TERCERO — PAZ Y SALVO:** Firmado este documento, las partes se declaran a paz y salvo \
por todo concepto derivado del contrato.

En la ciudad de {city}, a los ___ días del mes de ___ de 2026.

___________________________          ___________________________
**EMPLEADOR**                        **TRABAJADOR**
{employer_name}                      {worker_name}
{employer_nit_sfx_plain}             {worker_doc_sfx_plain}
""",

    "g5_instruccion_nomina": """\
## Instrucción a Nómina — Regularización de Seguridad Social

**Trabajador:** {worker_name}{worker_doc_sfx}
**Cargo:** {worker_role}
**Empleador:** {employer_name}{employer_nit_sfx}

Con fundamento en la **Ley 100 de 1993, artículo 22**, se instruye:

**PRIMERO — ACCIÓN INMEDIATA:** Regularizar los aportes en mora a salud, pensión \
y riesgos laborales en la plataforma PILA.

**SEGUNDO — INTERESES DE MORA:** Liquidar y pagar los intereses de mora conforme \
a la normativa vigente.

**TERCERO — CERTIFICACIÓN:** Obtener el paz y salvo de la PILA antes del cierre \
del período contable.

Fecha de instrucción: ___________________________
Responsable de nómina: ___________________________
""",
}


# ────────────────────────────────────────────────────────────────────────────
# API pública del módulo
# ────────────────────────────────────────────────────────────────────────────

def _format_cop(value: float) -> str:
    """Formatea un monto COP con puntos de miles (notación colombiana): 1000000 → '1.000.000'."""
    return f"{int(round(value)):,}".replace(",", ".")


def _referenced_keys(gap_id: str, remedy_type: str) -> set[str]:
    """Extrae los nombres de {placeholder} del skeleton correspondiente."""
    template = _SKELETONS.get(f"{gap_id}_{remedy_type}", "")
    return set(re.findall(r"\{(\w+)\}", template))


def build_figures(gap_id: str, remedy_type: str, liquidation_data: dict | None) -> dict:
    """
    Combina figuras estáticas del gap con cifras dinámicas de M4.

    Bug fix (ADR-M5-002): en la versión anterior se mezclaban TODAS las claves
    numéricas de M4 en `figures`, aunque el skeleton no las referenciara.
    validate_figures fallaba porque buscaba esas cifras en un texto que no las
    contenía → BlockedOutput incorrecto en g4 + liquidation_data.

    Solución: solo se incluyen las claves de liquidation_data que tienen un
    {placeholder} correspondiente en el skeleton del gap/remedy_type. Las cifras
    de M4 se formatean en notación COP ('1.000.000') antes de inyectarlas.
    validate_figures verificará la cadena formateada, no el float crudo.
    """
    figures = dict(_STATIC_FIGURES.get(gap_id, {}))
    if liquidation_data:
        allowed = _referenced_keys(gap_id, remedy_type)
        for key, value in liquidation_data.items():
            if key in allowed and isinstance(value, (int, float)):
                figures[key] = _format_cop(value)
    return figures


def build_skeleton(
    gap_id: str,
    remedy_type: str,
    figures: dict,
    party_data: dict | None = None,
) -> str:
    """
    Devuelve el borrador con cifras y datos de partes sustituidos.

    Usa _SafeDict para que claves faltantes muestren un placeholder
    legible ([employer_name]) en lugar de lanzar KeyError.
    """
    key = f"{gap_id}_{remedy_type}"
    template = _SKELETONS.get(key, _generic_skeleton(gap_id, remedy_type))
    context = _SafeDict({**figures, **_party_defaults(party_data or {})})
    try:
        return template.format_map(context)
    except (KeyError, ValueError):
        return template


def _generic_skeleton(gap_id: str, remedy_type: str) -> str:
    return (
        f"## Documento correctivo — {remedy_type.replace('_', ' ').title()}\n\n"
        f"En atención al hallazgo {gap_id}, se emite el presente documento de subsanación "
        f"conforme a la normativa aplicable.\n"
    )


_MESES = ["ene", "feb", "mar", "abr", "may", "jun",
          "jul", "ago", "sep", "oct", "nov", "dic"]


def _format_fecha(value: str) -> str:
    """ISO '2024-03-01' -> '1 de mar de 2024'. Si no es ISO, se devuelve tal cual
    (degradación honesta: no se inventa una fecha)."""
    try:
        y, m, d = value.split("-")
        return f"{int(d)} de {_MESES[int(m) - 1]} de {y}"
    except (ValueError, IndexError, AttributeError):
        return value


def _party_defaults(party_data: dict) -> dict:
    """
    Construye el contexto de partes con valores de fallback para claves
    opcionales y sufijos pre-formateados (NIT, C.C.) para simplificar templates.
    """
    employer_name = party_data.get("employer_name", "[EMPLEADOR]")
    employer_nit  = party_data.get("employer_nit",  "")
    worker_name   = party_data.get("worker_name",  "[TRABAJADOR]")
    worker_doc    = party_data.get("worker_doc",   "")
    worker_role   = party_data.get("worker_role",  "[CARGO]")
    contract_start = party_data.get("contract_start", "[FECHA INICIO]")
    city          = party_data.get("city") or "[CIUDAD]"

    return {
        "employer_name":      employer_name,
        "employer_nit_sfx":   f", NIT {employer_nit}" if employer_nit else "",
        "employer_nit_sfx_plain": f"NIT {employer_nit}" if employer_nit else "",
        "worker_name":        worker_name,
        "worker_doc_sfx":     f", C.C. {worker_doc}" if worker_doc else "",
        "worker_doc_sfx_plain": f"C.C. {worker_doc}" if worker_doc else "",
        "worker_role":        worker_role,
        "contract_start":     _format_fecha(contract_start),
        "city":               city,
    }


class _SafeDict(dict):
    """Devuelve '[{key}]' para claves ausentes en .format_map()."""
    def __missing__(self, key: str) -> str:
        return f"[{key}]"


def build_title(gap_id: str, remedy_type: str, figures: dict) -> str:
    template = _TITLES.get((gap_id, remedy_type), f"Documento correctivo {gap_id}")
    try:
        return template.format_map(_SafeDict(figures))
    except (KeyError, ValueError):
        return template


def gap_citations(gap_id: str) -> list[str]:
    """Devuelve las claves de corpus ('{norm_id}:{article}') para el gap dado."""
    return list(_CITATION_KEYS.get(gap_id, []))
