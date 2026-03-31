import json
import pytest
from pathlib import Path
from src.scrape_arena import load_arena_portfolio, validate_portfolio


def test_load_arena_portfolio_returns_dict():
    result = load_arena_portfolio()
    assert isinstance(result, dict)


def test_portfolio_has_required_keys():
    result = load_arena_portfolio()
    assert "as_at" in result
    assert "source" in result
    assert "states" in result
    assert "national" in result


def test_portfolio_states_have_required_fields():
    result = load_arena_portfolio()
    for state, data in result["states"].items():
        assert "centres" in data, f"{state} missing centres"
        assert "valuation_m" in data, f"{state} missing valuation_m"
        assert "metro_pct" in data, f"{state} missing metro_pct"
        assert "development_pipeline" in data, f"{state} missing development_pipeline"


def test_portfolio_national_totals_consistent():
    result = load_arena_portfolio()
    total_centres = sum(s["centres"] for s in result["states"].values())
    assert result["national"]["total_centres"] == total_centres


def test_validate_portfolio_rejects_missing_states():
    bad = {"as_at": "2026-01-01", "source": "test", "states": {}, "national": {}}
    with pytest.raises(ValueError, match="states"):
        validate_portfolio(bad)


def test_validate_portfolio_rejects_negative_centres():
    bad_state = {"centres": -1, "valuation_m": 1.0, "metro_pct": 50, "development_pipeline": 0}
    data = {
        "as_at": "2026-01-01",
        "source": "test",
        "states": {"VIC": bad_state},
        "national": {"total_centres": -1, "total_valuation_m": 1.0, "development_pipeline": 0},
    }
    with pytest.raises(ValueError, match="negative"):
        validate_portfolio(data)


def test_write_portfolio_json(tmp_output_dir):
    result = load_arena_portfolio()
    out_path = tmp_output_dir / "arena_portfolio.json"
    out_path.write_text(json.dumps(result, indent=2))
    loaded = json.loads(out_path.read_text())
    assert loaded == result
