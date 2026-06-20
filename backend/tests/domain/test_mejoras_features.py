"""
Tests de las 4 mejoras (rama feat/mejoras-documento-alertas-liquidacion).

F1 — Ingesta Excel (.xlsx): el adaptador extrae texto de hojas tabulares.
F2 — Alerta liquidacion_pendiente: nuevo tipo en M6, severidad escalonada.
F3 — Export Excel liquidación: _build_xlsx genera bytes válidos con todos los campos.
F4 — Reclasificación g2 mejorada: severidad alta con ≥2 indicios + mensaje enriquecido.
"""
from __future__ import annotations

import io
from datetime import date, timedelta

import pytest

REF = date(2026, 6, 18)


# ─────────────────────────────────────────────────────────────────────────────
# F1 — Ingesta Excel
# ─────────────────────────────────────────────────────────────────────────────

class TestIngestaExcel:
    """Valida que .xlsx se convierte a texto estructurado (degradación honesta)."""

    @pytest.fixture
    def xlsx_bytes(self):
        """Genera un .xlsx mínimo con openpyxl (solo si openpyxl instalado)."""
        openpyxl = pytest.importorskip("openpyxl")
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Nómina"
        ws.append(["Nombre", "Cargo", "Salario"])
        ws.append(["Juan García", "Asesor", 2_500_000])
        ws.append(["María Ospina", "Coordinadora", 3_800_000])
        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    def test_xlsx_extrae_encabezado_y_filas(self, xlsx_bytes):
        from app.adapters.ocr.ingest_pdf import ingest
        res = ingest("nomina_01", xlsx_bytes, "nomina.xlsx")
        assert res.status == "digital"
        assert res.confidence == 1.0
        assert "Nombre" in res.text
        assert "Juan García" in res.text
        assert "2500000" in res.text or "2.500.000" in res.text or "2500000.0" in res.text

    def test_xlsx_incluye_nombre_de_hoja(self, xlsx_bytes):
        from app.adapters.ocr.ingest_pdf import ingest
        res = ingest("nomina_02", xlsx_bytes, "nomina.xlsx")
        assert "[Hoja: Nómina]" in res.text or "Nómina" in res.text

    def test_xlsx_corrupto_retorna_needs_human(self):
        from app.adapters.ocr.ingest_pdf import ingest
        res = ingest("bad_xlsx", b"no soy un xlsx valido", "contrato.xlsx")
        assert res.status == "needs_human"
        assert res.text == ""

    def test_xls_extension_no_lanza(self):
        """El router acepta .xls como extensión válida (no ValueError)."""
        from app.adapters.ocr.ingest_pdf import ingest
        # Los bytes no son .xls real → needs_human, no ValueError
        res = ingest("old_excel", b"bytes_basura", "datos.xls")
        assert res.status == "needs_human"

    def test_extensiones_nuevas_en_supported_router(self):
        """SUPPORTED en el router de ingest incluye .xlsx y .xls."""
        from app.api.routers.ingest import SUPPORTED
        assert ".xlsx" in SUPPORTED
        assert ".xls" in SUPPORTED

    def test_batch_exts_incluyen_xlsx(self):
        """_DOC_EXTS en batch.py incluye .xlsx y .xls."""
        from app.api.routers.batch import _DOC_EXTS
        assert ".xlsx" in _DOC_EXTS
        assert ".xls" in _DOC_EXTS


# ─────────────────────────────────────────────────────────────────────────────
# F2 — Alerta liquidacion_pendiente
# ─────────────────────────────────────────────────────────────────────────────

class TestAlertaLiquidacionPendiente:
    """El motor de alertas M6 genera alerta cuando hay liquidación sin pagar."""

    def _ctx(self, dias_mora: int = 10, monto: float = 1_500_000.0):
        from app.domain.exposure.alerts import ContractContext
        return ContractContext(
            vinculo_type="termino_fijo",
            start_date="2025-01-01",
            end_date="2026-01-01",
            liquidacion_pendiente=True,
            liquidacion_monto_cop=monto,
            liquidacion_dias_mora=dias_mora,
        )

    def test_genera_alerta_tipo_liquidacion_pendiente(self):
        from app.domain.exposure.alerts import compute_alerts
        alerts = compute_alerts([self._ctx()], reference_date=REF)
        a = next((a for a in alerts if a.type == "liquidacion_pendiente"), None)
        assert a is not None

    def test_menos_de_30_dias_mora_es_media(self):
        from app.domain.exposure.alerts import compute_alerts
        alerts = compute_alerts([self._ctx(dias_mora=15)], reference_date=REF)
        a = next(a for a in alerts if a.type == "liquidacion_pendiente")
        assert a.severity == "media"

    def test_mas_de_30_dias_mora_es_alta(self):
        from app.domain.exposure.alerts import compute_alerts
        alerts = compute_alerts([self._ctx(dias_mora=45)], reference_date=REF)
        a = next(a for a in alerts if a.type == "liquidacion_pendiente")
        assert a.severity == "alta"

    def test_monto_en_amount_cop(self):
        from app.domain.exposure.alerts import compute_alerts
        alerts = compute_alerts([self._ctx(monto=2_000_000.0)], reference_date=REF)
        a = next(a for a in alerts if a.type == "liquidacion_pendiente")
        assert a.amount == {"value": 2_000_000.0, "currency": "COP"}

    def test_sin_flag_no_genera_alerta(self):
        from app.domain.exposure.alerts import ContractContext, compute_alerts
        ctx = ContractContext(
            vinculo_type="termino_fijo",
            start_date="2025-01-01",
            end_date="2026-01-01",
            liquidacion_pendiente=False,
        )
        alerts = compute_alerts([ctx], reference_date=REF)
        assert all(a.type != "liquidacion_pendiente" for a in alerts)

    def test_dias_mora_en_alerta(self):
        from app.domain.exposure.alerts import compute_alerts
        alerts = compute_alerts([self._ctx(dias_mora=60)], reference_date=REF)
        a = next(a for a in alerts if a.type == "liquidacion_pendiente")
        assert a.dias_mora == 60

    def test_to_dict_incluye_dias_mora(self):
        from app.domain.exposure.alerts import compute_alerts
        alerts = compute_alerts([self._ctx(dias_mora=20)], reference_date=REF)
        a = next(a for a in alerts if a.type == "liquidacion_pendiente")
        d = a.to_dict()
        assert d["dias_mora"] == 20

    def test_monto_cero_no_incluye_amount(self):
        from app.domain.exposure.alerts import compute_alerts
        alerts = compute_alerts([self._ctx(monto=0.0, dias_mora=5)], reference_date=REF)
        a = next(a for a in alerts if a.type == "liquidacion_pendiente")
        # amount es None cuando monto=0 → omitido en to_dict
        assert "amount" not in a.to_dict()


# ─────────────────────────────────────────────────────────────────────────────
# F3 — Export Excel liquidación
# ─────────────────────────────────────────────────────────────────────────────

class TestExportExcelLiquidacion:
    """_build_xlsx genera un .xlsx válido con todos los campos de LiquidationResult."""

    @pytest.fixture
    def req_and_result(self):
        from app.api.routers.liquidation import LiquidationRequest
        from app.domain.liquidation.engine import liquidate, LiquidationInput
        req = LiquidationRequest(
            doc_id="jose_ospino",
            monthly_salary=2_000_000.0,
            days_worked=180,
            vinculo_type="termino_fijo",
            auxilio_transporte=162_000.0,
            termination_cause="sin_justa_causa",
            months_remaining_fixed=3,
            antiguedad_anios=1.0,
        )
        inp = LiquidationInput(
            salario_basico=req.monthly_salary,
            days_worked=req.days_worked,
            vinculo_type=req.vinculo_type,
            termination_cause=req.termination_cause,
            auxilio_transporte=req.auxilio_transporte,
            months_remaining_fixed=req.months_remaining_fixed,
            antiguedad_anios=req.antiguedad_anios,
        )
        result = liquidate(inp)
        return req, result

    def test_genera_bytes_xlsx_validos(self, req_and_result):
        openpyxl = pytest.importorskip("openpyxl")
        from app.api.routers.liquidation import _build_xlsx
        req, result = req_and_result
        data = _build_xlsx(req, result)
        assert isinstance(data, bytes)
        assert len(data) > 0
        # openpyxl puede leerlo sin error
        wb = openpyxl.load_workbook(io.BytesIO(data))
        assert wb is not None

    def test_xlsx_tiene_hoja_liquidacion(self, req_and_result):
        openpyxl = pytest.importorskip("openpyxl")
        from app.api.routers.liquidation import _build_xlsx
        req, result = req_and_result
        wb = openpyxl.load_workbook(io.BytesIO(_build_xlsx(req, result)))
        assert "Liquidación HG" in wb.sheetnames

    def _all_text(self, ws) -> str:
        """Extrae todo el texto de la hoja en mayúsculas (case-insensitive)."""
        return " ".join(
            str(val).upper()
            for row in ws.iter_rows(values_only=True)
            for val in row
            if val is not None
        )

    def test_xlsx_contiene_conceptos_prestaciones(self, req_and_result):
        openpyxl = pytest.importorskip("openpyxl")
        from app.api.routers.liquidation import _build_xlsx
        req, result = req_and_result
        wb = openpyxl.load_workbook(io.BytesIO(_build_xlsx(req, result)))
        ws = wb["Liquidación HG"]
        textos = self._all_text(ws)
        for concepto in ["CESANT", "PRIMA", "VACACIONES", "TOTAL"]:
            assert concepto in textos, f"Falta '{concepto}' en el Excel generado"

    def test_xlsx_incluye_indemnizacion_cuando_aplica(self, req_and_result):
        openpyxl = pytest.importorskip("openpyxl")
        from app.api.routers.liquidation import _build_xlsx
        req, result = req_and_result
        assert result.indemnizacion > 0, "El caso de prueba debería tener indemnización"
        wb = openpyxl.load_workbook(io.BytesIO(_build_xlsx(req, result)))
        ws = wb["Liquidación HG"]
        textos = self._all_text(ws)
        assert "INDEMNIZACI" in textos

    def test_cop_formatter_formato_colombiano(self):
        from app.api.routers.liquidation import _cop
        assert _cop(1_500_000.0) == "$ 1.500.000"
        assert _cop(0.0) == "$ 0"
        assert _cop(162_000.0) == "$ 162.000"


# ─────────────────────────────────────────────────────────────────────────────
# F4 — Reclasificación g2 mejorada
# ─────────────────────────────────────────────────────────────────────────────

class TestReclasificacionG2Mejorada:
    """G2 tiene severidad alta con ≥2 indicios y mensaje enriquecido."""

    def _record(self, with_hours=True, with_role=True, with_salary=True, with_start=True):
        """Construye un DocumentRecord de prestación de servicios con indicios controlados."""
        from app.domain.models import DocumentRecord, Field
        return DocumentRecord(
            doc_id="test_g2",
            vinculo_type=Field(value="prestacion_servicios", confidence=1.0, sources=[]),
            employer=Field(value="Empresa XYZ", confidence=1.0, sources=[]),
            empleado_nombre=Field(value="Pedro Ruiz", confidence=1.0, sources=[]),
            empleado_documento=Field(value="12345678", confidence=1.0, sources=[]),
            role=Field(value="Consultor" if with_role else None, confidence=1.0, sources=[]),
            base_salary=Field(value=3_500_000.0 if with_salary else None, confidence=1.0, sources=[]),
            auxilio_transporte=Field(value=None, confidence=0.0, sources=[]),
            salario_variable=Field(value=False, confidence=1.0, sources=[]),
            weekly_hours=Field(value=40 if with_hours else None, confidence=1.0, sources=[]),
            start_date=Field(value="2025-01-01" if with_start else None, confidence=1.0, sources=[]),
            end_date=Field(value=None, confidence=0.0, sources=[]),
        )

    def test_cero_indicios_severidad_media(self):
        from app.domain.compliance.gap_rules import detect_gaps
        rec = self._record(with_hours=False, with_role=False, with_salary=False, with_start=False)
        gaps = detect_gaps(rec, reference_date=REF)
        g2 = next((g for g in gaps if g.gap_id == "g2"), None)
        assert g2 is not None
        assert g2.severity == "media"

    def test_un_indicio_severidad_media(self):
        from app.domain.compliance.gap_rules import detect_gaps
        rec = self._record(with_hours=True, with_role=False, with_salary=False, with_start=False)
        gaps = detect_gaps(rec, reference_date=REF)
        g2 = next(g for g in gaps if g.gap_id == "g2")
        assert g2.severity == "media"

    def test_dos_indicios_severidad_alta(self):
        from app.domain.compliance.gap_rules import detect_gaps
        rec = self._record(with_hours=True, with_role=True, with_salary=False, with_start=False)
        gaps = detect_gaps(rec, reference_date=REF)
        g2 = next(g for g in gaps if g.gap_id == "g2")
        assert g2.severity == "alta"

    def test_cuatro_indicios_severidad_alta(self):
        from app.domain.compliance.gap_rules import detect_gaps
        rec = self._record(with_hours=True, with_role=True, with_salary=True, with_start=True)
        gaps = detect_gaps(rec, reference_date=REF)
        g2 = next(g for g in gaps if g.gap_id == "g2")
        assert g2.severity == "alta"

    def test_remedy_type_es_contrato_corregido(self):
        from app.domain.compliance.gap_rules import detect_gaps
        rec = self._record()
        gaps = detect_gaps(rec, reference_date=REF)
        g2 = next(g for g in gaps if g.gap_id == "g2")
        assert g2.remedy_type == "contrato_corregido"

    def test_issue_menciona_numero_de_indicios(self):
        from app.domain.compliance.gap_rules import detect_gaps
        rec = self._record(with_hours=True, with_role=True, with_salary=False, with_start=False)
        gaps = detect_gaps(rec, reference_date=REF)
        g2 = next(g for g in gaps if g.gap_id == "g2")
        assert "2" in g2.issue

    def test_issue_menciona_ley_2466(self):
        from app.domain.compliance.gap_rules import detect_gaps
        rec = self._record()
        gaps = detect_gaps(rec, reference_date=REF)
        g2 = next(g for g in gaps if g.gap_id == "g2")
        assert "2466" in g2.issue

    def test_vinculo_laboral_no_genera_g2(self):
        """Contratos laborales (término fijo, indefinido) nunca generan g2."""
        from app.domain.models import DocumentRecord, Field
        from app.domain.compliance.gap_rules import detect_gaps
        rec = DocumentRecord(
            doc_id="test_laboral",
            vinculo_type=Field(value="termino_indefinido", confidence=1.0, sources=[]),
            employer=Field(value="Empresa", confidence=1.0, sources=[]),
            empleado_nombre=Field(value="Ana", confidence=1.0, sources=[]),
            empleado_documento=Field(value="999", confidence=1.0, sources=[]),
            role=Field(value="Analista", confidence=1.0, sources=[]),
            base_salary=Field(value=3_000_000.0, confidence=1.0, sources=[]),
            auxilio_transporte=Field(value=162_000.0, confidence=1.0, sources=[]),
            salario_variable=Field(value=False, confidence=1.0, sources=[]),
            weekly_hours=Field(value=40, confidence=1.0, sources=[]),
            start_date=Field(value="2025-01-01", confidence=1.0, sources=[]),
            end_date=Field(value=None, confidence=0.0, sources=[]),
        )
        gaps = detect_gaps(rec, reference_date=REF)
        assert all(g.gap_id != "g2" for g in gaps)
