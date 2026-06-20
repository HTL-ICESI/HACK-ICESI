"""
J3 — Guardián de debido proceso. LA JOYA. NÚCLEO DETERMINISTA. (Dueño: David)

Implementa la spec `PROCESO-DISCIPLINARIO.md` (este mismo directorio): las 7
garantías del art. 115 CST (mod. Ley 2466/2025) + precondición de tipicidad
(art. 114) + régimen simplificado (despido justa causa / micro-empresa) y
clasifica el proceso en **CONFORME / PARCIAL / NULO**. 100% determinista: dado el
estado de la diligencia -> veredicto reproducible. Cero LLM.

Contrato de testing clave: si falta la oportunidad de descargos o el término de
5 días -> NULO con su cita; si solo faltan garantías subsanables -> PARCIAL.

Compatibilidad: el veredicto conserva `nullity_alert`, `can_proceed` y
`missing_steps` (forma antigua de J3) además de los campos nuevos.
"""
from __future__ import annotations

from dataclasses import dataclass, field


# --- Vocabulario -----------------------------------------------------------

class Clasificacion:
    CONFORME = "CONFORME"
    PARCIAL = "PARCIAL"
    NULO = "NULO"


class Severidad:
    ALTA = "ALTA"
    MEDIA = "MEDIA"


# --- Estado de la diligencia (entrada) -------------------------------------

@dataclass(frozen=True)
class DiligenceState:
    """Las 7 garantías del art. 115 + precondición + contexto. Cada garantía es un
    booleano (lo capturado en el proceso/la llamada). Defaults conservadores: lo no
    confirmado se asume ausente (lo seguro), salvo lo que por regla no bloquea."""

    # Precondición (§1) y tipo de actuación (§0)
    falta_tipificada: bool = True
    tipo_actuacion: str = "sancion_disciplinaria"   # | "despido_justa_causa"

    # Las 7 garantías mínimas (§2)
    comunicacion_apertura_formal: bool = False      # G1 — citación/apertura formal escrita
    formulacion_cargos_concretos: bool = False      # G2 — hechos/conductas concretos
    traslado_pruebas: bool = False                  # G3 — pruebas entregadas
    termino_defensa_minimo: bool = False            # G4 — >= 5 días hábiles
    oportunidad_descargos: bool = False             # G5 — pudo manifestarse/controvertir
    decision_motivada: bool = False                 # G6 — decisión motivada
    derecho_impugnacion: bool = False               # G7 — doble instancia

    # Contexto que ajusta el estándar
    num_trabajadores: int = 50                      # <=10 -> simplificado (§9)
    worker_is_unionized: bool = False               # omitir acompañamiento sindical = más grave
    derecho_acompanamiento_informado: bool = True   # §4 — su omisión es vicio MEDIA


# --- Definición de las garantías (norma + severidad + si fuerza nulidad) ----

@dataclass(frozen=True)
class _Garantia:
    key: str
    label: str
    norma: str
    forces_nullity: bool        # su ausencia => NULO directo (§8)
    detalle_falta: str


_GARANTIAS = [
    _Garantia("comunicacion_apertura_formal", "Comunicación formal de apertura",
              "CST art. 115", True,
              "No hubo comunicación formal y escrita de apertura/citación."),
    _Garantia("formulacion_cargos_concretos", "Formulación de cargos concretos",
              "CST art. 115", True,
              "Cargos genéricos o imprecisos (sin hechos, fechas ni norma concreta)."),
    _Garantia("traslado_pruebas", "Traslado de pruebas",
              "CST art. 115", False,
              "No se trasladaron las pruebas que sustentan los cargos (se impide la contradicción)."),
    _Garantia("termino_defensa_minimo", "Término mínimo de defensa (5 días hábiles)",
              "CST art. 115 (Ley 2466/2025), Circular 0048/2026", True,
              "Término de defensa inferior a 5 días hábiles entre citación y diligencia."),
    _Garantia("oportunidad_descargos", "Oportunidad de descargos",
              "CN art. 29 · CST art. 115", True,
              "No se dio oportunidad real de rendir descargos ni controvertir pruebas."),
    _Garantia("decision_motivada", "Decisión motivada",
              "CST art. 115 num. 5", False,
              "La decisión no es motivada (no identifica hechos, pruebas y razones)."),
    _Garantia("derecho_impugnacion", "Derecho a impugnar (doble instancia)",
              "Ley 2466/2025 · Circular 0048/2026", False,
              "No se informó/garantizó el derecho a impugnar (doble instancia)."),
]

# Régimen simplificado (§0 despido justa causa, §9 micro-empresa): solo el núcleo
# del derecho de defensa.
_SIMPLIFICADO_KEYS = {
    "comunicacion_apertura_formal",   # notificar los hechos imputados
    "formulacion_cargos_concretos",   # qué conducta
    "oportunidad_descargos",          # ser oído
}


# --- Salida ----------------------------------------------------------------

@dataclass(frozen=True)
class Vicio:
    garantia: str
    severidad: str
    norma: str
    detalle: str

    def to_dict(self) -> dict:
        return {"garantia": self.garantia, "severidad": self.severidad,
                "norma": self.norma, "detalle": self.detalle}


@dataclass(frozen=True)
class MissingStep:
    """Forma antigua (compat con el contrato J3 previo)."""
    step: str
    norm: str
    consequence: str

    def to_dict(self) -> dict:
        return {"step": self.step, "norm": self.norm, "consequence": self.consequence}


_CONSECUENCIA = {
    Clasificacion.CONFORME: "La sanción/decisión es válida.",
    Clasificacion.PARCIAL: "Riesgo: vicios subsanables. Rehacer la etapa viciada antes de sancionar.",
    Clasificacion.NULO: ("Sanción anulable. Si sustenta un despido, puede volverse despido "
                         "injustificado (art. 64 CST): indemnización + salarios."),
}


@dataclass(frozen=True)
class GuardianVerdict:
    clasificacion: str
    garantias_ok: int
    garantias_total: int
    vicios: list[Vicio]
    consecuencia: str
    recomendacion: str
    regimen: str                       # "completo" | "simplificado"
    # --- compat con la forma antigua de J3 ---
    nullity_alert: bool
    can_proceed: bool
    missing_steps: list[MissingStep] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "clasificacion": self.clasificacion,
            "garantias_ok": self.garantias_ok,
            "garantias_total": self.garantias_total,
            "vicios": [v.to_dict() for v in self.vicios],
            "consecuencia": self.consecuencia,
            "recomendacion": self.recomendacion,
            "regimen": self.regimen,
            "nullity_alert": self.nullity_alert,
            "can_proceed": self.can_proceed,
            "missing_steps": [m.to_dict() for m in self.missing_steps],
        }


# --- Motor -----------------------------------------------------------------

def _recomendacion(vicios: list[Vicio], clasificacion: str) -> str:
    if clasificacion == Clasificacion.CONFORME:
        return "Proceso conforme. Puede proceder con la decisión."
    if not vicios:
        return "Revisar manualmente."
    primero = vicios[0]
    return f"Subsanar «{primero.garantia}» ({primero.norma}) y, si aplica, rehacer la etapa correspondiente."


def evaluate(state: DiligenceState) -> GuardianVerdict:
    """Spec PROCESO-DISCIPLINARIO.md §8. Puro y determinista."""
    simplificado = (state.tipo_actuacion == "despido_justa_causa"
                    or state.num_trabajadores <= 10)
    aplicables = [g for g in _GARANTIAS
                  if (not simplificado) or g.key in _SIMPLIFICADO_KEYS]

    # 1) Construir vicios a partir de las garantías ausentes.
    vicios: list[Vicio] = []
    for g in aplicables:
        if not getattr(state, g.key):
            vicios.append(Vicio(g.key, Severidad.ALTA, g.norma, g.detalle_falta))

    # Acompañamiento (§4): vicio MEDIA, no cuenta como una de las garantías.
    if not state.derecho_acompanamiento_informado:
        detalle = "No se informó el derecho a estar acompañado."
        if state.worker_is_unionized:
            detalle = ("No se informó el derecho a estar acompañado por hasta dos "
                       "representantes sindicales (garantía reforzada).")
        vicios.append(Vicio("derecho_acompanamiento_informado", Severidad.MEDIA, "CN art. 29", detalle))

    total = len(aplicables)
    ok = sum(1 for g in aplicables if getattr(state, g.key))
    forces = any(g.forces_nullity for g in aplicables if not getattr(state, g.key))
    hay_media = any(v.severidad == Severidad.MEDIA for v in vicios)

    # 2) Clasificar (§8).
    if not state.falta_tipificada:
        clasificacion = Clasificacion.NULO
        vicios.insert(0, Vicio("tipicidad", Severidad.ALTA, "CST art. 114",
                               "Sanción no prevista previamente (proceso ineficaz desde el origen)."))
    elif forces:
        clasificacion = Clasificacion.NULO
    elif ok == total:
        clasificacion = Clasificacion.PARCIAL if hay_media else Clasificacion.CONFORME
    elif ok >= max(4 if not simplificado else 2, total - 3):
        clasificacion = Clasificacion.PARCIAL
    else:
        clasificacion = Clasificacion.NULO

    # 3) Compat: missing_steps (forma antigua) a partir de los vicios.
    missing = [MissingStep(v.garantia, v.norma, v.detalle) for v in vicios]

    return GuardianVerdict(
        clasificacion=clasificacion,
        garantias_ok=ok,
        garantias_total=total,
        vicios=vicios,
        consecuencia=_CONSECUENCIA[clasificacion],
        recomendacion=_recomendacion(vicios, clasificacion),
        regimen="simplificado" if simplificado else "completo",
        nullity_alert=(clasificacion == Clasificacion.NULO),
        can_proceed=(clasificacion == Clasificacion.CONFORME),
        missing_steps=missing,
    )
