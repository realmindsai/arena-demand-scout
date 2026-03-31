"""Build pipeline — orchestrates data scripts and writes JSON to site/data/."""

import json
import sys
from pathlib import Path

from src.scrape_arena import load_arena_portfolio
from src.fetch_abs import download_projection_tables, build_projections_json
from src.compute_scores import compute_opportunity_scores
from src.fetch_sa2 import build_sa2_data, load_sa2_population, load_sa2_supply
from src.compute_sa2_scores import compute_sa2_scores
from src.compute_state_market import compute_state_market_stats

DEFAULT_OUTPUT_DIR = Path("site/data")


def run_build(
    output_dir: Path | None = None,
    cache_dir: Path | None = None,
    skip_abs_download: bool = False,
) -> None:
    """Run the full build pipeline."""
    out = output_dir or DEFAULT_OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    print("Loading Arena portfolio data...")
    portfolio = load_arena_portfolio()
    (out / "arena_portfolio.json").write_text(json.dumps(portfolio, indent=2))
    print(f"  Wrote arena_portfolio.json ({len(portfolio['states'])} states)")

    if skip_abs_download:
        print("Skipping ABS download (skip_abs_download=True)")
        return

    print("Downloading ABS projection tables...")
    state_files = download_projection_tables(cache_dir=cache_dir)
    print("Parsing XLSX files...")
    projections = build_projections_json(state_files)
    (out / "abs_projections.json").write_text(json.dumps(projections, indent=2))
    print(f"  Wrote abs_projections.json ({len(projections['states'])} states)")

    print("Computing opportunity scores...")
    scores = compute_opportunity_scores(portfolio, projections)
    (out / "opportunity_scores.json").write_text(json.dumps(scores, indent=2))
    print(f"  Wrote opportunity_scores.json ({len(scores['rankings'])} rankings)")

    print("Building SA2-level data...")
    merged_geojson, sa2_population = build_sa2_data(cache_dir=cache_dir)
    (out / "sa2_boundaries.geojson").write_text(json.dumps(merged_geojson))
    print(f"  Wrote sa2_boundaries.geojson ({len(merged_geojson['features'])} features)")

    print("Computing SA2 scores...")
    sa2_scores = compute_sa2_scores(merged_geojson)
    (out / "sa2_scores.json").write_text(json.dumps(sa2_scores))
    print(f"  Wrote sa2_scores.json ({sa2_scores['total_sa2_regions']} SA2 regions)")

    print("Computing state market stats...")
    supply = load_sa2_supply()
    population = load_sa2_population(cache_dir=cache_dir)
    market_stats = compute_state_market_stats(population, supply, portfolio, sa2_scores)
    (out / "state_market.json").write_text(json.dumps(market_stats, indent=2))
    print(f"  Wrote state_market.json ({len(market_stats['states'])} states)")

    print("Build complete.")


if __name__ == "__main__":
    run_build()
