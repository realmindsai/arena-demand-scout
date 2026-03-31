import json
import pytest
from pathlib import Path


@pytest.fixture
def sample_arena_portfolio():
    """Minimal valid Arena portfolio for testing."""
    return {
        "as_at": "2026-03-31",
        "source": "Test",
        "states": {
            "VIC": {"centres": 79, "valuation_m": 512.3, "metro_pct": 72, "development_pipeline": 5},
            "NSW": {"centres": 60, "valuation_m": 400.0, "metro_pct": 80, "development_pipeline": 3},
        },
        "national": {
            "total_centres": 139,
            "total_valuation_m": 912.3,
            "development_pipeline": 8,
        },
    }


@pytest.fixture
def sample_abs_projections():
    """Minimal valid ABS projections for testing."""
    years = list(range(2022, 2037))
    base_pop = 400000
    return {
        "base_year": 2022,
        "projection_years": years,
        "states": {
            "VIC": {
                "series_a": {"population_0_5": [base_pop + i * 3000 for i in range(len(years))]},
                "series_b": {"population_0_5": [base_pop + i * 2000 for i in range(len(years))]},
                "series_c": {"population_0_5": [base_pop + i * 1000 for i in range(len(years))]},
            },
            "NSW": {
                "series_a": {"population_0_5": [500000 + i * 2500 for i in range(len(years))]},
                "series_b": {"population_0_5": [500000 + i * 1500 for i in range(len(years))]},
                "series_c": {"population_0_5": [500000 + i * 500 for i in range(len(years))]},
            },
        },
        "erp_actual": {
            "VIC": {"population_0_5": [403500], "as_at": "2025-09-30"},
            "NSW": {"population_0_5": [504000], "as_at": "2025-09-30"},
        },
    }


@pytest.fixture
def tmp_output_dir(tmp_path):
    """Temporary directory for build output."""
    out = tmp_path / "data"
    out.mkdir()
    return out
