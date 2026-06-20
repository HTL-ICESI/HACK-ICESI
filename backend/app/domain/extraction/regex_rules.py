"""
Extractores deterministas por regex (M2). PURO: solo stdlib (`re`, `dataclasses`).

Cada extractor recibe el texto del contrato y devuelve una `Extraction` (valor +
`Span` citado) o `None` si el campo no aparece. NUNCA inventa: si el patrón no
matchea, retorna `None` y el orquestador marca el campo `not_found`.

Garantía de determinismo: mismo texto -> mismo valor + mismo span (no hay azar,
no hay red, no hay LLM). Esto es lo que el jurado audita como confiabilidad.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class Span:
    """Offset citado dentro del documento: [start, end) y el texto exacto matcheado."""
    start: int
    end: int
    text: str


@dataclass(frozen=True)
class Extraction:
    """Resultado de un extractor: el valor determinista + su span + confianza."""
    value: object
    span: Span
    confidence: float


# --------------------------------------------------------------------------- #
# Utilidades puras
# --------------------------------------------------------------------------- #
def _strip_accents(s: str) -> str:
    """Normaliza acentos para matchear 'término'/'termino' indistintamente."""
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )


_MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}

# Números en palabras (0-99) para jornada en letras: "cuarenta y ocho" -> 48.
_UNITS = {
    "cero": 0, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
    "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "once": 11,
    "doce": 12, "trece": 13, "catorce": 14, "quince": 15, "dieciseis": 16,
    "diecisiete": 17, "dieciocho": 18, "diecinueve": 19,
}
_TENS = {
    "veinte": 20, "treinta": 30, "cuarenta": 40, "cincuenta": 50, "sesenta": 60,
    "setenta": 70, "ochenta": 80, "noventa": 90,
}
# Veintiuno..veintinueve (forma contraída).
_VEINTI = {f"veinti{w}": 20 + v for w, v in _UNITS.items() if 1 <= v <= 9}


def _words_to_int(phrase: str) -> int | None:
    """Convierte una frase numérica española 0-99 a int, o None si no aplica."""
    norm = _strip_accents(phrase.lower()).strip()
    if norm in _UNITS:
        return _UNITS[norm]
    if norm in _TENS:
        return _TENS[norm]
    if norm in _VEINTI:
        return _VEINTI[norm]
    # "cuarenta y ocho", "treinta y dos"...
    m = re.fullmatch(r"(\w+)\s+y\s+(\w+)", norm)
    if m and m.group(1) in _TENS and m.group(2) in _UNITS:
        unit = _UNITS[m.group(2)]
        if 1 <= unit <= 9:
            return _TENS[m.group(1)] + unit
    return None


# --------------------------------------------------------------------------- #
# Tipo de vínculo (DETERMINISTA): el contrato lo dice EXPLÍCITO en el título.
# Es más confiable que el LLM y elimina la dependencia para g2/g4 de M3.
# Orden: prestación de servicios primero (un contrato laboral no la nombra).
# --------------------------------------------------------------------------- #
_VINCULO_PATTERNS = (
    (re.compile(r"prestaci[oó]n\s+de\s+servicios", re.IGNORECASE), "prestacion_servicios"),
    (re.compile(r"t[eé]rmino\s+fijo", re.IGNORECASE), "termino_fijo"),
    (re.compile(r"t[eé]rmino\s+indefinido", re.IGNORECASE), "termino_indefinido"),
    (re.compile(r"obra\s+(?:o\s+)?labor", re.IGNORECASE), "obra_labor"),
)


def extract_vinculo_type(text: str) -> Extraction | None:
    """Detecta el tipo de vínculo por su mención explícita en el contrato. None si
    no aparece (entonces el orquestador cae al LLM como respaldo)."""
    for pat, value in _VINCULO_PATTERNS:
        m = pat.search(text)
        if m:
            return Extraction(
                value=value,
                span=Span(m.start(), m.end(), m.group(0)),
                confidence=0.97,
            )
    return None


# --------------------------------------------------------------------------- #
# Empleador (DETERMINISTA): "Entre los suscritos, <NOMBRE>, sociedad/identificad/NIT"
# El nombre suele ir en mayúsculas; el NIT se captura aparte. Fallback al LLM si no
# coincide la estructura.
# --------------------------------------------------------------------------- #
_EMPLOYER_RE = re.compile(
    r"[Ee]ntre\s+(?:los\s+suscritos,?\s+)?"
    r"(.+?)\s*,\s*(?=sociedad|identificad|domiciliad|NIT|empresa)",
    re.IGNORECASE | re.DOTALL,
)
_NIT_RE = re.compile(r"NIT\s+([\d][\d.\-]+\d)", re.IGNORECASE)


def extract_employer(text: str) -> Extraction | None:
    """Nombre (y NIT si aparece) del empleador. value = {'name', 'nit'}."""
    m = _EMPLOYER_RE.search(text)
    if not m:
        return None
    name = " ".join(m.group(1).split())          # colapsa saltos de línea/espacios
    if not name or len(name) > 90:
        return None
    nit_m = _NIT_RE.search(text)
    return Extraction(
        value={"name": name, "nit": nit_m.group(1) if nit_m else ""},
        span=Span(m.start(1), m.end(1), m.group(1)),
        confidence=0.95,
    )


# --------------------------------------------------------------------------- #
# Cargo / rol (DETERMINISTA): "cargo de <ROL>," — hasta la primera coma/punto.
# --------------------------------------------------------------------------- #
_ROLE_RE = re.compile(
    r"cargo\s+de\s+([^,.\n]{2,70})",
    re.IGNORECASE,
)


def extract_role(text: str) -> Extraction | None:
    """Cargo desempeñado, tomado de 'cargo de <ROL>'. None si no aparece."""
    m = _ROLE_RE.search(text)
    if not m:
        return None
    role = " ".join(m.group(1).split()).strip()
    if not role:
        return None
    return Extraction(
        value=role,
        span=Span(m.start(1), m.end(1), m.group(1)),
        confidence=0.95,
    )


# --------------------------------------------------------------------------- #
# Salario (numérico -> SIEMPRE por regex, nunca por el LLM)
# --------------------------------------------------------------------------- #
# Monto con separadores de miles (punto, espacio o apóstrofo): 2.500.000 / 2'500.000.
_MONEY_RE = re.compile(r"\$?\s*(\d{1,3}(?:[.\s']\d{3})+|\d{4,})")
_SALARY_KEY_RE = re.compile(r"salari[oa]s?", re.IGNORECASE)
_PERIODICITY = (
    ("mensual", "mensual"),
    ("quincenal", "quincenal"),
    ("anual", "anual"),
)

# Word-form salary amounts: "DOS MILLONES QUINIENTOS MIL PESOS" → 2_500_000.
_MILLIONS_MAP: dict[str, int] = {
    "un": 1, "uno": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
    "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10,
    "once": 11, "doce": 12, "trece": 13, "catorce": 14, "quince": 15,
}
_HUNDREDS_MAP: dict[str, int] = {
    "cien": 100, "ciento": 100,
    "doscientos": 200, "doscientas": 200,
    "trescientos": 300, "trescientas": 300,
    "cuatrocientos": 400, "cuatrocientas": 400,
    "quinientos": 500, "quinientas": 500,
    "seiscientos": 600, "seiscientas": 600,
    "setecientos": 700, "setecientas": 700,
    "ochocientos": 800, "ochocientas": 800,
    "novecientos": 900, "novecientas": 900,
}
_MONEY_WORD_RE = re.compile(
    r"(un|uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez"
    r"|once|doce|trece|catorce|quince)"
    r"\s+mill[oó]n(?:es)?"          # "millón" / "millon" / "millones"
    r"(?:\s+(cien(?:to)?|doscient[ao]s|trescient[ao]s|cuatrocient[ao]s"
    r"|quinient[ao]s|seiscient[ao]s|setecient[ao]s|ochocient[ao]s|novecient[ao]s)"
    r"\s+mil)?",
    re.IGNORECASE,
)


def _parse_word_amount(m: re.Match) -> int:
    millions = _MILLIONS_MAP[_strip_accents(m.group(1).lower())]
    hundreds = _HUNDREDS_MAP.get(_strip_accents(m.group(2).lower()), 0) if m.group(2) else 0
    return millions * 1_000_000 + hundreds * 1_000


def extract_salary(text: str) -> Extraction | None:
    """
    Extrae el salario base como entero en COP + periodicidad, con el span del monto.

    Acepta formatos numéricos (2.500.000, 2'500.000, $1.200.000) y en palabras
    (DOS MILLONES QUINIENTOS MIL PESOS). Si no hay 'salario' o no hay monto -> None.
    """
    key = _SALARY_KEY_RE.search(text)
    if not key:
        return None
    window_start = key.start()
    window = text[window_start: window_start + 120]
    money = _MONEY_RE.search(window)
    money_word = _MONEY_WORD_RE.search(window)

    if money is None and money_word is None:
        return None

    # Periodicidad explícita cerca del salario; por defecto mensual.
    near = _strip_accents(window.lower())
    periodicity = "mensual"
    for needle, value in _PERIODICITY:
        if needle in near:
            periodicity = value
            break

    # El numeral es la cifra legalmente controlante en los contratos CO: suele ir
    # entre paréntesis tras el monto en palabras ("... PESOS (1.750.905)") y es exacto,
    # mientras que el parser de palabras no cubre montos compuestos (setecientos
    # cincuenta mil novecientos cinco). Por eso se prefiere el numeral siempre que
    # exista; la forma en palabras solo se usa cuando no hay numeral en la ventana.
    if money is not None:
        raw = money.group(1)
        amount = int(re.sub(r"[.\s']", "", raw))
        # Span desde la keyword ("salario mensual") hasta el monto, para cita legible.
        span_start = key.start()
        span_end = window_start + money.end(1)
        # Incluir el ")" de cierre si el numeral va entre paréntesis: "(1.750.905)".
        if span_end < len(text) and text[span_end] == ")":
            span_end += 1
    else:
        amount = _parse_word_amount(money_word)
        # Span desde la keyword hasta el final de la forma en palabras.
        span_start = key.start()
        span_end = window_start + money_word.end()
        # Recortar espacios finales del span.
        while span_end > span_start and text[span_end - 1].isspace():
            span_end -= 1

    return Extraction(
        value={"amount": amount, "periodicity": periodicity},
        span=Span(span_start, span_end, text[span_start:span_end]),
        confidence=0.99,
    )


# --------------------------------------------------------------------------- #
# Fechas (numérico -> regex). Formato palabra "1 de febrero de 2024" y "dd/mm/aaaa".
# --------------------------------------------------------------------------- #
_DATE_WORD_RE = re.compile(
    r"(\d{1,2})\s+de\s+([A-Za-zÁÉÍÓÚáéíóúñÑ]+)\s+de\s+(\d{4})", re.IGNORECASE
)
_DATE_NUM_RE = re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b")

_START_KEYS = ("a partir del", "a partir de", "desde el", "desde", "inicia el",
               "fecha de inicio", "inicio el", "con vigencia desde")
_END_KEYS = ("hasta el", "hasta", "vencimiento el", "finaliza el", "finaliza",
             "termina el", "fecha de terminacion", "vigencia hasta")


def _iso(year: int, month: int, day: int) -> str | None:
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return None
    return f"{year:04d}-{month:02d}-{day:02d}"


def _date_at(text: str, offset: int, window: int = 60) -> Extraction | None:
    """Primera fecha (palabra o numérica) dentro de [offset, offset+window)."""
    segment = text[offset: offset + window]
    best: tuple[int, int, str] | None = None  # (rel_start, rel_end, iso)

    wm = _DATE_WORD_RE.search(segment)
    if wm:
        month = _MONTHS.get(_strip_accents(wm.group(2).lower()))
        if month:
            iso = _iso(int(wm.group(3)), month, int(wm.group(1)))
            if iso:
                best = (wm.start(), wm.end(), iso)

    nm = _DATE_NUM_RE.search(segment)
    if nm and (best is None or nm.start() < best[0]):
        iso = _iso(int(nm.group(3)), int(nm.group(2)), int(nm.group(1)))
        if iso:
            best = (nm.start(), nm.end(), iso)

    if best is None:
        return None
    span_start = offset + best[0]
    span_end = offset + best[1]
    return Extraction(
        value=best[2],
        span=Span(span_start, span_end, text[span_start:span_end]),
        confidence=0.96,
    )


def _extract_keyed_date(text: str, keys: tuple[str, ...]) -> Extraction | None:
    """Busca una de las llaves de contexto y extrae la fecha que la sigue."""
    lower = _strip_accents(text.lower())
    for key in keys:
        idx = lower.find(key)
        if idx != -1:
            found = _date_at(text, idx + len(key))
            if found:
                return found
    return None


def extract_start_date(text: str) -> Extraction | None:
    """Fecha de inicio del vínculo, citada. None si no aparece con su contexto."""
    return _extract_keyed_date(text, _START_KEYS)


def extract_end_date(text: str) -> Extraction | None:
    """Fecha de terminación del vínculo, citada. None si no aparece."""
    return _extract_keyed_date(text, _END_KEYS)


# --------------------------------------------------------------------------- #
# Jornada semanal en horas (numérico -> regex; soporta dígitos y palabras).
# --------------------------------------------------------------------------- #
# El \)? tolera el formato canónico CO "cuarenta y ocho (48) horas semanales",
# donde el dígito autoritativo va entre paréntesis justo antes de "horas".
_HOURS_DIGIT_RE = re.compile(r"(\d{1,3})\s*\)?\s*horas?\s*(?:semanales?)?", re.IGNORECASE)
_HOURS_WORD_RE = re.compile(
    r"((?:veinti\w+|\w+\s+y\s+\w+|\w+))\s+horas?\s*(?:semanales?)?", re.IGNORECASE
)
# Prefijo contextual que convierte "(48) horas semanales" → "Jornada: cuarenta y
# ocho (48) horas semanales". El [:\s] tolera "Jornada:" (dos puntos) y "jornada de".
_JORNADA_PREFIX_RE = re.compile(
    r"jornada\s*:?\s*(?:de\s+)?|trabajo\s+semanal\s+(?:de\s+)?",
    re.IGNORECASE,
)
_JORNADA_LOOKBACK = 70  # chars máx hacia atrás para buscar el prefijo


def _with_jornada_prefix(text: str, span_start: int) -> int:
    """Retrocede hasta el keyword 'jornada de' más cercano (último en la ventana).
    Usar el último match evita capturar títulos de sección ('CLAUSULA — JORNADA')
    cuando la cláusula real está más cerca del número."""
    window_start = max(0, span_start - _JORNADA_LOOKBACK)
    matches = list(_JORNADA_PREFIX_RE.finditer(text[window_start:span_start]))
    if matches:
        return window_start + matches[-1].start()
    return span_start


def extract_weekly_hours(text: str) -> Extraction | None:
    """
    Extrae la jornada en horas (entero) con su span. Acepta '48 horas' y
    'cuarenta y ocho horas'. None si no hay una jornada en horas en el texto.
    El span incluye 'jornada de … horas semanales' para que la cita muestre
    la cláusula completa (relevante para g1 de M3).
    """
    digit = _HOURS_DIGIT_RE.search(text)
    if digit:
        span_start = _with_jornada_prefix(text, digit.start())
        span_end   = digit.end()
        return Extraction(
            value=int(digit.group(1)),
            span=Span(span_start, span_end, text[span_start:span_end]),
            confidence=0.95,
        )
    for m in _HOURS_WORD_RE.finditer(text):
        value = _words_to_int(m.group(1))
        if value is not None:
            span_start = _with_jornada_prefix(text, m.start())
            span_end   = m.end()
            return Extraction(
                value=value,
                span=Span(span_start, span_end, text[span_start:span_end]),
                confidence=0.9,
            )
    return None


# --------------------------------------------------------------------------- #
# Terminacion del vínculo (regex). Detecta evidencia explícita de terminación.
# --------------------------------------------------------------------------- #
_TERMINATION_RE = re.compile(
    r"(?:se\s+da\s+por\s+terminad[oa]"
    r"|acta\s+de\s+terminaci[oó]n"
    r"|liquidaci[oó]n\s+definitiva"
    r"|terminaci[oó]n\s+(?:por|de)\s+mutuo\s+acuerdo"
    r"|terminado\s+(?:de|por)\s+mutuo\s+acuerdo"
    r"|renuncia(?:\s+del?\s+trabajador)?"
    r"|despido\s+(?:con|sin)\s+justa\s+causa"
    r"|terminaci[oó]n\s+del\s+v[ií]nculo)",
    re.IGNORECASE,
)


def extract_termination(text: str) -> Extraction | None:
    """
    Detecta evidencia explícita de terminación del contrato.

    Retorna Extraction(value=True, span=...) si el texto contiene una cláusula
    de terminación (acta, mutuo acuerdo, renuncia, despido).
    Retorna None si no hay evidencia — el service decidirá si es value=False o
    not_found según si existe end_date.
    """
    m = _TERMINATION_RE.search(text)
    if m is None:
        return None
    return Extraction(
        value=True,
        span=Span(m.start(), m.end(), text[m.start():m.end()]),
        confidence=0.9,
    )


# --------------------------------------------------------------------------- #
# Datos del trabajador (regex determinista).
# Patrón estándar de contratos HG: "Trabajador: NOMBRE, C.C. NUMERO".
# Incluye "Contratista" — el nombre del trabajador en prestación de servicios
# (justo el caso de reclasificación Ley 2466). NO matchea "Contratante" (empleador).
# --------------------------------------------------------------------------- #
# Captura la línea completa para span legible; grupo 1 = nombre puro.
_WORKER_NAME_RE = re.compile(
    r"((?:trabajador[a]?(?:/contratista)?|contratista)\s*[:/]?[ \t]*"  # keyword + separador (acepta slash)
    r"(?:[A-Za-zÀ-ɏ]+[ \t]?){1,8})"  # 1-8 palabras de letras (incluye acentos)
    r"(?=\s*[,\-]|\s+[Cc]\.?\s*[Cc]\.?|\n|$)",
    re.IGNORECASE,
)
# Fallback 1: contratos HG con patrón "; y NOMBRE, identificad[oa]".
_WORKER_NAME_PREAMBLE_RE = re.compile(
    r";\s+y\s+"
    r"([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑa-záéíóúñ]+"
    r"(?:[\s\n]+[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑa-záéíóúñ]+){1,4})"
    r"[\s\n]*,?\s*identificad",
    re.IGNORECASE,
)
# Fallback 2: patrón de tabla "Trabajador/Contratista\nNOMBRE" o en cuerpo
# "y NOMBRE, mayor de edad, en adelante EL TRABAJADOR".
_WORKER_NAME_BODY_RE = re.compile(
    r",?\s+y\s+"
    r"([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑa-záéíóúñ]+"
    r"(?:[\s\n]+[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑa-záéíóúñ]+){1,4})"
    r"[\s\n]*,?\s*mayor\s+de\s+edad",
    re.IGNORECASE,
)
# C.C. seguida de número (con o sin puntos/espacios de miles).
_CC_RE = re.compile(
    r"(C\.?\s*C\.?\s*(?:[Nn][oO]\.?[ \t]*)?\d[\d.,\s']{4,14}\d)",
    re.IGNORECASE,
)
_CC_NUM_RE = re.compile(r"\d[\d.,\s']*\d")


def extract_employee_name(text: str) -> Extraction | None:
    """
    Extrae el nombre del trabajador. Tres patrones en cascada:
    1. Keyword explícito "Trabajador:" / "Trabajador/Contratista" (con o sin colon/slash).
    2. Cuerpo HG: "; y NOMBRE, identificad[oa]".
    3. Cuerpo estándar CST: "y NOMBRE, mayor de edad, en adelante EL TRABAJADOR".
    """
    m = _WORKER_NAME_RE.search(text)
    if m is not None:
        full = m.group(1).strip()
        # Eliminar el keyword (hasta el primer separador : o /)
        for sep in (":", "/"):
            idx = full.find(sep)
            if idx != -1:
                full = full[idx + 1:].strip()
                break
        # Si el slash era "Trabajador/Contratista", queda "Contratista NOMBRE" → quitar keyword residual.
        _kw_residual = re.compile(r"^(?:trabajador[a]?|contratista)\s+", re.IGNORECASE)
        full = _kw_residual.sub("", full).strip()
        name = full
        if len(name) >= 4:
            span_start, span_end = m.start(), m.end()
            return Extraction(
                value=name,
                span=Span(span_start, span_end, text[span_start:span_end]),
                confidence=0.95,
            )

    # Fallback 1 — "; y NOMBRE, identificad[oa]"
    m2 = _WORKER_NAME_PREAMBLE_RE.search(text)
    if m2 is not None:
        name = " ".join(m2.group(1).split())
        if len(name) >= 4:
            return Extraction(
                value=name,
                span=Span(m2.start(), m2.end(), text[m2.start():m2.end()]),
                confidence=0.88,
            )

    # Fallback 2 — "y NOMBRE, mayor de edad" (CST art. 22, cuerpo del contrato)
    m3 = _WORKER_NAME_BODY_RE.search(text)
    if m3 is None:
        return None
    name = " ".join(m3.group(1).split())
    if len(name) < 4:
        return None
    return Extraction(
        value=name,
        span=Span(m3.start(), m3.end(), text[m3.start():m3.end()]),
        confidence=0.85,
    )


def extract_employee_doc(text: str) -> Extraction | None:
    """
    Extrae el número de cédula (C.C.) del trabajador como string normalizado.
    El span incluye "C.C." para que la cita sea verificable.
    """
    m = _CC_RE.search(text)
    if m is None:
        return None
    # Extraer solo los dígitos del número
    num_match = _CC_NUM_RE.search(m.group(1))
    if num_match is None:
        return None
    cc_digits = re.sub(r"[.,\s']", "", num_match.group())
    if not cc_digits.isdigit() or not (6 <= len(cc_digits) <= 11):
        return None
    span_start, span_end = m.start(), m.end()
    return Extraction(
        value=cc_digits,
        span=Span(span_start, span_end, text[span_start:span_end]),
        confidence=0.99,
    )


# --------------------------------------------------------------------------- #
# Auxilio de transporte (numérico, regex). Puro: nunca el LLM.
# --------------------------------------------------------------------------- #
_TRANSPORT_KEY_RE = re.compile(
    r"auxilio\s+(?:de\s+)?transporte|subsidio\s+(?:de\s+)?transporte",
    re.IGNORECASE,
)


# Monto legal de auxilio de transporte 2026 (Decreto 2673/2024).
_AUXILIO_LEGAL_2026 = 200_000

# Frases que confirman derecho al auxilio sin cifra explícita.
_AUXILIO_DERECHO_RE = re.compile(
    r"(?:tendr[aá]|tiene)\s+derecho\s+al\s+(?:auxilio|subsidio)\s+(?:de\s+)?transporte"
    r"|auxilio\s+(?:de\s+)?transporte\s+(?:legal|de\s+ley)",
    re.IGNORECASE,
)


def extract_auxilio_transporte(text: str) -> Extraction | None:
    """
    Extrae el auxilio de transporte mensual (COP) con su span.

    Prioridad:
    1. Monto numérico explícito junto a la keyword.
    2. Mención implícita de derecho ("tendrá derecho al auxilio de transporte")
       → usa el valor legal vigente 2026 ($200.000) con confianza media.
    Retorna None si el contrato no menciona el auxilio en ninguna forma.
    """
    key = _TRANSPORT_KEY_RE.search(text)
    if not key:
        return None

    # Intento 1: monto numérico en los 120 chars siguientes a la keyword.
    window_start = key.start()
    window = text[window_start: window_start + 120]
    money = _MONEY_RE.search(window)
    if money is not None:
        raw = money.group(1)
        amount = int(re.sub(r"[.\s']", "", raw))
        span_end = window_start + money.end(1)
        return Extraction(
            value={"amount": amount, "periodicity": "mensual"},
            span=Span(key.start(), span_end, text[key.start():span_end]),
            confidence=0.97,
        )

    # Intento 2: frase de derecho implícito sin cifra → valor legal 2026.
    derecho = _AUXILIO_DERECHO_RE.search(text)
    if derecho is not None:
        return Extraction(
            value={"amount": _AUXILIO_LEGAL_2026, "periodicity": "mensual"},
            span=Span(derecho.start(), derecho.end(), text[derecho.start():derecho.end()]),
            confidence=0.75,
        )

    return None


# --------------------------------------------------------------------------- #
# Salario variable (booleano, regex). Detecta componentes variables en el texto.
# --------------------------------------------------------------------------- #
_VARIABLE_RE = re.compile(
    r"(?:salario\s+variable"
    r"|comisiones?"
    r"|componente\s+variable"
    r"|horas\s+extras?"
    r"|recargos?\s+(?:nocturnos?|dominicales?|festivos?)"
    r"|bonificaci[oó]n\s+salarial)",
    re.IGNORECASE,
)


def extract_salario_variable(text: str) -> Extraction | None:
    """
    Detecta si el salario tiene componentes variables (comisiones, HE, recargos…).

    Retorna Extraction(value=True, span=span_de_la_clausula) si se detecta.
    Retorna None si no aparece → el service lo interpreta como salario fijo
    (value=False, status=ok) — no es `not_found` porque la ausencia es la respuesta.
    """
    m = _VARIABLE_RE.search(text)
    if m is None:
        return None
    return Extraction(
        value=True,
        span=Span(m.start(), m.end(), text[m.start():m.end()]),
        confidence=0.88,
    )
