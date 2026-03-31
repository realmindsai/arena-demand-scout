"""Build pipeline — orchestrates data scripts and writes JSON to site/data/."""

import json
import sys
from pathlib import Path

from src.scrape_arena import load_arena_portfolio
from src.fetch_abs import download_projection_tables, build_projections_json
from src.compute_scores import compute_opportunity_scores

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

    print("Build complete.")


if __name__ == "__main__":
    run_build()
