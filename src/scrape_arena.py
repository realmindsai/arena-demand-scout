"""Load and validate Arena REIT portfolio data from curated JSON."""

import json
from pathlib import Path

SOURCE_PATH = Path(__file__).parent / "data" / "arena_portfolio_source.json"

REQUIRED_STATE_FIELDS = {"centres", "valuation_m", "metro_pct", "development_pipeline"}
REQUIRED_NATIONAL_FIELDS = {"total_centres", "total_valuation_m", "development_pipeline"}


def load_arena_portfolio(source_path: Path | None = None) -> dict:
    """Load Arena portfolio from curated JSON file."""
    path = source_path or SOURCE_PATH
    with open(path) as f:
        data = json.load(f)
    validate_portfolio(data)
    return data


def validate_portfolio(data: dict) -> None:
    """Validate portfolio data structure and values."""
    if not data.get("states"):
        raise ValueError("Portfolio must have non-empty states")

    for state, info in data["states"].items():
        missing = REQUIRED_STATE_FIELDS - set(info.keys())
        if missing:
            raise ValueError(f"{state} missing fields: {missing}")
        if info["centres"] < 0:
            raise ValueError(f"{state} has negative centres")
        if info["valuation_m"] < 0:
            raise ValueError(f"{state} has negative valuation")

    national = data.get("national", {})
    missing = REQUIRED_NATIONAL_FIELDS - set(national.keys())
    if missing:
        raise ValueError(f"National missing fields: {missing}")
