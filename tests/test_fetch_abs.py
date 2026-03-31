import json
import pytest
from pathlib import Path
from src.fetch_abs import (
    parse_projection_xlsx,
    aggregate_age_0_5,
    build_projections_json,
    STATE_TABLE_MAP,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def test_state_table_map_has_all_states():
    expected_states = {"NSW", "VIC", "QLD", "SA", "WA", "TAS", "NT", "ACT"}
    assert expected_states == set(STATE_TABLE_MAP.keys())


def test_parse_projection_xlsx_returns_age_data():
    xlsx_path = FIXTURE_DIR / "sample_projection.xlsx"
    if not xlsx_path.exists():
        pytest.skip("Run tests/fixtures/create_test_xlsx.py first")
    result = parse_projection_xlsx(xlsx_path)
    assert "years" in result
    assert "male" in result
    assert "female" in result


def test_parse_projection_xlsx_correct_years():
    xlsx_path = FIXTURE_DIR / "sample_projection.xlsx"
    if not xlsx_path.exists():
        pytest.skip("Run tests/fixtures/create_test_xlsx.py first")
    result = parse_projection_xlsx(xlsx_path)
    assert result["years"][0] == 2022
    assert result["years"][-1] == 2036


def test_aggregate_age_0_5_sums_correctly():
    male = {0: [100, 110], 1: [200, 210], 2: [300, 310],
            3: [400, 410], 4: [500, 510], 5: [600, 610]}
    female = {0: [100, 110], 1: [200, 210], 2: [300, 310],
              3: [400, 410], 4: [500, 510], 5: [600, 610]}
    result = aggregate_age_0_5(male, female)
    assert result == [4200, 4320]


def test_build_projections_json_structure(tmp_path):
    xlsx_path = FIXTURE_DIR / "sample_projection.xlsx"
    if not xlsx_path.exists():
        pytest.skip("Run tests/fixtures/create_test_xlsx.py first")

    state_files = {"VIC": {"series_b": xlsx_path}}
    result = build_projections_json(state_files)

    assert "base_year" in result
    assert "projection_years" in result
    assert "states" in result
    assert "VIC" in result["states"]
    assert "series_b" in result["states"]["VIC"]
    assert "population_0_5" in result["states"]["VIC"]["series_b"]
    assert len(result["states"]["VIC"]["series_b"]["population_0_5"]) == 15

    # erp_actual should be populated from Series B base year
    assert "erp_actual" in result
    assert "VIC" in result["erp_actual"]
    assert isinstance(result["erp_actual"]["VIC"]["population_0_5"], list)
    assert len(result["erp_actual"]["VIC"]["population_0_5"]) == 1


def test_parse_real_abs_file_if_available():
    """Sanity check against real ABS data."""
    real_path = Path(__file__).parent.parent / ".abs_cache" / "3222_Table_B2.xlsx"
    if not real_path.exists():
        pytest.skip("Real ABS file not available")
    result = parse_projection_xlsx(real_path)
    assert result["years"][0] == 2022
    assert len(result["years"]) == 15  # capped at 2036
    # VIC 0-year-old males in 2022 should be ~38000 (known from file)
    assert 30000 < result["male"][0][0] < 50000
