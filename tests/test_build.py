import json
import pytest
from pathlib import Path
from build import run_build


def test_build_creates_output_directory(tmp_path):
    output_dir = tmp_path / "site" / "data"
    run_build(output_dir=output_dir, skip_abs_download=True)
    assert output_dir.exists()


def test_build_creates_arena_json(tmp_path):
    output_dir = tmp_path / "site" / "data"
    run_build(output_dir=output_dir, skip_abs_download=True)
    arena_path = output_dir / "arena_portfolio.json"
    assert arena_path.exists()
    data = json.loads(arena_path.read_text())
    assert "states" in data
    assert "national" in data


def test_build_creates_all_output_files_when_abs_cached(tmp_path):
    """Full integration test — requires ABS files to be cached."""
    output_dir = tmp_path / "site" / "data"
    cache_dir = Path(".abs_cache")
    if not cache_dir.exists() or not list(cache_dir.glob("*.xlsx")):
        pytest.skip("ABS cache not populated — run 'make build' first")

    run_build(output_dir=output_dir, cache_dir=cache_dir)

    assert (output_dir / "arena_portfolio.json").exists()
    assert (output_dir / "abs_projections.json").exists()
    assert (output_dir / "opportunity_scores.json").exists()
