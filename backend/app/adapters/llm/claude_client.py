"""
Adapter LLM para extraccion blanda (M2) y redaccion (M5).

Jerarquia de backends (se intenta en orden):
  1. Anthropic Claude Haiku  -- si ANTHROPIC_API_KEY esta presente.
  2. Infermatic / TotalGPT   -- si INFERMATIC_API_KEY esta presente (fallback OpenAI-compatible).
  3. Degradacion honesta      -- devuelve {} sin afirmar nada.

Regla invariante: el LLM SOLO entrega el VALOR de cada campo.
Los spans los calcula el service con _locate_value() de forma determinista.
Nunca le pedimos al LLM que cuente offsets de caracteres: falla en eso.
"""
from __future__ import annotations

import json
import re

from app.config import get_settings

_ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"

# ---------------------------------------------------------------------------
# Prompt para Infermatic / modelos OpenAI-compatible (Qwen 3.6).
#
# DISENO: el LLM solo da el VALOR. Los spans los calcula el service.
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """\
Eres un extractor juridico especializado en contratos laborales colombianos.

TAREA: Leer el contrato entre <doc></doc> y extraer UNICAMENTE los campos que
aparezcan ESCRITOS EXPLICITAMENTE en el texto. No deduzcas, no asumas.

CAMPOS A EXTRAER
================

1. vinculo_type  -- Tipo de contrato.
   Elige EXACTAMENTE uno de estos valores (solo si el contrato lo menciona):
   "termino_fijo"         -> texto dice "termino fijo", "TERMINO FIJO", "plazo fijo"
   "termino_indefinido"   -> texto dice "termino indefinido", "duracion indefinida"
   "obra_labor"           -> texto dice "obra o labor", "duracion de la obra"
   "prestacion_servicios" -> texto dice "prestacion de servicios"

2. role  -- Cargo o funcion del trabajador.
   Copia el texto exacto tal como aparece en el documento.
   Ejemplos: "Asesor comercial", "Analista de sistemas", "Auxiliar contable"

3. employer  -- La empresa o persona que contrata al trabajador.
   Formato: {"name": "nombre exacto del empleador", "nit": "NIT si aparece en el texto"}
   Si el NIT no esta en el texto, omite ese campo del objeto.

REGLAS
======
- Si un campo NO aparece explicitamente en el texto -> NO lo incluyas en la respuesta.
- Para employer.name: copia el nombre exactamente como esta en el documento.
- confidence: tu nivel de certeza de 0.0 a 1.0 (usa 0.9 si estas muy seguro).
- NO incluyas span_start ni span_end en tu respuesta.

FORMATO DE SALIDA
=================
JSON puro, sin markdown, sin explicaciones. Solo los campos que encontraste.

Ejemplo (tres campos encontrados):
{
  "vinculo_type": {"value": "termino_fijo",     "confidence": 0.95},
  "role":         {"value": "Asesor comercial", "confidence": 0.92},
  "employer":     {"value": {"name": "EMPRESA CLIENTE SAS", "nit": "900.123.456-7"}, "confidence": 0.90}
}

Ejemplo (solo encontraste role):
{
  "role": {"value": "Auxiliar contable", "confidence": 0.88}
}
"""

_USER_TEMPLATE = (
    "Analiza el siguiente contrato laboral y extrae los campos indicados.\n\n"
    "<doc>\n{text}\n</doc>\n\n"
    "Responde SOLO con el JSON. No incluyas campos que no esten en el texto."
)

_EXPECTED_FIELDS = ("vinculo_type", "role", "employer")


class ClaudeClient:
    def __init__(self) -> None:
        s = get_settings()
        self._anthropic_key    = s.anthropic_api_key
        self._infermatic_key   = s.infermatic_api_key
        self._infermatic_url   = s.infermatic_base_url
        self._infermatic_model = s.infermatic_model

    # Minimo de caracteres para que valga la pena llamar al LLM.
    # Un contrato real tiene clausulas, partes y condiciones: al menos 50 chars.
    _MIN_TEXT_LEN = 50

    async def extract_soft_fields(self, text: str, schema: dict) -> dict:
        """
        Extrae campos blandos. Intenta Anthropic -> Infermatic -> {}.

        El LLM devuelve {"field": {"value": ..., "confidence": float}}.
        Los spans los calcula el service con _locate_value() determinista.
        Textos demasiado cortos se saltan: el LLM alucina sobre texto vacio.
        """
        if len(text.strip()) < self._MIN_TEXT_LEN:
            return {}
        if self._anthropic_key:
            return await self._via_anthropic(text, schema)
        if self._infermatic_key:
            return await self._via_infermatic(text)
        return {}

    # ------------------------------------------------------------------ #
    # Backend 1: Anthropic (tool_use para output estructurado)
    # ------------------------------------------------------------------ #
    async def _via_anthropic(self, text: str, schema: dict) -> dict:
        try:
            from anthropic import AsyncAnthropic
            client = AsyncAnthropic(api_key=self._anthropic_key)
            prompt = (
                "Eres un extractor juridico. Del CONTRATO entre <doc></doc> extrae, "
                "cuando aparezcan EXPLICITAMENTE, estos campos blandos:\n"
                "- vinculo_type: uno de "
                "[termino_fijo, termino_indefinido, obra_labor, prestacion_servicios]\n"
                "- role: el cargo del trabajador (texto)\n"
                "- employer: el empleador como objeto {name, nit}\n\n"
                "REGLAS:\n"
                "1. Para CADA campo entrega span_start y span_end: offsets de caracter "
                "(0-indexados) del fragmento EXACTO del documento que justifica el valor.\n"
                "2. Si un campo NO aparece, OMITELO. Nunca inventes ni deduzcas.\n"
                "3. Responde SOLO con la herramienta, sin texto adicional.\n\n"
                f"<doc>{text}</doc>"
            )
            tool = {
                "name": "emit_fields",
                "description": "Emite los campos blandos extraidos con sus spans.",
                "input_schema": schema,
            }
            msg = await client.messages.create(
                model=_ANTHROPIC_MODEL,
                max_tokens=1024,
                tools=[tool],
                tool_choice={"type": "tool", "name": "emit_fields"},
                messages=[{"role": "user", "content": prompt}],
            )
            for block in msg.content:
                if getattr(block, "type", None) == "tool_use":
                    data = block.input
                    return data if isinstance(data, dict) else json.loads(data)
        except Exception:
            pass
        return {}

    # ------------------------------------------------------------------ #
    # Backend 2: Infermatic / TotalGPT (OpenAI-compatible, JSON mode)
    # ------------------------------------------------------------------ #
    async def _via_infermatic(self, text: str) -> dict:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(
                api_key=self._infermatic_key,
                base_url=self._infermatic_url,
            )
            resp = await client.chat.completions.create(
                model=self._infermatic_model,
                response_format={"type": "json_object"},
                max_tokens=512,
                temperature=0,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user",   "content": _USER_TEMPLATE.format(text=text)},
                ],
            )
            raw = resp.choices[0].message.content or "{}"
            raw = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
            data = json.loads(raw)
            return data if isinstance(data, dict) else {}
        except Exception:
            pass
        return {}

    # ------------------------------------------------------------------ #
    # Contraste descargo ↔ cargos (J1): ¿la defensa del trabajador responde
    # a lo que se le imputó? Tarea de LENGUAJE -> el LLM analiza; el resultado
    # es ASESOR (lo revisa el abogado), NO decide el debido proceso (eso es del
    # guardián determinista). Sin LLM -> "no_evaluado" (nunca inventa un juicio).
    # ------------------------------------------------------------------ #
    _CONTRAST_SCHEMA = {
        "type": "object",
        "properties": {
            "responde": {"type": "boolean",
                         "description": "¿El descargo aborda los cargos imputados?"},
            "cobertura": {"type": "string", "enum": ["total", "parcial", "nula"],
                          "description": "Qué tanto de los cargos quedó respondido."},
            "puntos_respondidos": {"type": "array", "items": {"type": "string"}},
            "puntos_sin_responder": {"type": "array", "items": {"type": "string"}},
            "contradice_evidencia": {"type": "boolean",
                                     "description": "¿El descargo contradice la evidencia aportada?"},
            "resumen": {"type": "string",
                        "description": "Síntesis neutral de 1-2 frases para el abogado."},
        },
        "required": ["responde", "cobertura", "resumen"],
    }

    async def analyze_descargo(self, charges_summary: str, evidence_summary: str,
                               descargo_text: str) -> dict:
        """Contrasta el descargo contra los cargos. Devuelve dict estructurado con
        `evaluado_por` = 'llm' | 'sin_llm'. Sin LLM degrada honestamente."""
        prompt = (
            "Eres un analista jurídico laboral colombiano, neutral. Contrasta el DESCARGO "
            "del trabajador contra los CARGOS imputados y la EVIDENCIA. No acuses ni absuelvas: "
            "solo analiza si la defensa responde a lo que se le imputó.\n\n"
            f"CARGOS IMPUTADOS:\n{charges_summary}\n\n"
            f"EVIDENCIA DE LA EMPRESA:\n{evidence_summary}\n\n"
            f"DESCARGO DEL TRABAJADOR:\n{descargo_text}\n\n"
            "Responde si el descargo aborda los cargos, qué cobertura tiene "
            "(total/parcial/nula), qué puntos respondió y cuáles no, y si contradice la evidencia."
        )
        if self._anthropic_key:
            data = await self._contrast_via_anthropic(prompt)
            if data:
                return {**data, "evaluado_por": "llm"}
        if self._infermatic_key:
            data = await self._contrast_via_infermatic(prompt)
            if data:
                return {**data, "evaluado_por": "llm"}
        # Degradación honesta: sin LLM no se emite un juicio.
        return {
            "responde": None, "cobertura": "no_evaluado",
            "puntos_respondidos": [], "puntos_sin_responder": [],
            "contradice_evidencia": None,
            "resumen": "Contraste automático no disponible (sin modelo). Revisión manual del abogado.",
            "evaluado_por": "sin_llm",
        }

    async def _contrast_via_anthropic(self, prompt: str) -> dict:
        try:
            from anthropic import AsyncAnthropic
            client = AsyncAnthropic(api_key=self._anthropic_key)
            tool = {"name": "emit_contrast",
                    "description": "Emite el contraste estructurado descargo↔cargos.",
                    "input_schema": self._CONTRAST_SCHEMA}
            msg = await client.messages.create(
                model=_ANTHROPIC_MODEL, max_tokens=1024, tools=[tool],
                tool_choice={"type": "tool", "name": "emit_contrast"},
                messages=[{"role": "user", "content": prompt}],
            )
            for block in msg.content:
                if getattr(block, "type", None) == "tool_use":
                    data = block.input
                    return data if isinstance(data, dict) else json.loads(data)
        except Exception:
            pass
        return {}

    async def _contrast_via_infermatic(self, prompt: str) -> dict:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=self._infermatic_key, base_url=self._infermatic_url)
            resp = await client.chat.completions.create(
                model=self._infermatic_model, response_format={"type": "json_object"},
                max_tokens=700, temperature=0,
                messages=[
                    {"role": "system", "content": "Responde SOLO con JSON válido del contraste."},
                    {"role": "user", "content": prompt + "\n\nDevuelve JSON con: responde (bool), "
                     "cobertura (total|parcial|nula), puntos_respondidos (lista), "
                     "puntos_sin_responder (lista), contradice_evidencia (bool), resumen (texto)."},
                ],
            )
            raw = resp.choices[0].message.content or "{}"
            raw = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
            data = json.loads(raw)
            return data if isinstance(data, dict) else {}
        except Exception:
            pass
        return {}

    async def draft_document(self, kind: str, context: dict) -> str:
        """
        Elabora el documento correctivo.

        El esqueleto ya tiene las cifras inyectadas por el código.
        El LLM SOLO amplía la prosa legal — nunca decide cifras.
        Degradación honesta: sin LLM → devuelve el esqueleto tal cual.
        El esqueleto ya pasa validate_figures porque las cifras están en él.
        """
        skeleton: str = context.get("skeleton", "")
        if self._anthropic_key:
            return await self._draft_via_anthropic(kind, context, skeleton)
        if self._infermatic_key:
            return await self._draft_via_infermatic_doc(kind, context, skeleton)
        # Degradación honesta: sin LLM → el esqueleto ya es un documento válido
        return skeleton

    # ------------------------------------------------------------------ #
    # Backends para draft_document
    # ------------------------------------------------------------------ #

    async def _draft_via_anthropic(self, kind: str, context: dict, skeleton: str) -> str:
        try:
            from anthropic import AsyncAnthropic
            client = AsyncAnthropic(api_key=self._anthropic_key)
            figures_note = ", ".join(
                f"{k}={v}" for k, v in context.get("figures", {}).items()
            )
            prompt = (
                f"Eres un redactor jurídico laboral colombiano. Tienes el borrador de un "
                f"documento de tipo '{kind}' ya con las cifras correctas inyectadas.\n\n"
                f"CIFRAS OBLIGATORIAS (no las cambies, no las elimines): {figures_note}\n\n"
                f"INSTRUCCIÓN: Elabora el texto legal completando la prosa entre las "
                f"secciones marcadas. Mantén TODAS las cifras intactas en el texto final. "
                f"Devuelve el documento completo en markdown.\n\n"
                f"BORRADOR:\n{skeleton}"
            )
            msg = await client.messages.create(
                model=_ANTHROPIC_MODEL,
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}],
            )
            text = msg.content[0].text.strip() if msg.content else ""
            return text or skeleton
        except Exception:
            return skeleton

    async def _draft_via_infermatic_doc(self, kind: str, context: dict, skeleton: str) -> str:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(
                api_key=self._infermatic_key,
                base_url=self._infermatic_url,
            )
            figures_note = ", ".join(
                f"{k}={v}" for k, v in context.get("figures", {}).items()
            )
            system = (
                "Eres un redactor jurídico laboral colombiano. "
                "Tu tarea: elaborar documentos correctivos laborales en español. "
                "REGLA CRÍTICA: NO modifiques, elimines ni reemplaces ningún número del borrador. "
                "Solo amplías la prosa legal. Devuelves el documento completo en markdown."
            )
            user = (
                f"Tipo de documento: {kind}\n"
                f"Cifras obligatorias (no alterar): {figures_note}\n\n"
                f"BORRADOR CON CIFRAS:\n{skeleton}\n\n"
                f"Elabora el documento manteniendo todas las cifras intactas."
            )
            resp = await client.chat.completions.create(
                model=self._infermatic_model,
                max_tokens=1500,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
            )
            text = (resp.choices[0].message.content or "").strip()
            text = _extract_document(text, skeleton)
            return text or skeleton
        except Exception:
            return skeleton


def _extract_document(text: str, skeleton: str) -> str:
    """
    Extrae el documento legal del output del LLM.

    Qwen/extended-thinking models a veces anteponen bloques de razonamiento
    en texto plano o con <think> tags. Esta función los descarta y devuelve
    solo el documento markdown. Si no encuentra un documento limpio, retorna
    el skeleton (que ya tiene las cifras correctas y pasa validate_figures).

    Orden de intento:
    1. Quitar <think>…</think> (tagged thinking, Qwen3 en modo explicit).
    2. Buscar el primer encabezado markdown (## …) — el documento real.
    3. Si lo que queda tiene un encabezado → documento válido.
    4. Si no → fallback al skeleton (evita body ilegible en el demo).
    """
    # 1. Quitar bloques <think>
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    # 2. Buscar el primer encabezado markdown
    match = re.search(r"^#{1,3} ", text, re.MULTILINE)
    if match:
        candidate = text[match.start():].strip()
        # Verificar que el candidato tiene estructura de documento (al menos 100 chars)
        if len(candidate) >= 100:
            return candidate

    # 3. Texto plano sin thinking y sin encabezados: si es largo y tiene contenido
    #    legal, lo aceptamos; si no, fallback al skeleton
    if len(text) >= 200 and not text.lower().startswith("here's"):
        return text

    return skeleton
