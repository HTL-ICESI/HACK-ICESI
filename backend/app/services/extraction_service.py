"""
M2 service — orquesta la extracción del `DocumentRecord` con cita.

Reparto de responsabilidades (regla anti-alucinación):
- Campos NUMÉRICOS / de formato predecible (salario, fechas, jornada) -> dominio
  determinista (`app.domain.extraction`). NUNCA los decide el LLM.
- Campos de redacción variable (tipo de vínculo, cargo, empleador) -> LLM, pero su
  valor solo se acepta si trae un `span` verificable contra el texto. Sin span ->
  `needs_human`. Si el LLM ni lo menciona -> `not_found`.

Persiste el record namespaced por tenant para que M3/M4/M6 lo consuman, y deja
traza en el audit log.
"""
from __future__ import annotations

import re
import unicodedata

from app.core.tenancy import TenantContext
from app.core.audit import AuditLog
from app.adapters.storage.repository import InMemoryRepository
from app.adapters.llm.claude_client import ClaudeClient
from app.domain.extraction import (
    Extraction,
    extract_vinculo_type,
    extract_employer,
    extract_role,
    extract_salary,
    extract_start_date,
    extract_end_date,
    extract_weekly_hours,
    extract_termination,
    extract_employee_name,
    extract_employee_doc,
    extract_auxilio_transporte,
    extract_salario_variable,
)
from app.domain.models import (
    DocumentRecord,
    Field,
    Source,
    Money,
    Periodicity,
    FieldStatus,
)

COLLECTION = "records"


# --------------------------------------------------------------------------- #
# Utilidades de búsqueda determinista para verificar spans del LLM
# --------------------------------------------------------------------------- #

def _normalize(s: str) -> str:
    """Lowercase + strip accents para comparación insensible a caso y tildes."""
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    ).lower()


# Mapeo de enum values a la frase buscable en el texto del contrato.
_VINCULO_SEARCH: dict[str, str] = {
    "termino_fijo":         "termino fijo",
    "termino_indefinido":   "termino indefinido",
    "obra_labor":           "obra",
    "prestacion_servicios": "prestacion",
}


def _locate_value(value: object, text: str) -> tuple[int, int] | None:
    """
    Busca el valor del LLM en el texto de forma determinista.

    Para enums (vinculo_type) usa la frase canónica del contrato.
    Para strings (role) busca la cadena directamente.
    Para dicts (employer) busca el campo 'name'.

    Retorna (span_start, span_end) en el texto ORIGINAL, o None si no aparece.
    La búsqueda es insensible a mayúsculas y tildes.
    """
    if isinstance(value, str):
        phrase = _VINCULO_SEARCH.get(value, value).replace("_", " ")
    elif isinstance(value, dict) and "name" in value:
        phrase = str(value["name"])
    else:
        return None

    phrase = phrase.strip()
    if not phrase:
        return None

    norm_text = _normalize(text)
    norm_phrase = _normalize(phrase)
    idx = norm_text.find(norm_phrase)
    if idx == -1:
        return None
    return (idx, idx + len(phrase))


def _span_overlaps_value(value: object, snippet: str) -> bool:
    """
    Verificación mínima cruzada: ¿el texto citado contiene alguna palabra
    sustantiva del valor? (fallback cuando la búsqueda exacta falla).

    Ignora palabras cortas (artículos, preposiciones) de ≤ 3 letras.
    """
    if isinstance(value, str):
        phrase = _VINCULO_SEARCH.get(value, value).replace("_", " ")
    elif isinstance(value, dict) and "name" in value:
        phrase = str(value["name"])
    else:
        return False

    keywords = [w for w in re.split(r"\W+", phrase) if len(w) > 3]
    if not keywords:
        return False
    norm_snippet = _normalize(snippet)
    return any(_normalize(kw) in norm_snippet for kw in keywords)

# Esquema que se le exige al LLM: cada campo blando DEBE traer su span.
SOFT_FIELDS_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "vinculo_type": {
            "type": "object",
            "properties": {
                "value": {
                    "type": "string",
                    "enum": [
                        "termino_fijo", "termino_indefinido",
                        "obra_labor", "prestacion_servicios",
                    ],
                },
                "span_start": {"type": "integer"},
                "span_end": {"type": "integer"},
                "confidence": {"type": "number"},
            },
            "required": ["value", "span_start", "span_end"],
        },
        "role": {
            "type": "object",
            "properties": {
                "value": {"type": "string"},
                "span_start": {"type": "integer"},
                "span_end": {"type": "integer"},
                "confidence": {"type": "number"},
            },
            "required": ["value", "span_start", "span_end"],
        },
        "employer": {
            "type": "object",
            "properties": {
                "value": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "nit": {"type": "string"},
                    },
                    "required": ["name"],
                },
                "span_start": {"type": "integer"},
                "span_end": {"type": "integer"},
                "confidence": {"type": "number"},
            },
            "required": ["value", "span_start", "span_end"],
        },
    },
}

_SOFT_FIELDS = ("vinculo_type", "role", "employer")


class ExtractionService:
    def __init__(self, repo: InMemoryRepository, audit: AuditLog, llm: ClaudeClient) -> None:
        self._repo = repo
        self._audit = audit
        self._llm = llm

    async def extract(self, ctx: TenantContext, doc_id: str, text: str) -> DocumentRecord:
        # 1) Campos duros: dominio determinista (regex). Plata: nunca el LLM.
        sal = extract_salary(text)
        base_salary = self._money_field(sal, doc_id)
        auxilio_transporte = self._money_field(extract_auxilio_transporte(text), doc_id)
        salario_variable = self._boolean_flag_field(extract_salario_variable(text), doc_id)
        empleado_nombre = self._scalar_field(extract_employee_name(text), doc_id)
        empleado_documento = self._scalar_field(extract_employee_doc(text), doc_id)
        start_date = self._scalar_field(extract_start_date(text), doc_id)
        end_date = self._scalar_field(extract_end_date(text), doc_id)
        weekly_hours = self._scalar_field(extract_weekly_hours(text), doc_id)
        termination_confirmed = self._termination_field(
            extract_termination(text), end_date, doc_id
        )
        # vinculo_type es DETERMINISTA si el contrato lo dice explícito (regex).
        # Solo cae al LLM cuando el título no lo menciona. Así g2/g4 de M3 no
        # dependen del LLM (de-risk del campo que clasifica el régimen).
        vinculo_regex = self._scalar_field(extract_vinculo_type(text), doc_id)
        # employer y role también son deterministas si el contrato sigue la estructura
        # típica ("Entre los suscritos, <X>, sociedad…" / "cargo de <Y>,"). Así el
        # detalle queda completo incluso sin LLM (demo offline robusta).
        employer_regex = self._scalar_field(extract_employer(text), doc_id)
        role_regex = self._scalar_field(extract_role(text), doc_id)

        # 2) Campos blandos: LLM, pero cada valor exige span verificable.
        soft = await self._soft_fields(text, doc_id)

        vinculo_type = (
            vinculo_regex if vinculo_regex.status == FieldStatus.OK
            else soft["vinculo_type"]
        )
        employer = (
            employer_regex if employer_regex.status == FieldStatus.OK
            else soft["employer"]
        )
        role = role_regex if role_regex.status == FieldStatus.OK else soft["role"]

        record = DocumentRecord(
            doc_id=doc_id,
            employer=employer,
            empleado_nombre=empleado_nombre,
            empleado_documento=empleado_documento,
            role=role,
            vinculo_type=vinculo_type,
            base_salary=base_salary,
            auxilio_transporte=auxilio_transporte,
            salario_variable=salario_variable,
            start_date=start_date,
            end_date=end_date,
            weekly_hours=weekly_hours,
            termination_confirmed=termination_confirmed,
        )

        self._repo.put(ctx, COLLECTION, doc_id, record)
        self._audit.record(
            ctx, "extract", doc_id,
            # Solo campos que M2 puebla (Field). Los opcionales operativos (pago_ss_mora,
            # provistos por M4/M5) llegan en None y no se incluyen en el grounding.
            grounding=[f"{name}={fld.status.value}"
                       for name in DocumentRecord.model_fields if name != "doc_id"
                       if isinstance((fld := getattr(record, name)), Field)],
        )
        return record

    # ------------------------------------------------------------------ #
    # Builders de campos duros (numéricos / formato predecible)
    # ------------------------------------------------------------------ #
    def _money_field(self, ex: Extraction | None, doc_id: str) -> Field:
        if ex is None:
            return Field(value=None, source=None, status=FieldStatus.NOT_FOUND)
        money = Money(
            value=float(ex.value["amount"]),
            currency="COP",
            periodicity=Periodicity(ex.value["periodicity"]),
        )
        return Field(value=money, source=self._source(ex, doc_id), status=FieldStatus.OK)

    def _scalar_field(self, ex: Extraction | None, doc_id: str) -> Field:
        if ex is None:
            return Field(value=None, source=None, status=FieldStatus.NOT_FOUND)
        return Field(value=ex.value, source=self._source(ex, doc_id), status=FieldStatus.OK)

    def _termination_field(
        self, ex: Extraction | None, end_date_field: Field, doc_id: str
    ) -> Field:
        """
        Construye el campo termination_confirmed con semántica triestado:
        - value=True, status=ok, source=span  → clausula de terminación hallada.
        - value=False, status=ok, source=None → end_date existe pero sin clausula
                                                (zona gris; M3 chequea si ya venció).
        - value=None, status=not_found        → sin end_date (indefinido o indeterminado).
        """
        if ex is not None:
            return Field(value=True, source=self._source(ex, doc_id), status=FieldStatus.OK)
        if end_date_field.status == FieldStatus.OK:
            return Field(value=False, source=None, status=FieldStatus.OK)
        return Field(value=None, source=None, status=FieldStatus.NOT_FOUND)

    def _boolean_flag_field(self, ex: Extraction | None, doc_id: str) -> Field:
        """
        Booleano detectado por regex: value=True+span si hay evidencia en el texto;
        value=False sin source si no hay mención (la ausencia ES la respuesta,
        no una duda — nunca not_found para este tipo de campo).
        """
        if ex is not None:
            return Field(value=True, source=self._source(ex, doc_id), status=FieldStatus.OK)
        return Field(value=False, source=None, status=FieldStatus.OK)

    @staticmethod
    def _source(ex: Extraction, doc_id: str) -> Source:
        return Source(
            span_start=ex.span.start,
            span_end=ex.span.end,
            text=ex.span.text,
            confidence=ex.confidence,
            doc_id=doc_id,
        )

    # ------------------------------------------------------------------ #
    # Campos blandos: LLM + validación de span (anti-alucinación)
    # ------------------------------------------------------------------ #
    async def _soft_fields(self, text: str, doc_id: str) -> dict[str, Field]:
        try:
            raw = await self._llm.extract_soft_fields(text, SOFT_FIELDS_SCHEMA)
        except Exception:
            # Degradación honesta: si el LLM falla, no afirmamos nada blando.
            raw = {}
        if not isinstance(raw, dict):
            raw = {}
        return {name: self._validated_soft_field(raw.get(name), text, doc_id)
                for name in _SOFT_FIELDS}

    def _validated_soft_field(self, payload: object, text: str, doc_id: str) -> Field:
        # El LLM no lo mencionó -> not_found (no se inventa).
        if not isinstance(payload, dict) or payload.get("value") in (None, ""):
            return Field(value=None, source=None, status=FieldStatus.NOT_FOUND)

        value = payload["value"]
        source = self._source_from_payload(payload, text, doc_id)
        if source is None:
            # Hay un valor candidato pero SIN span verificable -> a revisión humana.
            return Field(value=value, source=None, status=FieldStatus.NEEDS_HUMAN)
        return Field(value=value, source=source, status=FieldStatus.OK)

    @staticmethod
    def _source_from_payload(payload: dict, text: str, doc_id: str) -> Source | None:
        """
        Construye el Source verificando que el valor exista en el texto.

        Estrategia (orden de prioridad):
        1. Búsqueda determinista: localizamos el valor en el texto nosotros mismos.
           → span 100% correcto, confianza alta.
        2. El LLM dio un span válido Y el texto citado contiene palabras clave del valor.
           → aceptamos con confianza media.
        3. Ninguna verificación posible → None (el service lo marcará needs_human).
        """
        value = payload.get("value")

        # 1. Búsqueda determinista: el valor debe aparecer literalmente en el texto.
        #    Usamos la confidence del LLM sobre el valor; el span lo ponemos nosotros.
        real = _locate_value(value, text)
        if real:
            llm_conf = payload.get("confidence")
            confidence = float(llm_conf) if isinstance(llm_conf, (int, float)) else 0.85
            return Source(
                span_start=real[0], span_end=real[1],
                text=text[real[0]:real[1]],
                confidence=confidence, doc_id=doc_id,
            )

        # 2. El LLM dio un span: solo lo aceptamos si el texto citado contiene
        #    al menos una palabra sustantiva del valor (verificación mínima cruzada).
        start, end = payload.get("span_start"), payload.get("span_end")
        if isinstance(start, int) and isinstance(end, int) and 0 <= start < end <= len(text):
            snippet = text[start:end]
            if snippet.strip() and _span_overlaps_value(value, snippet):
                confidence = payload.get("confidence")
                confidence = float(confidence) if isinstance(confidence, (int, float)) else 0.7
                return Source(
                    span_start=start, span_end=end, text=snippet,
                    confidence=confidence, doc_id=doc_id,
                )

        return None
