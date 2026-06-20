"""
J4 — Generador de documentos disciplinarios, probado como código puro.
Contrato: los cargos, las normas y las fechas salen del caso (deterministas); la
decisión sancionatoria queda bloqueada si el guardián clasifica NULO.
"""
from app.domain.disciplinary.guardian import DiligenceState
from app.domain.disciplinary.pliego import (
    Cargo, DisciplinaryCase, build_citacion, build_pliego, build_documents,
)


def _case(**kw) -> DisciplinaryCase:
    base = dict(
        empresa="ACME S.A.S.", nit_empresa="900.123.456-7",
        trabajador="JUAN PEREZ", cedula_trabajador="79.000.111", cargo_trabajador="Operario",
        cargos=[Cargo("Inasistencia injustificada",
                      "Faltó los días 12, 13 y 14 de mayo de 2026 sin justificación.",
                      "RIT art. 45")],
        pruebas=["Registro biométrico de acceso"],
    )
    base.update(kw)
    return DisciplinaryCase(**base)


def _full_ok() -> DiligenceState:
    return DiligenceState(
        falta_tipificada=True,
        comunicacion_apertura_formal=True, formulacion_cargos_concretos=True,
        traslado_pruebas=True, termino_defensa_minimo=True,
        oportunidad_descargos=True, decision_motivada=True, derecho_impugnacion=True,
    )


def test_citacion_incluye_cargos_concretos_y_normas():
    doc = build_citacion(_case())
    assert "Inasistencia injustificada" in doc.cuerpo
    assert "12, 13 y 14 de mayo de 2026" in doc.cuerpo   # los hechos concretos, no inventados
    assert "RIT art. 45" in doc.cuerpo
    assert any("115" in c for c in doc.citas)


def test_termino_menor_a_5_dias_dispara_advertencia_en_citacion():
    doc = build_citacion(_case(dias_habiles_termino=2))
    assert "inferior al mínimo" in doc.cuerpo
    assert "anulable" in doc.cuerpo


def test_pliego_no_inventa_cargos_si_no_hay():
    doc = build_pliego(_case(cargos=[]))
    assert "sin cargos concretos" in doc.cuerpo   # honesto, no alucina una imputación


def test_decision_bloqueada_si_proceso_nulo():
    nulo = DiligenceState(falta_tipificada=False)   # NULO de origen
    verdict, docs = build_documents(_case(), nulo)
    decision = next(d for d in docs if d.tipo == "decision_motivada")
    assert decision.bloqueado is True
    assert decision.cuerpo == ""
    assert "anulable" in decision.motivo_bloqueo or "NULO" in decision.motivo_bloqueo


def test_decision_se_emite_si_conforme():
    verdict, docs = build_documents(_case(tipo_sancion="suspension", dias_suspension=3), _full_ok())
    decision = next(d for d in docs if d.tipo == "decision_motivada")
    assert decision.bloqueado is False
    assert "suspensión" in decision.cuerpo
    assert "3 días" in decision.cuerpo
    assert "CONFORME" in decision.cuerpo


def test_es_determinista():
    a = build_documents(_case(), _full_ok())
    b = build_documents(_case(), _full_ok())
    assert [d.cuerpo for d in a[1]] == [d.cuerpo for d in b[1]]
