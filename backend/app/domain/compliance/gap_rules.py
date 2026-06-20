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

    # --- Regla 1: Jornada maxima (Ley 2101/2021 art. 3) ---
    hours = record.weekly_hours.value
    if isinstance(hours, (int, float)) and hours > JORNADA_MAX_2026:
        gaps.append(Gap(
            gap_id="g1",
            issue=f"Jornada de {hours}h excede el maximo legal de {JORNADA_MAX_2026}h (Ley 2101/2021, vigor pleno 2026)",
            severity="alta",
            norm_id="Ley 2101/2021",
            article="art. 3",
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
        gaps.append(Gap(
            gap_id="g2",
            issue=(
                f"Contrato de prestacion de servicios con {indicios} indicio(s) de subordinacion "
                f"({', '.join(_INDICIOS_FIELDS[:indicios] if indicios else ['ninguno detectado'])}). "
                f"Riesgo {riesgo_label} (Ley 2466/2025 art. 5). "
                f"Accion: revisar clausulas y emitir contrato corregido si se confirma subordinacion."
            ),
            severity=severity_g2,
            norm_id="Ley 2466/2025",
            article="art. 5",
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
                gaps.append(Gap(
                    gap_id="g3",
                    issue="Periodo laboral superior a 1 anio sin evidencia de vacaciones tomadas (CST art. 186)",
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
                            f"Contrato a termino fijo VENCIDO hace {abs(days_left)} dias "
                            f"sin registro de renovacion ni acta de terminacion (CST art. 46)"
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
                            f"Contrato a termino fijo vence en {days_left} dias — "
                            f"requiere renovacion o preaviso de no prorroga (CST art. 46)"
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
            issue="Mora comprobada en aportes a seguridad social — regularizar de inmediato (Ley 100/1993 art. 22)",
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
