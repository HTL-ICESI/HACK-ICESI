"""Tests del número mágico (M6). Contrato: función pura, reproducible."""
import pytest

from app.domain.exposure.calculator import ExposureInput, compute


def test_exposicion_reproducible():
    inp = ExposureInput(workers_at_risk=50, detected_reliquidations=0,
                        total_clauses=30, outdated_clauses=7, year=2026)
    a, b = compute(inp), compute(inp)
    assert a == b


def test_exposicion_base_sin_reliquidaciones():
    inp = ExposureInput(workers_at_risk=50, detected_reliquidations=0,
                        total_clauses=30, outdated_clauses=7, year=2026)
    res = compute(inp)
    assert res.cop_exposure == pytest.approx(50 * 1_423_500)
    assert res.pct_outdated == pytest.approx(23.3)
