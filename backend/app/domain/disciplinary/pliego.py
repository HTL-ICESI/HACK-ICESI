"""
J4 — Generador de documentos del proceso disciplinario. NÚCLEO DETERMINISTA.

Produce los tres documentos que exige el reto (elaboración de pliegos de cargos +
debido proceso): la **citación a descargos**, el **pliego de cargos** y la
**decisión motivada**. Implementa las etapas de `PROCESO-DISCIPLINARIO.md` (§4, §6).

Patrón anti-alucinación: TODO el contenido jurídico —los cargos imputados, las
normas citadas, las fechas, el término de defensa— es determinista, armado por
código a partir del caso (`DisciplinaryCase`) y del veredicto del guardián. El LLM
NO entra aquí: solo el servicio puede, opcionalmente, ampliar la prosa del relato
sobre este esqueleto (degradación honesta: sin LLM el esqueleto ya es válido).

VETO (§8): la **decisión sancionatoria** no se emite si el guardián clasifica el
proceso como NULO. La citación y el pliego sí se generan siempre: son las
herramientas que PREVIENEN la nulidad (fijan el término de 5 días, concretan los
cargos), por lo que el sistema debe poder producirlas desde el inicio.

Puro: stdlib únicamente, sin I/O, sin LLM, sin importar nada de adapters/services.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from app.domain.disciplinary.guardian import (
    Clasificacion,
    DiligenceState,
    GuardianVerdict,
    evaluate,
)

TERMINO_MINIMO_HABILES = 5  # art. 115 CST (Ley 2466/2025) + Circular 0048/2026


# --- Entrada ----------------------------------------------------------------

@dataclass(frozen=True)
class Cargo:
    """Un cargo concreto: la conducta imputada con sus hechos. Nunca genérico
    (la genericidad la veta el guardián, garantía G2)."""
    conducta: str            # qué hizo (la falta)
    hechos: str              # cuándo/cómo/dónde — hechos concretos
    norma_infringida: str    # reglamento/artículo/cláusula que tipifica la falta


@dataclass(frozen=True)
class DisciplinaryCase:
    """Caso disciplinario: los datos duros del proceso. Lo que el código cita
    en los documentos sale de aquí, nunca se inventa."""
    empresa: str
    nit_empresa: str
    trabajador: str
    cedula_trabajador: str
    cargo_trabajador: str                       # el rol/puesto, no la imputación
    cargos: list[Cargo]
    pruebas: list[str] = field(default_factory=list)
    fecha_citacion: date | None = None
    fecha_diligencia: date | None = None
    dias_habiles_termino: int = TERMINO_MINIMO_HABILES
    lugar_diligencia: str = "las instalaciones de la empresa"
    hora_diligencia: str = "9:00 a.m."
    instructor: str = "el empleador"
    cargo_instructor: str = "Representante Legal"
    ciudad: str = "Cali"
    # Para la decisión motivada
    tipo_sancion: str = ""                       # "amonestacion" | "suspension" | "multa" | "terminacion"
    dias_suspension: int = 0
    motivacion: str = ""                         # razones de la decisión (in dubio pro disciplinado)


# --- Salida -----------------------------------------------------------------

@dataclass(frozen=True)
class DisciplinaryDocument:
    tipo: str                  # "citacion_descargos" | "pliego_de_cargos" | "decision_motivada"
    titulo: str
    cuerpo: str                # markdown determinista (el esqueleto)
    citas: list[str]           # normas invocadas (trazabilidad)
    bloqueado: bool = False    # True si el VETO impidió emitirlo
    motivo_bloqueo: str = ""

    def to_dict(self) -> dict:
        return {
            "tipo": self.tipo, "titulo": self.titulo, "cuerpo": self.cuerpo,
            "citas": list(self.citas), "bloqueado": self.bloqueado,
            "motivo_bloqueo": self.motivo_bloqueo,
        }


def _fecha(d: date | None) -> str:
    return d.isoformat() if d else "__________"


def _cargos_md(case: DisciplinaryCase) -> str:
    if not case.cargos:
        return "_(sin cargos concretos — el proceso no puede iniciar sin imputación, art. 115 CST)_"
    return "\n".join(
        f"{i}. **{c.conducta}.** {c.hechos} "
        f"(presunta infracción a {c.norma_infringida})."
        for i, c in enumerate(case.cargos, 1)
    )


def _pruebas_md(case: DisciplinaryCase) -> str:
    if not case.pruebas:
        return "_(no se relacionaron pruebas — su falta vicia la contradicción, garantía G3)_"
    return "\n".join(f"- {p}" for p in case.pruebas)


# --- Documento 1: Citación a descargos (§4) ---------------------------------

def build_citacion(case: DisciplinaryCase) -> DisciplinaryDocument:
    citas = ["CN art. 29", "CST art. 115 (Ley 2466/2025)", "Circular 0048/2026 MinTrabajo"]
    aviso_termino = ""
    if case.dias_habiles_termino < TERMINO_MINIMO_HABILES:
        aviso_termino = (
            f"\n\n> ⚠️ **Advertencia del sistema:** el término fijado "
            f"({case.dias_habiles_termino} días hábiles) es inferior al mínimo de "
            f"{TERMINO_MINIMO_HABILES} días hábiles (art. 115 CST). Corríjalo antes de "
            f"notificar: de lo contrario la sanción será anulable."
        )
    cuerpo = f"""## CITACIÓN A DILIGENCIA DE DESCARGOS

**{case.empresa}** (NIT {case.nit_empresa})
{case.ciudad}, {_fecha(case.fecha_citacion)}

Señor(a) **{case.trabajador}**
C.C. {case.cedula_trabajador} — {case.cargo_trabajador}

En cumplimiento del debido proceso (art. 29 de la Constitución Política y art. 115
del Código Sustantivo del Trabajo, modificado por la Ley 2466 de 2025), la empresa
le **CITA** a rendir descargos respecto de los siguientes hechos:

{_cargos_md(case)}

**Pruebas que sustentan los cargos** (se trasladan con esta citación para su
contradicción):
{_pruebas_md(case)}

**Diligencia:** {_fecha(case.fecha_diligencia)} a las {case.hora_diligencia}, en
{case.lugar_diligencia}. Usted dispone de un término de **{case.dias_habiles_termino}
días hábiles** para preparar su defensa.

Se le informa su derecho a **comparecer acompañado** de dos (2) representantes del
sindicato o de una persona de su confianza (art. 29 CN), y a controvertir las
pruebas. La inasistencia injustificada se entenderá como renuncia a pronunciarse y
el proceso continuará con las pruebas obrantes.{aviso_termino}

Atentamente,

**{case.instructor}**
{case.cargo_instructor} — {case.empresa}
"""
    return DisciplinaryDocument("citacion_descargos", "Citación a diligencia de descargos",
                                cuerpo, citas)


# --- Documento 2: Pliego de cargos (§4 G2) ----------------------------------

def build_pliego(case: DisciplinaryCase) -> DisciplinaryDocument:
    citas = ["CST art. 114 (tipicidad)", "CST art. 115 (Ley 2466/2025)"]
    cuerpo = f"""## PLIEGO DE CARGOS

**{case.empresa}** (NIT {case.nit_empresa}) — {case.ciudad}, {_fecha(case.fecha_citacion)}
Trabajador: **{case.trabajador}**, C.C. {case.cedula_trabajador} ({case.cargo_trabajador})

La empresa **FORMULA** contra el trabajador los siguientes cargos, con indicación
concreta de los hechos, conductas u omisiones imputadas (art. 115 CST), advirtiendo
que toda sanción exige que la falta esté previamente tipificada (art. 114 CST):

{_cargos_md(case)}

**Material probatorio trasladado:**
{_pruebas_md(case)}

El trabajador podrá pronunciarse sobre cada cargo, aportar y solicitar pruebas, y
ejercer su derecho de defensa en la diligencia de descargos señalada, dentro del
término concedido.

**{case.instructor}** — {case.cargo_instructor}
"""
    return DisciplinaryDocument("pliego_de_cargos", "Pliego de cargos", cuerpo, citas)


# --- Documento 3: Decisión motivada (§6) — sujeta a VETO --------------------

_SANCION_LABEL = {
    "amonestacion": "amonestación escrita",
    "suspension": "suspensión del contrato de trabajo",
    "multa": "multa",
    "terminacion": "terminación del contrato de trabajo",
}


def build_decision(case: DisciplinaryCase, verdict: GuardianVerdict) -> DisciplinaryDocument:
    citas = ["CST art. 115 num. 5", "CST art. 113 (proporcionalidad)"]
    # VETO (§8): si el proceso es NULO, no se emite la decisión sancionatoria.
    if verdict.clasificacion == Clasificacion.NULO:
        vicios = "; ".join(f"{v.garantia} ({v.norma})" for v in verdict.vicios) or "vicios del debido proceso"
        return DisciplinaryDocument(
            "decision_motivada", "Decisión motivada (BLOQUEADA)", "",
            citas, bloqueado=True,
            motivo_bloqueo=(
                f"Decisión sancionatoria bloqueada: el proceso es NULO. {vicios}. "
                f"Sancionar sobre esta base expone a reintegro/indemnización (art. 64 CST). "
                f"{verdict.recomendacion}"
            ),
        )

    aviso = ""
    if verdict.clasificacion == Clasificacion.PARCIAL:
        aviso = (
            "\n\n> ⚠️ **Advertencia:** el proceso presenta vicios subsanables "
            f"({len(verdict.vicios)}). Se recomienda corregirlos antes de notificar la "
            f"decisión. {verdict.recomendacion}"
        )
    sancion = _SANCION_LABEL.get(case.tipo_sancion, "la sanción que en derecho corresponda")
    detalle_susp = (f" por **{case.dias_suspension} días**" if case.tipo_sancion == "suspension"
                    and case.dias_suspension else "")
    motivacion = case.motivacion or (
        "Valoradas las pruebas y los descargos, se encuentran probados los hechos "
        "imputados y su tipicidad como falta sancionable."
    )
    cuerpo = f"""## DECISIÓN MOTIVADA

**{case.empresa}** (NIT {case.nit_empresa}) — {case.ciudad}, {_fecha(case.fecha_diligencia)}
Trabajador: **{case.trabajador}**, C.C. {case.cedula_trabajador}

**Hechos y cargos:**
{_cargos_md(case)}

**Motivación** (art. 115 num. 5 CST): {motivacion}

**Decisión:** la empresa resuelve imponer **{sancion}**{detalle_susp}, en proporción
a la gravedad de la falta (art. 113 CST).

**Recursos:** contra esta decisión procede el derecho de impugnación (doble
instancia, Ley 2466/2025), que deberá resolver un superior distinto de quien sancionó.

Debido proceso verificado por el guardián: **{verdict.clasificacion}**
({verdict.garantias_ok}/{verdict.garantias_total} garantías).{aviso}

**{case.instructor}** — {case.cargo_instructor}
"""
    return DisciplinaryDocument("decision_motivada", "Decisión motivada", cuerpo, citas)


# --- Orquestación determinista ----------------------------------------------

def build_documents(case: DisciplinaryCase, state: DiligenceState | None = None
                    ) -> tuple[GuardianVerdict, list[DisciplinaryDocument]]:
    """Genera los 3 documentos. La citación y el pliego siempre; la decisión queda
    sujeta al VETO del guardián. Si no se pasa `state`, se evalúa uno neutro para
    la decisión (que entonces se bloquea por garantías ausentes)."""
    verdict = evaluate(state) if state is not None else evaluate(DiligenceState())
    docs = [
        build_citacion(case),
        build_pliego(case),
        build_decision(case, verdict),
    ]
    return verdict, docs
