"""
Configuración del agente ElevenLabs para la DILIGENCIA DE DESCARGOS.

Port de AFFIRMA `src/agent_config.py`, adaptado al debido proceso disciplinario
colombiano: art. 29 CN + art. 115 CST (modificado por art. 7 Ley 2466/2025) +
Circular MinTrabajo 0048/2026 + Código Procesal del Trabajo. Doctrina CSJ Sala
Laboral (criterio reiterado: el despido con justa causa NO es sanción
disciplinaria y NO exige las formalidades del art. 115 — solo garantía de
defensa; cfr. línea C-593/2014 y jurisprudencia CSJ posterior).

CAMBIOS FRENTE A LA VERSIÓN 1 (resumen):
  (A) El art. 115 reformado tiene SIETE pasos mínimos, no cinco. Se añaden el
      aviso de DECISIÓN MOTIVADA y el DERECHO A IMPUGNAR (doble instancia).
  (B) El término de 5 días hábiles debe mediar ANTES de la diligencia (entre la
      citación/traslado de pruebas y los descargos). El agente ahora VERIFICA y
      REGISTRA que ese término previo se respetó, en vez de solo anunciar un
      plazo posterior.
  (C) Nuevo campo `process_type`: distingue SANCIÓN DISCIPLINARIA (115 pleno)
      de GARANTÍA DE DEFENSA PRE-DESPIDO (informal). Correr el 115 pleno para un
      despido eleva el estándar exigible — hay que saber qué proceso es.
  (D) La renuncia expresa a estar acompañado se captura aparte (blinda el acta
      cuando el trabajador decide continuar solo).
  (E) El silencio del trabajador es ejercicio LEGÍTIMO de defensa, no un vicio.
      Se separa "no tuvo oportunidad" (vicio) de "tuvo oportunidad y calló".
  (F) Se captura la SOLICITUD de pruebas del trabajador (contradicción).
  (G) DISCLOSURE de que es un asistente AUTOMATIZADO (lealtad/buena fe + dignidad
      + habeas data). No se presenta como persona.

La regla de oro NO cambia: el agente CONDUCE y CAPTURA; el guardián (código puro)
DECIDE. Ningún booleano del checklist lo "decide" el LLM.

NOTA: los nombres de campos de ElevenLabs cambian; verificar contra el dashboard
en vivo antes de importar (ver `_verify_live`).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Caso de descargos — el contexto que se inyecta por llamada (dynamic variables)
# ---------------------------------------------------------------------------

@dataclass
class DescargosCase:
    """Insumo de UNA diligencia. Todo lo específico es variable, así el mismo
    agente sirve para cualquier trabajador/empresa/falta."""
    session_id: str
    company_name: str                 # empresa empleadora (cliente de HG)
    worker_name: str                  # trabajador citado a descargos
    charges_summary: str              # relación clara de los hechos/cargos imputados
    evidence_summary: str             # pruebas que sustentan los cargos
    response_deadline: str            # término para complementar descargos por escrito

    # --- NUEVO (B): el término de defensa que YA transcurrió antes de la diligencia ---
    citation_date: str                # fecha en que se citó y se trasladaron las pruebas
    diligence_date: str               # fecha de esta diligencia
    defense_term_elapsed: str         # días hábiles transcurridos entre ambas (texto)

    # --- NUEVO (C): tipo de proceso (cambia el estándar exigible) ---
    # "sancion_disciplinaria"  -> art. 115 pleno (7 pasos)
    # "garantia_defensa_predespido" -> solo garantizar que el trabajador sea oído
    process_type: str = "sancion_disciplinaria"

    # --- NUEVO (D): ¿el trabajador está sindicalizado? (peso de nulidad distinto) ---
    worker_is_unionized: bool = False

    instructor_name: str = "Justo"   # nombre humano del asistente; la aclaración de que
                                      # es un sistema automatizado va explícita en FIRST_MESSAGE
    language: str = "es"

    def dynamic_variables(self) -> dict:
        """Los valores {{...}} que ElevenLabs inyecta por llamada."""
        return {
            "instructor_name": self.instructor_name,
            "company_name": self.company_name,
            "worker_name": self.worker_name,
            "charges_summary": self.charges_summary,
            "evidence_summary": self.evidence_summary,
            "response_deadline": self.response_deadline,
            "citation_date": self.citation_date,
            "diligence_date": self.diligence_date,
            "defense_term_elapsed": self.defense_term_elapsed,
            "process_type": self.process_type,
            "worker_is_unionized": str(self.worker_is_unionized).lower(),
            "language": self.language,
            "session_id": self.session_id,
        }


# ---------------------------------------------------------------------------
# Primer mensaje (DISCLOSURE de IA + advertencia de grabación + habeas data)
#   (G) Ya NO se presenta como persona. Declara que es un asistente automatizado.
# ---------------------------------------------------------------------------

FIRST_MESSAGE = (
    "Buenas, le habla {{instructor_name}}, del área de cumplimiento laboral, que actúa "
    "por encargo de la empresa {{company_name}}. Le aclaro desde ya que {{instructor_name}} "
    "es un asistente automatizado, es decir, un sistema asistido por computadora, no una "
    "persona; un abogado de la empresa revisa y firma el acta y la decisión final. Antes de "
    "comenzar le informo: esta llamada es grabada para dejar constancia de su diligencia de "
    "descargos y como prueba dentro del proceso. El tratamiento de sus datos se hace conforme "
    "a la ley de habeas data y usted puede pedir acceder a ellos, corregirlos o eliminarlos. "
    "¿Está hablando con {{worker_name}} y es un buen momento para atender la diligencia?"
)


# ---------------------------------------------------------------------------
# System prompt — el flujo EXACTO del debido proceso disciplinario.
# Cada paso del flujo corresponde a un atributo de DiligenceState.
# AHORA SON SIETE PASOS (art. 115 reformado), más el ramal pre-despido.
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
# Personalidad
Eres {{instructor_name}}, un asistente AUTOMATIZADO de cumplimiento laboral, profesional, sereno y
respetuoso, que conduce una diligencia de descargos por encargo de {{company_name}}. Hablas en lenguaje
claro y cotidiano, sin jerga jurídica. Tratas al trabajador con respeto y neutralidad: NO acusas, NO opinas
sobre la culpa, NO presionas. Solo garantizas que el trabajador entienda y pueda ejercer su defensa. Nunca
finges ser humano: si te preguntan, confirmas que {{instructor_name}} es un sistema automatizado y que un
abogado revisa el acta.

# Entorno
Estás en una llamada telefónica GRABADA con {{worker_name}}, trabajador de {{company_name}}. No puedes ver a
la persona; todo es por voz. El acta de esta diligencia y la decisión las revisa y firma un abogado de HG;
tú NO decides la sanción.

# Tipo de proceso (define cuánto rigor formal aplicas)
process_type = {{process_type}}
- Si es "sancion_disciplinaria": aplicas el procedimiento COMPLETO del art. 115 (los siete pasos).
- Si es "garantia_defensa_predespido": el objetivo es MÁS SIMPLE — basta que el trabajador sea oído y dé su
  versión. NO eleves el formalismo: lee los hechos, dale amplia oportunidad de responder y cierra. No anuncies
  un trámite sancionatorio que no corresponde, porque eso puede comprometer la decisión de la empresa.
Salvo que process_type sea "garantia_defensa_predespido", sigue los SIETE pasos en orden.

# Tono
Cálido, calmado, formal-cercano. Frases cortas, una idea a la vez. Verifica comprensión seguido
("¿me sigue hasta aquí?"). Nunca apresures. Sé paciente con la repetición y con el silencio.

# Objetivo — los SIETE pasos del debido proceso (art. 29 CN, art. 115 CST, Circular 0048/2026)

Paso 1 - Identidad y derecho a la defensa/acompañamiento.
  a) Confirma nombre completo y número de documento, leyéndolos de vuelta UNA sola vez.
  b) De forma OBLIGATORIA, ADVIÉRTELE EXPRESAMENTE su derecho a estar acompañado. Si worker_is_unionized es
     true, menciona EXPRESAMENTE el derecho a estar acompañado por hasta DOS representantes de su sindicato
     (garantía reforzada). Menciona también que puede asistir con un compañero o un abogado de su confianza.
  c) Adviértele que la diligencia puede APLAZARSE si desea ejercer ese derecho.
  d) Pregunta claramente: ¿desea continuar ahora, o aplazar para venir acompañado?
     - Si pide aplazar o pide abogado: RESPÉTALO. No sigas con el fondo. Registra
       outcome = "aplazada_por_acompanamiento" y cierra con respeto.
     - Si decide continuar solo: pídele que lo diga con sus palabras ("¿confirma que desea continuar hoy sin
       acompañante?") y registra esa RENUNCIA EXPRESA. Esto blinda el acta.
  (Omitir la advertencia del literal b es causal de NULIDAD, art. 29 CN.)

Paso 2 - Verificación del término de defensa (que ya transcurrió ANTES de hoy).
  Confírmale que fue citado el {{citation_date}}, que las pruebas se le trasladaron en esa oportunidad, y que
  entre esa fecha y hoy ({{diligence_date}}) transcurrieron {{defense_term_elapsed}} para preparar su defensa.
  Pregúntale si efectivamente recibió la citación y las pruebas con esa antelación y si tuvo tiempo de
  prepararse. Registra su respuesta. (El término no puede ser inferior a 5 días hábiles; si el trabajador
  dice que NO recibió antelación, regístralo: el guardián marcará un posible vicio.)

Paso 3 - Lectura de cargos.
  Léele de forma clara y completa los hechos y cargos imputados:
  {{charges_summary}}
  Asegúrate de que comprende QUÉ conducta se le imputa y cuándo habría ocurrido. Pregunta si lo entendió.

Paso 4 - Presentación de pruebas (contradicción).
  Indícale las pruebas en que se sustentan los cargos:
  {{evidence_summary}}
  Permite que conozca y controvierta cada prueba.

Paso 5 - Descargos del trabajador (lo central — derecho de defensa).
  Dale la palabra de forma AMPLIA: su versión de los hechos, sus explicaciones, y las pruebas que quiera
  APORTAR o SOLICITAR que se practiquen. NO lo interrumpas ni lo evalúes.
  - Si guarda silencio o decide no responder: es su derecho. Acláraselo, no lo presiones, y regístralo como
    silencio voluntario (NO como falta de oportunidad).
  - Si pide que se practiquen pruebas: anótalo textualmente como solicitud pendiente.
  Al final, resume lo que dijo y pregúntale si tu resumen es fiel.

Paso 6 - Aviso de decisión MOTIVADA.
  Infórmale que la empresa adoptará una decisión por ESCRITO y MOTIVADA, que explicará los hechos, las pruebas
  y las razones; y que esa decisión se le notificará. (No anticipes cuál será la decisión ni la sanción.)

Paso 7 - Aviso del derecho a IMPUGNAR + término.
  Infórmale EXPRESAMENTE que tendrá derecho a IMPUGNAR la decisión (recursos de reposición o apelación según el
  reglamento interno), y recuérdale el término que tiene para complementar sus descargos o aportar pruebas por
  escrito: {{response_deadline}}. El acta de esta diligencia quedará a su disposición.
  Agradece y cierra con respeto. Luego llama a submit_descargos con todo lo capturado.

# Guardarraíles
- El Paso 1(b) está INCOMPLETO si no advertiste EXPRESAMENTE el derecho a estar acompañado (y, si aplica, a
  los dos representantes sindicales) y a aplazar. Dilo con todas sus palabras; nunca lo des por hecho.
- Si el trabajador continúa solo, NO basta con que no haya pedido acompañante: necesitas su RENUNCIA EXPRESA.
- El silencio del trabajador NUNCA se registra como "no tuvo oportunidad de responder". Son cosas opuestas.
- Nunca emitas juicio sobre la culpa ni anticipes la decisión o la sanción. Tú garantizas el proceso.
- No inventes hechos, cargos ni pruebas. Solo lees {{charges_summary}} y {{evidence_summary}}. Lo demás, lo
  ve un abogado de HG.
- Si process_type es "garantia_defensa_predespido", NO uses lenguaje de "sanción" ni de "proceso disciplinario
  formal": limítate a oír al trabajador. Elevar el formalismo puede perjudicar a la empresa.
- Si hay una barrera (no entiende, indisposición, problema de salud), ofrece reprogramar; no fuerces.
- Confidencialidad del documento de identidad: léelo de vuelta una sola vez.
- Si preguntan, confirma que eres un sistema automatizado. Nunca afirmes ser humano.
- Habla en {{language}} (por defecto español de Colombia).

# Herramientas
- submit_descargos (webhook): llámala SOLO al cerrar, con todo lo capturado.
- end_call (sistema): finaliza la llamada tras el cierre.
"""


# ---------------------------------------------------------------------------
# Data Collection — extracción tipada post-llamada.
# Los booleanos MAPEAN 1:1 a DiligenceState (ver mapping.py).
# ---------------------------------------------------------------------------

def data_collection_schema() -> list[dict]:
    return [
        # --- identidad / soporte del acta ---
        {"identifier": "worker_full_name", "type": "string",
         "description": "Nombre completo del trabajador, confirmado en la llamada."},
        {"identifier": "worker_id_number", "type": "string",
         "description": "Número de documento de identidad del trabajador, confirmado en la llamada."},

        # --- Paso 1: acompañamiento + renuncia expresa (D) ---
        {"identifier": "right_to_companion_notified", "type": "boolean",
         "description": "True SOLO si se advirtió EXPRESAMENTE el derecho a estar acompañado "
                        "(y, si el trabajador es sindicalizado, a dos representantes del sindicato) "
                        "y a aplazar. Si no se dijo con todas sus palabras, False."},
        {"identifier": "union_representation_notified", "type": "boolean",
         "description": "True si, siendo el trabajador sindicalizado, se le advirtió EXPRESAMENTE el "
                        "derecho a estar acompañado por hasta dos representantes sindicales. Si no es "
                        "sindicalizado, dejar en false (no aplica al peso de nulidad)."},
        {"identifier": "worker_waived_companion", "type": "boolean",
         "description": "True SOLO si el trabajador renunció EXPRESAMENTE a estar acompañado y aceptó "
                        "continuar hoy. Si no hubo renuncia expresa (aunque haya seguido), False."},

        # --- Paso 2: término de defensa previo (B) ---
        {"identifier": "prior_defense_term_respected", "type": "boolean",
         "description": "True si el trabajador confirma que fue citado y recibió las pruebas con al menos "
                        "5 días hábiles de antelación a esta diligencia. False si dice que no tuvo esa "
                        "antelación."},

        # --- Pasos 3-4: cargos y pruebas ---
        {"identifier": "charges_read", "type": "boolean",
         "description": "True si se leyeron de forma clara y completa los hechos y cargos imputados."},
        {"identifier": "evidence_presented", "type": "boolean",
         "description": "True si se le indicaron al trabajador las pruebas que sustentan los cargos."},

        # --- Paso 5: descargos (defensa) + silencio + solicitud de pruebas (E, F) ---
        {"identifier": "worker_allowed_to_respond", "type": "boolean",
         "description": "True SOLO si el trabajador tuvo oportunidad REAL y amplia de rendir descargos. "
                        "OJO: si el trabajador tuvo la oportunidad pero eligió callar, esto sigue siendo "
                        "True (sí tuvo oportunidad). Solo es False si se le negó o interrumpió la palabra."},
        {"identifier": "worker_chose_silence", "type": "boolean",
         "description": "True si el trabajador, teniendo la oportunidad, decidió no rendir descargos "
                        "(silencio voluntario). Es ejercicio legítimo de defensa, no un vicio."},
        {"identifier": "worker_response_summary", "type": "string",
         "description": "Resumen fiel, en las palabras del trabajador, de los descargos que rindió. "
                        "Vacío si guardó silencio."},
        {"identifier": "evidence_requested_by_worker", "type": "string",
         "description": "Pruebas que el trabajador pidió que se practiquen o aporten, textual. Vacío si no "
                        "solicitó ninguna."},

        # --- Pasos 6-7: decisión motivada + impugnación (A) ---
        {"identifier": "motivated_decision_announced", "type": "boolean",
         "description": "True si se informó que la decisión será por escrito y motivada."},
        {"identifier": "right_to_appeal_notified", "type": "boolean",
         "description": "True si se advirtió EXPRESAMENTE el derecho a impugnar la decisión "
                        "(reposición/apelación según reglamento interno)."},

        # --- desenlace ---
        {"identifier": "outcome", "type": "string",
         "description": "Uno de: descargos_rendidos, descargos_con_silencio, "
                        "aplazada_por_acompanamiento, reprogramada, trabajador_no_disponible."},
    ]


def evaluation_criteria() -> list[dict]:
    return [
        {"identifier": "ai_disclosure_given",
         "description": "¿El agente declaró al inicio que es un sistema automatizado, no una persona?"},
        {"identifier": "recording_disclosure_given",
         "description": "¿El agente informó al inicio que la llamada es grabada y por qué (habeas data)?"},
        {"identifier": "right_to_companion_notified",
         "description": "¿Se advirtió EXPRESAMENTE el derecho a estar acompañado (sindicato si aplica) y a aplazar?"},
        {"identifier": "prior_defense_term_respected",
         "description": "¿Se verificó que medió un término no inferior a 5 días hábiles antes de la diligencia?"},
        {"identifier": "charges_clearly_read",
         "description": "¿Se leyeron los cargos de forma clara y completa?"},
        {"identifier": "worker_had_real_defense",
         "description": "¿El trabajador tuvo oportunidad real y amplia de rendir descargos (aun si calló)?"},
        {"identifier": "motivated_decision_and_appeal_notified",
         "description": "¿Se avisó que la decisión será motivada y que existe derecho a impugnarla?"},
    ]


def submit_descargos_tool(backend_host: str = "{{backend_host}}") -> dict:
    """Server (webhook) tool que se dispara al cerrar la diligencia."""
    return {
        "type": "webhook",
        "name": "submit_descargos",
        "description": (
            "Llamar SOLO al cerrar la diligencia. Envía lo capturado al backend "
            "para construir el DiligenceState, correr el guardián de debido proceso "
            "y generar el acta. NO determina la sanción."
        ),
        "api_schema": {
            "url": f"https://{backend_host}/api/disciplinary/call/webhook",
            "method": "POST",
            "request_headers": {"X-HG-Secret": "{{secret__backend_token}}"},
            "request_body_schema": {
                "conversation_id": {"type": "string", "description": "Id de conversación",
                                    "value_type": "dynamic_variable",
                                    "dynamic_variable": "system__conversation_id"},
                "session_id": {"type": "string", "description": "Id de la diligencia",
                               "value_type": "dynamic_variable", "dynamic_variable": "session_id"},
                "process_type": {"type": "string", "value_type": "dynamic_variable",
                                 "dynamic_variable": "process_type",
                                 "description": "sancion_disciplinaria | garantia_defensa_predespido"},
                "worker_full_name": {"type": "string", "value_type": "llm_prompt",
                                     "description": "Nombre completo confirmado en la llamada"},
                "worker_id_number": {"type": "string", "value_type": "llm_prompt",
                                     "description": "Número de documento confirmado"},
                "right_to_companion_notified": {"type": "boolean", "value_type": "llm_prompt",
                                                "description": "¿Se advirtió el derecho a acompañante?"},
                "union_representation_notified": {"type": "boolean", "value_type": "llm_prompt",
                                                  "description": "¿Se advirtió el derecho a dos reps. sindicales?"},
                "worker_waived_companion": {"type": "boolean", "value_type": "llm_prompt",
                                            "description": "¿Renunció EXPRESAMENTE a acompañante?"},
                "prior_defense_term_respected": {"type": "boolean", "value_type": "llm_prompt",
                                                 "description": "¿Medió >=5 días hábiles antes de hoy?"},
                "charges_read": {"type": "boolean", "value_type": "llm_prompt",
                                 "description": "¿Se leyeron los cargos?"},
                "evidence_presented": {"type": "boolean", "value_type": "llm_prompt",
                                       "description": "¿Se presentaron las pruebas?"},
                "worker_allowed_to_respond": {"type": "boolean", "value_type": "llm_prompt",
                                              "description": "¿El trabajador pudo rendir descargos?"},
                "worker_chose_silence": {"type": "boolean", "value_type": "llm_prompt",
                                         "description": "¿Eligió callar teniendo la oportunidad?"},
                "worker_response_summary": {"type": "string", "value_type": "llm_prompt",
                                            "description": "Resumen fiel de los descargos"},
                "evidence_requested_by_worker": {"type": "string", "value_type": "llm_prompt",
                                                 "description": "Pruebas que el trabajador pidió practicar"},
                "motivated_decision_announced": {"type": "boolean", "value_type": "llm_prompt",
                                                 "description": "¿Se avisó decisión motivada por escrito?"},
                "right_to_appeal_notified": {"type": "boolean", "value_type": "llm_prompt",
                                             "description": "¿Se advirtió el derecho a impugnar?"},
                "outcome": {"type": "string", "value_type": "llm_prompt",
                            "description": "Desenlace de la diligencia"},
            },
        },
    }


def build_agent_config(case: DescargosCase, *, backend_host: str = "{{backend_host}}") -> dict:
    """Configuración del agente ElevenLabs lista para importar/parchar."""
    return {
        "name": f"Cerebro Laboral HG — Diligencia de descargos ({case.company_name})",
        "first_message": FIRST_MESSAGE,
        "system_prompt": SYSTEM_PROMPT,
        "dynamic_variables": case.dynamic_variables(),
        "data_collection": data_collection_schema(),
        "evaluation_criteria": evaluation_criteria(),
        "tools": [submit_descargos_tool(backend_host)],
        "privacy": {"record_voice": True, "retention_days": 2555},  # evidencia: nunca 0
        "_verify_live": [
            "nombres de campos de data_collection / evaluation / server tool",
            "payload de post_call_transcription (+ fallback system__conversation_id)",
            "params de POST /v1/convai/twilio/outbound-call",
        ],
    }


def to_json(case: DescargosCase, **kw) -> str:
    return json.dumps(build_agent_config(case, **kw), indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Resolución de {{...}} (lo que ElevenLabs hace en vivo)
# ---------------------------------------------------------------------------

def resolve(text: str, variables: dict, keep: tuple = ()) -> str:
    """Sustituye {{key}} -> value. Las claves en `keep` se dejan como {{key}}.
    Placeholders desconocidos (p.ej. {{secret__...}}) se dejan intactos."""
    keepset = set(keep)
    out = text
    for key, value in variables.items():
        if key in keepset:
            continue
        out = out.replace("{{" + key + "}}", str(value))
    return out


def resolved_prompts(case: DescargosCase, *, keep: tuple = ()) -> dict:
    dv = case.dynamic_variables()
    return {
        "system_prompt": resolve(SYSTEM_PROMPT, dv, keep=keep),
        "first_message": resolve(FIRST_MESSAGE, dv, keep=keep),
    }


# Caso de muestra (para demo/tests) — falta disciplinaria típica.
def sample_case(session_id: str = "desc-001") -> DescargosCase:
    return DescargosCase(
        session_id=session_id,
        company_name="Empresa Cliente SAS",
        worker_name="Pedro Pérez",
        charges_summary=(
            "El día 12 de mayo de 2026 usted se ausentó de su puesto de trabajo "
            "durante toda la jornada sin presentar excusa ni autorización previa, "
            "incumpliendo el reglamento interno de trabajo."
        ),
        evidence_summary=(
            "Registro de control de acceso del 12 de mayo, reporte del jefe inmediato "
            "y planilla de asistencia del equipo."
        ),
        response_deadline="cinco (5) días hábiles",
        citation_date="2 de junio de 2026",
        diligence_date="11 de junio de 2026",
        defense_term_elapsed="siete (7) días hábiles",
        process_type="sancion_disciplinaria",
        worker_is_unionized=False,
    )
