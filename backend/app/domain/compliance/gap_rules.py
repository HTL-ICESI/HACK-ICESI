"""
M3 — Reglas de deteccion de ausencias normativas. NUCLEO DETERMINISTA.

Cruza un DocumentRecord contra el corpus normativo vigente y marca gaps con su cita.
Incluye la regla de reclasificacion (Ley 2466/2025) — criterio CALIFICADO del jurado.

Regla de oro: la etiqueta de gap la decide CODIGO, no el LLM.
Sin nodo en el corpus -> no se afirma el gap (lo filtra el service al resolver).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.domain.models import DocumentRecord
from app.domain.liquidation.constants import JORNADA_MAX_2026

# Indicios de subordinacion presentes en DocumentRecord (Ley 2466/2025 art. 2).
# Cada campo con valor no-None extraído del contrato cuenta como un indicio.
# Cuantos más indicios, mayor riesgo de reclasificación:
#   1. weekly_hours  → horario controlado por el contratante
#   2. role          → cargo predeterminado por el contratante
#   3. base_salary   → remuneración fija mensual (indicio de dependencia económica)
#   4. start_date    → vinculación con fecha de inicio subordinada (inicio pactado)
# David puede agregar: lugar_trabajo, exclusividad, herramientas_propias cuando M2 los extraiga.
_INDICIOS_FIELDS = ("weekly_hours", "role", "base_salary", "start_date")

LABORAL_VINCULOS = {"termino_fijo", "termino_indefinido", "obra_labor"}


@dataclass(frozen=True)
class Gap:
    gap_id: str
    issue: str
    severity: str        # alta | media | baja
    norm_id: str         # clave de busqueda en source_pack: "{norm_id}:{article}"
    article: str
    remedy_type: str     # otrosi | instruccion_nomina | acta_terminacion | contrato_corregido
    source_field: str | None = None  # campo de DocumentRecord que disparo el gap


def detect_gaps(
    record: DocumentRecord,
    *,
    reference_date: date | None = None,
) -> list[Gap]:
    """
    Aplica todas las reglas deterministas.
    Mismo record + reference_date -> mismos gaps (funcion pura).
    Sin I/O, sin LLM.
    """
    ref = reference_date or date.today()
    gaps: list[Gap] = []

    # --- Regla 1: Jornada maxima (Ley 2101/2021 art. 2, que modifica el CST art. 161) ---
    hours = record.weekly_hours.value
    if isinstance(hours, (int, float)) and hours > JORNADA_MAX_2026:
        exceso = hours - JORNADA_MAX_2026
        gaps.append(Gap(
            gap_id="g1",
            issue=(
                f"El contrato pacta una jornada de {hours} horas semanales, {exceso}h por "
                f"encima del maximo legal de {JORNADA_MAX_2026}h. La Ley 2101 de 2021 (art. 2, "
                f"que modifico el art. 161 del CST) redujo la jornada ordinaria a 42 horas, "
                f"con implementacion gradual que culmina en 2026. Una jornada superior expone "
                f"a la empresa al pago de horas extra retroactivas y a reclamaciones; debe "
                f"corregirse mediante otrosi que ajuste la jornada al limite vigente."
            ),
            severity="alta",
            norm_id="Ley 2101/2021",
            article="art. 2",
            remedy_type="otrosi",
            source_field="weekly_hours",
        ))

    # --- Regla 2: Reclasificacion laboral (Ley 2466/2025 art. 5) ---
    # Cuenta indicios de subordinacion extraidos del record.
    # Severidad escalonada: 0-1 indicios → media (alerta), 2+ → alta (reclasificacion probable).
    # El sistema SIEMPRE genera el gap para prestacion_servicios (la ley presume la relacion
    # laboral si se demuestran indicios); la severidad sube con el numero de indicios.
    vinculo = record.vinculo_type.value
    if vinculo == "prestacion_servicios":
        indicios = sum(
            1 for f in _INDICIOS_FIELDS
            if getattr(record, f, None) is not None
            and getattr(record, f).value is not None
        )
        # Severidad: con 2+ indicios el riesgo es ALTO (reclasificación probable)
        severity_g2 = "alta" if indicios >= 2 else "media"
        riesgo_label = (
            "ALTO — reclasificacion probable" if indicios >= 2
            else "MEDIO — verificar subordinacion"
        )
        indicios_txt = ", ".join(_INDICIOS_FIELDS[:indicios]) if indicios else "ninguno detectado"
        gaps.append(Gap(
            gap_id="g2",
            issue=(
                f"El contrato es de prestacion de servicios, pero se detectaron {indicios} "
                f"indicio(s) de subordinacion ({indicios_txt}). El art. 23 del CST exige "
                f"subordinacion para que exista contrato de trabajo, y el art. 24 PRESUME la "
                f"relacion laboral cuando hay prestacion personal del servicio; la Ley 2466/2025 "
                f"refuerza este criterio para el trabajo mediado por plataformas o algoritmos. "
                f"Riesgo {riesgo_label}: si un juez confirma la subordinacion, el contrato se "
                f"reclasifica como laboral con pago retroactivo de prestaciones y aportes. Accion: "
                f"revisar las clausulas y emitir un contrato corregido o formalizar el vinculo."
            ),
            severity=severity_g2,
            norm_id="CST",
            article="art. 24",
            remedy_type="contrato_corregido",
            source_field="vinculo_type",
        ))

    # --- Regla 3: Vacaciones acumuladas > 1 anio (CST art. 186) ---
    start_val = record.start_date.value
    if start_val and isinstance(start_val, str):
        try:
            start_dt = date.fromisoformat(start_val)
            end_val = record.end_date.value
            end_dt = date.fromisoformat(end_val) if (end_val and isinstance(end_val, str)) else ref
            if (end_dt - start_dt).days > 365:
                anios = (end_dt - start_dt).days // 365
                gaps.append(Gap(
                    gap_id="g3",
                    issue=(
                        f"El trabajador acumula mas de {anios} anio(s) de servicio sin registro de "
                        f"vacaciones disfrutadas. El art. 186 del CST otorga 15 dias habiles de "
                        f"vacaciones remuneradas por cada anio trabajado. Las vacaciones no tomadas "
                        f"se acumulan y deben compensarse o programarse; dejarlas vencer genera un "
                        f"pasivo creciente y riesgo de reclamacion. Accion: programar el disfrute o "
                        f"instruir a nomina la compensacion correspondiente."
                    ),
                    severity="media",
                    norm_id="CST",
                    article="art. 186",
                    remedy_type="instruccion_nomina",
                    source_field="start_date",
                ))
        except ValueError:
            pass  # fechas malformadas -> no se afirma el gap

    # termination_confirmed: señal de M2 — True=acta encontrada, False=no encontrada, None=no buscado
    tc = record.termination_confirmed
    tc_confirmed = tc is not None and tc.value is True

    # --- Regla 4: Vencimiento contrato a termino fijo (CST art. 46) ---
    # Cubre dos casos: (a) vence pronto, (b) ya vencio sin documentar renovacion/terminacion
    # Suprimida si termination_confirmed=True (el contrato se cerro correctamente).
    if vinculo == "termino_fijo" and not tc_confirmed:
        end_val = record.end_date.value
        if end_val and isinstance(end_val, str):
            try:
                end_dt = date.fromisoformat(end_val)
                days_left = (end_dt - ref).days
                if days_left < 0:
                    gaps.append(Gap(
                        gap_id="g4",
                        issue=(
                            f"El contrato a termino fijo esta VENCIDO hace {abs(days_left)} dias sin "
                            f"registro de renovacion ni acta de terminacion. El art. 46 del CST exige "
                            f"preaviso escrito de no prorroga con 30 dias de antelacion; sin el, el "
                            f"contrato se entiende RENOVADO automaticamente por un periodo igual. "
                            f"Seguir sin documentar genera incertidumbre sobre la vigencia y posible "
                            f"indemnizacion. Accion: formalizar la renovacion o el acta de terminacion."
                        ),
                        severity="alta",
                        norm_id="CST",
                        article="art. 46",
                        remedy_type="acta_terminacion",
                        source_field="end_date",
                    ))
                elif days_left <= 90:
                    severity = "alta" if days_left <= 30 else "media"
                    gaps.append(Gap(
                        gap_id="g4",
                        issue=(
                            f"El contrato a termino fijo vence en {days_left} dias. El art. 46 del CST "
                            f"obliga a dar preaviso escrito de no prorroga con minimo 30 dias de "
                            f"antelacion; de lo contrario el contrato se renueva automaticamente por "
                            f"un periodo igual al pactado. Dejar pasar el plazo sin decision puede "
                            f"comprometer a la empresa a un nuevo periodo no deseado. Accion: decidir "
                            f"renovacion o emitir el preaviso de no prorroga a tiempo."
                        ),
                        severity=severity,
                        norm_id="CST",
                        article="art. 46",
                        remedy_type="acta_terminacion",
                        source_field="end_date",
                    ))
            except ValueError:
                pass

    # --- Regla 5: Mora comprobada en seguridad social (Ley 100/1993 art. 22) ---
    # Requiere evidencia explicita de mora en los datos operativos de nomina (pago_ss_mora).
    # Sin ese dato -> no se afirma el gap. Emitirlo sin evidencia genera ruido en todo
    # contrato laboral activo, lo que degrada la precision del analisis.
    mora = record.pago_ss_mora
    if mora is not None and mora.value is True and not tc_confirmed:
        gaps.append(Gap(
            gap_id="g5",
            issue=(
                "Se detecto mora en el pago de aportes a la seguridad social. El art. 22 de la "
                "Ley 100 de 1993 obliga al empleador a afiliar y cotizar oportunamente a salud, "
                "pension y riesgos; la mora genera intereses, sanciones de la UGPP y, si ocurre un "
                "siniestro, traslada el costo de la prestacion al empleador. Es una contingencia de "
                "alto impacto economico y reputacional. Accion: regularizar los aportes en mora de "
                "inmediato e instruir a nomina el pago con intereses."
            ),
            severity="alta",
            norm_id="Ley 100/1993",
            article="art. 22",
            remedy_type="instruccion_nomina",
            source_field="pago_ss_mora",
        ))

    # TODO(futuro — necesita datos operativos de nomina):
    # Regla 60-40: base de cotizacion de bonificaciones no salariales (CST art. 128).
    # Si bonificaciones_no_salariales > 40% del salario total -> gap de compliance.
    # NO implementar hasta que M2 extraiga montos de bonificacion del contrato o RIT,
    # o hasta que la BD de nomina provea los datos de causacion. Ver M4 caso gold David.
    # Norma a agregar al corpus: "CST:art. 128" cuando David valide el umbral.

    return gaps
