# Arena Demand Scout Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a static dashboard (GitHub Pages) that overlays Arena REIT's public portfolio against ABS 0–5 population projections to identify ELC expansion opportunities by state.

**Architecture:** Python build pipeline downloads ABS XLSX files + reads curated Arena portfolio JSON → processes into clean JSON → static single-page site renders with Alpine.js (state), Plotly.js (charts), Leaflet.js (map). Deployed to GitHub Pages.

**Tech Stack:** Python 3.12 + uv, openpyxl, httpx, pytest, playwright. HTML/CSS (Tailwind CDN), Alpine.js, Plotly.js, Leaflet.js.

**Spec:** `docs/superpowers/specs/2026-03-31-arena-demand-scout-design.md`

---

## File Map

| File | Responsibility |
|------|---------------|
| `pyproject.toml` | Project metadata, dependencies, scripts |
| `Makefile` | Build/test/serve shortcuts |
| `.gitignore` | Ignore .venv, site/data/, __pycache__, .xlsx cache |
| `build.py` | Orchestrator — runs all data scripts, writes JSON to site/data/ |
| `src/__init__.py` | Package marker |
| `src/scrape_arena.py` | Reads curated Arena portfolio JSON, validates, copies to site/data/ |
| `src/fetch_abs.py` | Downloads ABS XLSX files, parses 0–5 age cohort, outputs JSON |
| `src/compute_scores.py` | Computes opportunity scores from portfolio + projections |
| `src/data/arena_portfolio_source.json` | Hand-curated Arena REIT portfolio data |
| `site/index.html` | Single-page dashboard with 4 tabs |
| `site/css/style.css` | Custom styles (Tailwind via CDN in HTML) |
| `site/js/app.js` | Alpine.js app state, tab switching, filter controls |
| `site/js/charts.js` | Plotly.js chart configurations for all tabs |
| `site/js/map.js` | Leaflet map setup, choropleth, popups |
| `site/assets/geo/aus_states.geojson` | Simplified Australian state boundaries |
| `tests/test_scrape_arena.py` | Unit tests for Arena data loading/validation |
| `tests/test_fetch_abs.py` | Unit tests for ABS XLSX parsing |
| `tests/test_compute_scores.py` | Unit tests for opportunity scoring |
| `tests/test_build.py` | Integration test — full build pipeline |
| `tests/test_e2e.py` | Playwright e2e — tabs render, charts load, filters work |
| `tests/conftest.py` | Shared fixtures (sample data, temp dirs) |
| `tests/fixtures/create_test_xlsx.py` | Helper script to generate test XLSX fixture |
| `tests/fixtures/sample_projection.xlsx` | Generated ABS-format test fixture (committed) |
| `.github/workflows/deploy.yml` | GitHub Actions — build + deploy to Pages |

---

## Chunk 1: Project Scaffolding + Arena Portfolio Data

### Task 1: Project scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `Makefile`
- Create: `.gitignore`
- Create: `src/__init__.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "arena-demand-scout"
version = "0.1.0"
description = "Dashboard: Arena REIT portfolio vs ABS childcare demand projections"
requires-python = ">=3.12"
dependencies = [
    "httpx>=0.28",
    "openpyxl>=3.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-playwright>=0.6",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

- [ ] **Step 2: Create Makefile**

```makefile
.PHONY: build test serve clean

build:
	uv run python build.py

test:
	uv run pytest tests/ -v --ignore=tests/test_e2e.py

test-e2e:
	uv run pytest tests/test_e2e.py -v

serve:
	cd site && python -m http.server 8000

clean:
	rm -rf site/data/*.json .abs_cache/
```

- [ ] **Step 3: Create .gitignore**

```
.venv/
__pycache__/
*.pyc
site/data/
.abs_cache/
*.xlsx
.pytest_cache/
```

- [ ] **Step 4: Create src/__init__.py**

Empty file.

- [ ] **Step 5: Install dependencies**

Run: `uv sync --all-extras`
Expected: Dependencies install successfully

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml Makefile .gitignore src/__init__.py
git commit -m "chore: project scaffolding with uv, pytest, openpyxl, httpx"
```

---

### Task 2: Arena portfolio source data + loader

**Files:**
- Create: `src/data/arena_portfolio_source.json`
- Create: `src/scrape_arena.py`
- Create: `tests/conftest.py`
- Create: `tests/test_scrape_arena.py`

- [ ] **Step 1: Research Arena REIT public data**

Visit arena.com.au/investors/ and locate the latest results presentation PDF. Extract state-by-state ELC counts, valuations, metro/regional splits, and development pipeline numbers. Record the source document name and date.

- [ ] **Step 2: Create the curated source JSON**

Create `src/data/arena_portfolio_source.json` with real data from the results presentation. Structure:

```json
{
  "as_at": "2026-03-31",
  "source": "Arena REIT HY2026 Results Presentation",
  "states": {
    "NSW": {"centres": 0, "valuation_m": 0, "metro_pct": 0, "development_pipeline": 0},
    "VIC": {"centres": 0, "valuation_m": 0, "metro_pct": 0, "development_pipeline": 0},
    "QLD": {"centres": 0, "valuation_m": 0, "metro_pct": 0, "development_pipeline": 0},
    "SA":  {"centres": 0, "valuation_m": 0, "metro_pct": 0, "development_pipeline": 0},
    "WA":  {"centres": 0, "valuation_m": 0, "metro_pct": 0, "development_pipeline": 0},
    "TAS": {"centres": 0, "valuation_m": 0, "metro_pct": 0, "development_pipeline": 0},
    "NT":  {"centres": 0, "valuation_m": 0, "metro_pct": 0, "development_pipeline": 0},
    "ACT": {"centres": 0, "valuation_m": 0, "metro_pct": 0, "development_pipeline": 0}
  },
  "national": {
    "total_centres": 0,
    "total_valuation_m": 0,
    "development_pipeline": 0
  }
}
```

Replace all `0` values with real data from Step 1.

- [ ] **Step 3: Create tests/conftest.py with shared fixtures**

```python
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
```

- [ ] **Step 4: Write failing tests for scrape_arena.py**

Create `tests/test_scrape_arena.py`:

```python
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
```

- [ ] **Step 5: Run tests to verify they fail**

Run: `uv run pytest tests/test_scrape_arena.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.scrape_arena'`

- [ ] **Step 6: Implement src/scrape_arena.py**

```python
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
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `uv run pytest tests/test_scrape_arena.py -v`
Expected: All 7 tests PASS

- [ ] **Step 8: Commit**

```bash
git add src/ tests/conftest.py tests/test_scrape_arena.py
git commit -m "feat: Arena portfolio loader with validation and curated source data"
```

---

## Chunk 2: ABS Data Fetcher

### Task 3: ABS projection XLSX downloader + parser

**Files:**
- Create: `src/fetch_abs.py`
- Create: `tests/test_fetch_abs.py`
- Create: `tests/fixtures/` (small test XLSX files)

This is the most complex data task. The ABS XLSX files have a specific structure:
- Sheet `Data1`: columns are `Projected persons ; Series XX(Y) ; STATE ; Male/Female ; AGE ;`
- Rows: dates from 2022-06-01 to 2071-06-01

- [ ] **Step 1: Download a sample ABS XLSX to understand structure**

Run: `curl -o /tmp/abs_sample_b2.xlsx "https://www.abs.gov.au/statistics/people/population/population-projections-australia/2022-base-2071/3222_Table_B2.xlsx"`

Examine the file to confirm sheet names, column header format, and row structure. This informs the parser.

- [ ] **Step 2: Create a minimal test fixture XLSX**

Create `tests/fixtures/create_test_xlsx.py` — a helper script that generates a small XLSX file mimicking the ABS format for testing. Run it once to produce `tests/fixtures/sample_projection.xlsx`.

```python
"""Generate a minimal ABS-format XLSX for testing. Run once."""

import openpyxl
from pathlib import Path

FIXTURE_DIR = Path(__file__).parent


def create_sample_projection_xlsx():
    wb = openpyxl.Workbook()

    # Data1 sheet with single-year-of-age columns
    ws = wb.active
    ws.title = "Data1"

    # Row 1: Series description (metadata, skip in parsing)
    # Actual ABS files have ~10 header rows before data.
    # We'll simulate a simplified version: header row then data rows.

    # Build headers: "Projected persons ; Series 29(B) ; VIC ; Male ; 0 ;"
    ages = list(range(0, 6))  # only ages 0-5 for test brevity
    headers = ["Date"]
    for sex in ["Male", "Female"]:
        for age in ages:
            headers.append(f"Projected persons ; Series 29(B) ; Victoria ; {sex} ; {age} ;")

    ws.append(headers)

    # Data rows: 2022 through 2036 (15 years)
    import datetime
    for year_offset in range(15):
        year = 2022 + year_offset
        dt = datetime.date(year, 6, 1)
        row = [dt]
        for sex in ["Male", "Female"]:
            for age in ages:
                # base 33000 per age/sex, grows 200/year
                row.append(33000 + year_offset * 200 + age * 100)
        ws.append(row)

    wb.save(FIXTURE_DIR / "sample_projection.xlsx")
    print(f"Created {FIXTURE_DIR / 'sample_projection.xlsx'}")


if __name__ == "__main__":
    create_sample_projection_xlsx()
```

Run: `uv run python tests/fixtures/create_test_xlsx.py`

- [ ] **Step 3: Write failing tests for fetch_abs.py**

Create `tests/test_fetch_abs.py`:

```python
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
    # 6 ages (0-5) x 2 sexes = 12 values per year
    male = {0: [100, 110], 1: [200, 210], 2: [300, 310],
            3: [400, 410], 4: [500, 510], 5: [600, 610]}
    female = {0: [100, 110], 1: [200, 210], 2: [300, 310],
              3: [400, 410], 4: [500, 510], 5: [600, 610]}
    result = aggregate_age_0_5(male, female)
    # year 0: (100+200+300+400+500+600)*2 = 4200
    # year 1: (110+210+310+410+510+610)*2 = 4320
    assert result == [4200, 4320]


def test_build_projections_json_structure(tmp_path):
    """Test with fixture XLSX files (simplified: just validates output shape)."""
    # This test uses the fixture to validate the output structure
    xlsx_path = FIXTURE_DIR / "sample_projection.xlsx"
    if not xlsx_path.exists():
        pytest.skip("Run tests/fixtures/create_test_xlsx.py first")

    # Test with a single-state dict pointing to the fixture
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
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `uv run pytest tests/test_fetch_abs.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.fetch_abs'`

- [ ] **Step 5: Implement src/fetch_abs.py**

```python
"""Fetch and parse ABS population projection XLSX files."""

import datetime
import httpx
import openpyxl
from pathlib import Path

PROJECTIONS_BASE_URL = (
    "https://www.abs.gov.au/statistics/people/population/"
    "population-projections-australia/2022-base-2071"
)

CACHE_DIR = Path(".abs_cache")

STATE_TABLE_MAP = {
    "NSW": 1, "VIC": 2, "QLD": 3, "SA": 4,
    "WA": 5, "TAS": 6, "NT": 7, "ACT": 8,
}

SERIES_MAP = {"series_a": "A", "series_b": "B", "series_c": "C"}

MAX_PROJECTION_YEAR = 2036


def download_xlsx(url: str, dest: Path) -> Path:
    """Download XLSX file if not already cached."""
    if dest.exists():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    resp = httpx.get(url, follow_redirects=True, timeout=60)
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    return dest


def download_projection_tables(cache_dir: Path | None = None) -> dict:
    """Download all projection XLSX files, return {state: {series: path}}."""
    cache = cache_dir or CACHE_DIR
    state_files = {}
    for state, num in STATE_TABLE_MAP.items():
        state_files[state] = {}
        for series_key, series_letter in SERIES_MAP.items():
            filename = f"3222_Table_{series_letter}{num}.xlsx"
            url = f"{PROJECTIONS_BASE_URL}/{filename}"
            dest = cache / filename
            download_xlsx(url, dest)
            state_files[state][series_key] = dest
    return state_files


def parse_projection_xlsx(xlsx_path: Path) -> dict:
    """Parse an ABS projection XLSX, extracting age 0-5 data by sex."""
    wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)

    # Try Data1 sheet first, fall back to first sheet
    if "Data1" in wb.sheetnames:
        ws = wb["Data1"]
    else:
        ws = wb[wb.sheetnames[0]]

    rows = list(ws.iter_rows(values_only=True))
    wb.close()

    # Find header row (contains column descriptions)
    header_row_idx = None
    for i, row in enumerate(rows):
        if row and row[0] and str(row[0]).strip().lower() in ("date", "series id"):
            header_row_idx = i
            break

    if header_row_idx is None:
        # ABS files often have metadata rows; look for the row before dates start
        for i, row in enumerate(rows):
            if row and row[0] and isinstance(row[0], datetime.datetime):
                header_row_idx = i - 1
                break

    if header_row_idx is None:
        raise ValueError(f"Could not find header row in {xlsx_path}")

    headers = rows[header_row_idx]
    data_rows = rows[header_row_idx + 1:]

    # Parse column headers to identify age/sex columns
    male = {}  # {age: [values_per_year]}
    female = {}
    col_map = []  # [(col_idx, sex, age)]

    for col_idx, header in enumerate(headers):
        if col_idx == 0 or not header:
            continue
        h = str(header).strip()
        h_lower = h.lower()

        # Extract sex and age from header string
        sex = None
        age = None
        if "male" in h_lower and "female" not in h_lower:
            sex = "male"
        elif "female" in h_lower:
            sex = "female"
        # Also handle "Persons" columns (combined sex)
        elif "persons" in h_lower:
            sex = "persons"

        if sex:
            # Extract age — last numeric part before ';' or end
            parts = h.split(";")
            for part in reversed(parts):
                part = part.strip().rstrip(";").strip()
                if part.isdigit():
                    age = int(part)
                    break

        if sex and age is not None and 0 <= age <= 5:
            col_map.append((col_idx, sex, age))

    # Extract year and values
    years = []
    for sex in ["male", "female"]:
        for age in range(6):
            if sex == "male":
                male[age] = []
            else:
                female[age] = []

    for row in data_rows:
        if not row or not row[0]:
            continue
        date_val = row[0]
        if isinstance(date_val, datetime.datetime):
            year = date_val.year
        elif isinstance(date_val, str) and len(date_val) >= 4:
            year = int(date_val[:4])
        else:
            continue

        if year > MAX_PROJECTION_YEAR:
            break

        if not years or years[-1] != year:
            years.append(year)

        for col_idx, sex, age in col_map:
            val = row[col_idx] if col_idx < len(row) else None
            if val is None:
                val = 0
            if sex == "male":
                male[age].append(int(val))
            elif sex == "female":
                female[age].append(int(val))
            elif sex == "persons":
                # If we only have "Persons" columns, put half in each
                male.setdefault(age, []).append(int(val) // 2)
                female.setdefault(age, []).append(int(val) - int(val) // 2)

    return {"years": years, "male": male, "female": female}


def aggregate_age_0_5(male: dict, female: dict) -> list[int]:
    """Sum ages 0-5 across both sexes for each year."""
    if not male or not female:
        return []
    n_years = min(len(male.get(0, [])), len(female.get(0, [])))
    totals = []
    for i in range(n_years):
        total = 0
        for age in range(6):
            total += male.get(age, [0] * n_years)[i]
            total += female.get(age, [0] * n_years)[i]
        totals.append(total)
    return totals


def build_projections_json(state_files: dict) -> dict:
    """Build the full projections JSON from downloaded XLSX files.

    state_files: {state: {series_key: Path}}

    erp_actual is derived from the projection base year (2022) Series B data.
    The ABS ERP XLSX files use a different structure and are not downloaded
    separately — the projection base year serves as the actual population anchor.
    """
    result = {
        "base_year": 2022,
        "projection_years": [],
        "states": {},
        "erp_actual": {},
    }

    for state, series_paths in state_files.items():
        result["states"][state] = {}
        for series_key, xlsx_path in series_paths.items():
            parsed = parse_projection_xlsx(xlsx_path)
            pop_0_5 = aggregate_age_0_5(parsed["male"], parsed["female"])
            result["states"][state][series_key] = {"population_0_5": pop_0_5}

            if not result["projection_years"] and parsed["years"]:
                result["projection_years"] = parsed["years"]

            # Use Series B base year value as the ERP actual anchor
            if series_key == "series_b" and pop_0_5:
                result["erp_actual"][state] = {
                    "population_0_5": [pop_0_5[0]],
                    "as_at": "2022-06-30",
                }

    return result
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/test_fetch_abs.py -v`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add src/fetch_abs.py tests/test_fetch_abs.py tests/fixtures/
git commit -m "feat: ABS population projection XLSX fetcher and parser"
```

---

## Chunk 3: Opportunity Scorer + Build Orchestrator

### Task 4: Opportunity scorer

**Files:**
- Create: `src/compute_scores.py`
- Create: `tests/test_compute_scores.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_compute_scores.py`:

```python
import pytest
from src.compute_scores import compute_opportunity_scores, get_verdict


def test_compute_scores_returns_rankings(sample_arena_portfolio, sample_abs_projections):
    result = compute_opportunity_scores(sample_arena_portfolio, sample_abs_projections)
    assert "rankings" in result
    assert len(result["rankings"]) == 2  # VIC + NSW from fixtures


def test_ranking_has_required_fields(sample_arena_portfolio, sample_abs_projections):
    result = compute_opportunity_scores(sample_arena_portfolio, sample_abs_projections)
    for entry in result["rankings"]:
        assert "state" in entry
        assert "centre_count" in entry
        assert "demand_growth_pct" in entry
        assert "current_supply_density" in entry
        assert "opportunity_score" in entry
        assert "verdict" in entry


def test_scores_are_0_to_100(sample_arena_portfolio, sample_abs_projections):
    result = compute_opportunity_scores(sample_arena_portfolio, sample_abs_projections)
    for entry in result["rankings"]:
        assert 0 <= entry["opportunity_score"] <= 100


def test_rankings_sorted_by_score_descending(sample_arena_portfolio, sample_abs_projections):
    result = compute_opportunity_scores(sample_arena_portfolio, sample_abs_projections)
    scores = [e["opportunity_score"] for e in result["rankings"]]
    assert scores == sorted(scores, reverse=True)


def test_demand_growth_pct_positive_for_growing_population(
    sample_arena_portfolio, sample_abs_projections
):
    """Fixture data has growing populations, so growth should be positive."""
    result = compute_opportunity_scores(sample_arena_portfolio, sample_abs_projections)
    for entry in result["rankings"]:
        assert entry["demand_growth_pct"] > 0


def test_get_verdict_thresholds():
    assert get_verdict(70) == "High priority"
    assert get_verdict(85) == "High priority"
    assert get_verdict(40) == "Medium priority"
    assert get_verdict(69) == "Medium priority"
    assert get_verdict(39) == "Low priority"
    assert get_verdict(0) == "Low priority"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_compute_scores.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement src/compute_scores.py**

```python
"""Compute opportunity scores from Arena portfolio + ABS projections."""


def get_verdict(score: int) -> str:
    if score >= 70:
        return "High priority"
    elif score >= 40:
        return "Medium priority"
    return "Low priority"


def compute_opportunity_scores(portfolio: dict, projections: dict) -> dict:
    """Compute per-state opportunity scores.

    Formula:
        normalised_growth = (growth - min_growth) / (max_growth - min_growth)
        normalised_gap = 1 - (density - min_density) / (max_density - min_density)
        raw_score = 0.6 * normalised_growth + 0.4 * normalised_gap
        opportunity_score = round(raw_score * 100)
    """
    years = projections["projection_years"]

    # Find indices for 2026 and 2031 in the projection years
    try:
        idx_2026 = years.index(2026)
    except ValueError:
        idx_2026 = 4  # fallback: 2022 + 4 = 2026

    try:
        idx_2031 = years.index(2031)
    except ValueError:
        idx_2031 = 9  # fallback: 2022 + 9 = 2031

    # Only score states that appear in both datasets
    common_states = set(portfolio["states"].keys()) & set(projections["states"].keys())

    raw_entries = []
    for state in common_states:
        arena = portfolio["states"][state]
        pop_data = projections["states"][state]["series_b"]["population_0_5"]

        pop_2026 = pop_data[idx_2026]
        pop_2031 = pop_data[idx_2031]

        demand_growth_pct = round((pop_2031 - pop_2026) / pop_2026 * 100, 1)
        supply_density = round(arena["centres"] / (pop_2026 / 1000), 2)

        raw_entries.append({
            "state": state,
            "centre_count": arena["centres"],
            "demand_growth_pct": demand_growth_pct,
            "current_supply_density": supply_density,
        })

    if not raw_entries:
        return {"rankings": []}

    # Min-max normalise across states
    growths = [e["demand_growth_pct"] for e in raw_entries]
    densities = [e["current_supply_density"] for e in raw_entries]

    growth_min, growth_max = min(growths), max(growths)
    density_min, density_max = min(densities), max(densities)

    growth_range = growth_max - growth_min if growth_max != growth_min else 1
    density_range = density_max - density_min if density_max != density_min else 1

    for entry in raw_entries:
        norm_growth = (entry["demand_growth_pct"] - growth_min) / growth_range
        norm_gap = 1 - (entry["current_supply_density"] - density_min) / density_range
        raw_score = 0.6 * norm_growth + 0.4 * norm_gap
        entry["opportunity_score"] = max(0, min(100, round(raw_score * 100)))
        entry["verdict"] = get_verdict(entry["opportunity_score"])

    rankings = sorted(raw_entries, key=lambda e: e["opportunity_score"], reverse=True)
    return {"rankings": rankings}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_compute_scores.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/compute_scores.py tests/test_compute_scores.py
git commit -m "feat: opportunity scoring with min-max normalisation"
```

---

### Task 5: Build orchestrator

**Files:**
- Create: `build.py`
- Create: `tests/test_build.py`

- [ ] **Step 1: Write failing integration test**

Create `tests/test_build.py`:

```python
import json
import pytest
from pathlib import Path
from unittest.mock import patch
from build import run_build


def test_build_creates_output_directory(tmp_path):
    output_dir = tmp_path / "site" / "data"
    with patch("build.download_projection_tables") as mock_download:
        # Skip real downloads in test
        mock_download.return_value = {}
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_build.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'build'`

- [ ] **Step 3: Implement build.py**

```python
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

    # Step 1: Arena portfolio
    print("Loading Arena portfolio data...")
    portfolio = load_arena_portfolio()
    (out / "arena_portfolio.json").write_text(json.dumps(portfolio, indent=2))
    print(f"  Wrote arena_portfolio.json ({len(portfolio['states'])} states)")

    if skip_abs_download:
        print("Skipping ABS download (skip_abs_download=True)")
        return

    # Step 2: ABS projections
    print("Downloading ABS projection tables...")
    state_files = download_projection_tables(cache_dir=cache_dir)
    print("Parsing XLSX files...")
    projections = build_projections_json(state_files)
    (out / "abs_projections.json").write_text(json.dumps(projections, indent=2))
    print(f"  Wrote abs_projections.json ({len(projections['states'])} states)")

    # Step 3: Opportunity scores
    print("Computing opportunity scores...")
    scores = compute_opportunity_scores(portfolio, projections)
    (out / "opportunity_scores.json").write_text(json.dumps(scores, indent=2))
    print(f"  Wrote opportunity_scores.json ({len(scores['rankings'])} rankings)")

    print("Build complete.")


if __name__ == "__main__":
    run_build()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_build.py -v`
Expected: First two tests PASS, third skipped (no ABS cache)

- [ ] **Step 5: Run the actual build to download ABS data and generate all JSON**

Run: `uv run python build.py`
Expected: Downloads 24 XLSX files (~5MB total), generates 3 JSON files in site/data/

- [ ] **Step 6: Run the full integration test now that cache exists**

Run: `uv run pytest tests/test_build.py -v`
Expected: All 3 tests PASS

- [ ] **Step 7: Commit**

```bash
git add build.py tests/test_build.py
git commit -m "feat: build orchestrator — downloads ABS data, generates all JSON"
```

---

## Chunk 4: Frontend Shell (HTML + CSS + Alpine.js)

### Task 6: HTML structure + Alpine.js app

**Files:**
- Create: `site/index.html`
- Create: `site/css/style.css`
- Create: `site/js/app.js`

- [ ] **Step 1: Create site/index.html**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Arena Demand Scout</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
    <script src="https://cdn.plot.ly/plotly-2.35.0.min.js"></script>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <link rel="stylesheet" href="css/style.css">
</head>
<body class="bg-slate-50 text-slate-800 font-sans">

<div x-data="demandScout()" x-init="init()">

    <!-- Header -->
    <header class="bg-slate-900 text-white px-6 py-4 shadow-lg">
        <div class="max-w-7xl mx-auto flex items-center justify-between">
            <div>
                <h1 class="text-2xl font-bold tracking-tight">Arena Demand Scout</h1>
                <p class="text-slate-400 text-sm mt-1">
                    Portfolio vs Childcare Demand Analysis
                    <span x-show="portfolio" x-text="'| Data as at ' + portfolio?.as_at" class="ml-2"></span>
                </p>
            </div>
            <div class="flex items-center gap-2">
                <span class="text-sm text-slate-400">Projection:</span>
                <template x-for="s in ['series_a', 'series_b', 'series_c']" :key="s">
                    <button
                        :class="activeSeries === s
                            ? 'bg-teal-500 text-white'
                            : 'bg-slate-700 text-slate-300 hover:bg-slate-600'"
                        class="px-3 py-1 rounded text-sm font-medium transition-colors"
                        x-text="s === 'series_a' ? 'High' : s === 'series_b' ? 'Medium' : 'Low'"
                        @click="setSeries(s)"
                    ></button>
                </template>
            </div>
        </div>
    </header>

    <!-- Tab Navigation -->
    <nav class="bg-white border-b border-slate-200 px-6">
        <div class="max-w-7xl mx-auto flex gap-1">
            <template x-for="tab in tabs" :key="tab.id">
                <button
                    :class="activeTab === tab.id
                        ? 'border-teal-500 text-teal-600 bg-teal-50'
                        : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'"
                    class="px-4 py-3 text-sm font-medium border-b-2 transition-colors"
                    x-text="tab.label"
                    @click="setTab(tab.id)"
                ></button>
            </template>
        </div>
    </nav>

    <!-- Loading State -->
    <div x-show="loading" class="max-w-7xl mx-auto p-12 text-center">
        <p class="text-slate-500">Loading data...</p>
    </div>

    <!-- Tab Content -->
    <main x-show="!loading" class="max-w-7xl mx-auto p-6">

        <!-- Tab 1: Portfolio Overview -->
        <section x-show="activeTab === 'portfolio'" x-cloak>
            <!-- Summary Cards -->
            <div class="grid grid-cols-3 gap-4 mb-6">
                <div class="bg-white rounded-lg shadow p-6 text-center">
                    <p class="text-3xl font-bold text-teal-600" x-text="portfolio?.national?.total_centres || '—'"></p>
                    <p class="text-sm text-slate-500 mt-1">Total ELC Centres</p>
                </div>
                <div class="bg-white rounded-lg shadow p-6 text-center">
                    <p class="text-3xl font-bold text-teal-600" x-text="portfolio?.national?.total_valuation_m ? '$' + portfolio.national.total_valuation_m + 'M' : '—'"></p>
                    <p class="text-sm text-slate-500 mt-1">Total Valuation</p>
                </div>
                <div class="bg-white rounded-lg shadow p-6 text-center">
                    <p class="text-3xl font-bold text-teal-600" x-text="portfolio?.national?.development_pipeline || '—'"></p>
                    <p class="text-sm text-slate-500 mt-1">Development Pipeline</p>
                </div>
            </div>

            <!-- State Table + Donut -->
            <div class="grid grid-cols-2 gap-6">
                <div class="bg-white rounded-lg shadow overflow-hidden">
                    <table class="w-full text-sm">
                        <thead class="bg-slate-100">
                            <tr>
                                <th class="text-left px-4 py-3">State</th>
                                <th class="text-right px-4 py-3">Centres</th>
                                <th class="text-right px-4 py-3">Valuation ($M)</th>
                                <th class="text-right px-4 py-3">Metro %</th>
                                <th class="text-right px-4 py-3">Pipeline</th>
                            </tr>
                        </thead>
                        <tbody>
                            <template x-for="[state, data] in stateEntries" :key="state">
                                <tr class="border-t border-slate-100 hover:bg-slate-50">
                                    <td class="px-4 py-2 font-medium" x-text="state"></td>
                                    <td class="px-4 py-2 text-right" x-text="data.centres"></td>
                                    <td class="px-4 py-2 text-right" x-text="'$' + data.valuation_m"></td>
                                    <td class="px-4 py-2 text-right" x-text="data.metro_pct + '%'"></td>
                                    <td class="px-4 py-2 text-right" x-text="data.development_pipeline"></td>
                                </tr>
                            </template>
                        </tbody>
                    </table>
                </div>
                <div id="chart-donut" class="bg-white rounded-lg shadow p-4"></div>
            </div>
        </section>

        <!-- Tab 2: Demand Forecast -->
        <section x-show="activeTab === 'forecast'" x-cloak>
            <div class="mb-4 flex flex-wrap gap-2">
                <button
                    :class="selectedStates.length === allStates.length
                        ? 'bg-teal-500 text-white' : 'bg-slate-200 text-slate-600'"
                    class="px-3 py-1 rounded text-sm"
                    @click="toggleAllStates()"
                >All</button>
                <template x-for="st in allStates" :key="st">
                    <button
                        :class="selectedStates.includes(st)
                            ? 'bg-teal-500 text-white' : 'bg-slate-200 text-slate-600 hover:bg-slate-300'"
                        class="px-3 py-1 rounded text-sm transition-colors"
                        x-text="st"
                        @click="toggleState(st)"
                    ></button>
                </template>
            </div>
            <div id="chart-forecast" class="bg-white rounded-lg shadow p-4 mb-6"></div>
            <div id="forecast-summary" class="bg-white rounded-lg shadow p-4">
                <h3 class="font-semibold text-slate-700 mb-3">Growth Summary (Series B)</h3>
                <div class="grid grid-cols-4 gap-4 text-sm" id="forecast-summary-grid"></div>
            </div>
        </section>

        <!-- Tab 3: Opportunity Scoring -->
        <section x-show="activeTab === 'opportunity'" x-cloak>
            <div class="grid grid-cols-2 gap-6">
                <div class="bg-white rounded-lg shadow overflow-hidden">
                    <table class="w-full text-sm">
                        <thead class="bg-slate-100">
                            <tr>
                                <th class="text-left px-4 py-3">State</th>
                                <th class="text-right px-4 py-3">Demand Growth %</th>
                                <th class="text-right px-4 py-3">Supply Density</th>
                                <th class="text-right px-4 py-3">Score</th>
                                <th class="text-left px-4 py-3">Verdict</th>
                            </tr>
                        </thead>
                        <tbody>
                            <template x-for="entry in scores?.rankings || []" :key="entry.state">
                                <tr class="border-t border-slate-100">
                                    <td class="px-4 py-2 font-medium" x-text="entry.state"></td>
                                    <td class="px-4 py-2 text-right" x-text="entry.demand_growth_pct + '%'"></td>
                                    <td class="px-4 py-2 text-right" x-text="entry.current_supply_density"></td>
                                    <td class="px-4 py-2 text-right">
                                        <span class="inline-block px-2 py-0.5 rounded text-white text-xs font-bold"
                                              :class="scoreColor(entry.opportunity_score)"
                                              x-text="entry.opportunity_score"></span>
                                    </td>
                                    <td class="px-4 py-2" x-text="entry.verdict"></td>
                                </tr>
                            </template>
                        </tbody>
                    </table>
                </div>
                <div id="chart-scatter" class="bg-white rounded-lg shadow p-4"></div>
            </div>
        </section>

        <!-- Tab 4: Map -->
        <section x-show="activeTab === 'map'" x-cloak>
            <div id="map-container" class="bg-white rounded-lg shadow" style="height: 600px;"></div>
        </section>

    </main>
</div>

<script src="js/app.js"></script>
<script src="js/charts.js"></script>
<script src="js/map.js"></script>

</body>
</html>
```

- [ ] **Step 2: Create site/css/style.css**

```css
/* Custom overrides for Tailwind + component styles */

[x-cloak] { display: none !important; }

/* Score colour classes */
.score-high { background-color: #059669; }
.score-medium { background-color: #d97706; }
.score-low { background-color: #dc2626; }

/* Leaflet container fix inside Tailwind */
#map-container .leaflet-container {
    height: 100%;
    width: 100%;
    border-radius: 0.5rem;
}

/* Plotly chart containers */
#chart-donut, #chart-forecast, #chart-scatter {
    min-height: 400px;
}
```

- [ ] **Step 3: Create site/js/app.js — Alpine.js application state**

```javascript
// Alpine.js application state for Arena Demand Scout
function demandScout() {
    return {
        // UI state
        activeTab: 'portfolio',
        activeSeries: 'series_b',
        loading: true,
        selectedStates: [],
        allStates: [],

        tabs: [
            { id: 'portfolio', label: 'Portfolio Overview' },
            { id: 'forecast', label: 'Demand Forecast' },
            { id: 'opportunity', label: 'Opportunity Scoring' },
            { id: 'map', label: 'Map' },
        ],

        // Data
        portfolio: null,
        projections: null,
        scores: null,

        get stateEntries() {
            if (!this.portfolio?.states) return [];
            return Object.entries(this.portfolio.states)
                .sort((a, b) => b[1].centres - a[1].centres);
        },

        async init() {
            try {
                const [portfolioRes, projectionsRes, scoresRes] = await Promise.all([
                    fetch('data/arena_portfolio.json').then(r => r.json()),
                    fetch('data/abs_projections.json').then(r => r.json()),
                    fetch('data/opportunity_scores.json').then(r => r.json()),
                ]);
                this.portfolio = portfolioRes;
                this.projections = projectionsRes;
                this.scores = scoresRes;

                this.allStates = Object.keys(this.projections.states);
                this.selectedStates = [...this.allStates];

                this.loading = false;

                // Render initial tab charts after DOM update
                this.$nextTick(() => this.renderTab());
            } catch (err) {
                console.error('Failed to load data:', err);
                this.loading = false;
            }
        },

        setTab(tabId) {
            this.activeTab = tabId;
            this.$nextTick(() => this.renderTab());
        },

        setSeries(series) {
            this.activeSeries = series;
            this.$nextTick(() => this.renderTab());
        },

        toggleState(state) {
            const idx = this.selectedStates.indexOf(state);
            if (idx >= 0) {
                this.selectedStates.splice(idx, 1);
            } else {
                this.selectedStates.push(state);
            }
            this.$nextTick(() => this.renderTab());
        },

        toggleAllStates() {
            if (this.selectedStates.length === this.allStates.length) {
                this.selectedStates = [];
            } else {
                this.selectedStates = [...this.allStates];
            }
            this.$nextTick(() => this.renderTab());
        },

        scoreColor(score) {
            if (score >= 70) return 'score-high';
            if (score >= 40) return 'score-medium';
            return 'score-low';
        },

        renderTab() {
            switch (this.activeTab) {
                case 'portfolio':
                    if (this.portfolio) renderDonutChart(this.portfolio);
                    break;
                case 'forecast':
                    if (this.projections) {
                        renderForecastChart(this.projections, this.activeSeries, this.selectedStates);
                        renderForecastSummary(this.projections, this.activeSeries);
                    }
                    break;
                case 'opportunity':
                    if (this.scores) renderScatterChart(this.scores);
                    break;
                case 'map':
                    if (this.scores) initMap(this.scores);
                    break;
            }
        },
    };
}
```

- [ ] **Step 4: Verify the page loads without errors**

Run: `cd site && python -m http.server 8000 &`
Open `http://localhost:8000` — confirm the page renders with header, tabs, and "Loading data..." message (charts won't work yet — that's Task 7).

- [ ] **Step 5: Commit**

```bash
git add site/index.html site/css/style.css site/js/app.js
git commit -m "feat: frontend shell — HTML structure, Tailwind, Alpine.js app state"
```

---

## Chunk 5: Frontend Charts + Map

### Task 7: Plotly.js charts

**Files:**
- Create: `site/js/charts.js`

- [ ] **Step 1: Implement charts.js — all three Plotly charts**

```javascript
// Plotly.js chart configurations for Arena Demand Scout

const STATE_COLORS = {
    NSW: '#2563eb', VIC: '#059669', QLD: '#d97706',
    SA: '#dc2626', WA: '#7c3aed', TAS: '#0891b2',
    NT: '#be185d', ACT: '#65a30d',
};

const PLOTLY_LAYOUT_BASE = {
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: { family: 'system-ui, sans-serif', color: '#334155' },
    margin: { t: 40, r: 20, b: 40, l: 60 },
};

const PLOTLY_CONFIG = { responsive: true, displayModeBar: false };


function renderDonutChart(portfolio) {
    const states = Object.keys(portfolio.states);
    const centres = states.map(s => portfolio.states[s].centres);

    const data = [{
        type: 'pie',
        hole: 0.5,
        labels: states,
        values: centres,
        marker: { colors: states.map(s => STATE_COLORS[s] || '#94a3b8') },
        textinfo: 'label+percent',
        textposition: 'outside',
        hovertemplate: '%{label}: %{value} centres<extra></extra>',
    }];

    const layout = {
        ...PLOTLY_LAYOUT_BASE,
        title: { text: 'Centre Distribution by State', font: { size: 16 } },
        showlegend: false,
    };

    Plotly.newPlot('chart-donut', data, layout, PLOTLY_CONFIG);
}


function renderForecastChart(projections, activeSeries, selectedStates) {
    const years = projections.projection_years;
    const traces = [];

    for (const state of selectedStates) {
        const stateData = projections.states[state];
        if (!stateData || !stateData[activeSeries]) continue;

        const pop = stateData[activeSeries].population_0_5;
        const color = STATE_COLORS[state] || '#94a3b8';

        // Main line (selected series)
        traces.push({
            x: years.slice(0, pop.length),
            y: pop,
            name: state,
            type: 'scatter',
            mode: 'lines',
            line: { color, width: 2 },
            hovertemplate: `${state}: %{y:,.0f}<extra>%{x}</extra>`,
        });

        // Confidence band (series A/C) — only if selected series is B
        if (activeSeries === 'series_b' && stateData.series_a && stateData.series_c) {
            const high = stateData.series_a.population_0_5;
            const low = stateData.series_c.population_0_5;
            const bandYears = years.slice(0, Math.min(high.length, low.length));

            traces.push({
                x: [...bandYears, ...bandYears.slice().reverse()],
                y: [...high.slice(0, bandYears.length), ...low.slice(0, bandYears.length).reverse()],
                fill: 'toself',
                fillcolor: color + '15',
                line: { color: 'transparent' },
                showlegend: false,
                hoverinfo: 'skip',
                type: 'scatter',
            });
        }
    }

    // "Today" line — rendered as a layout shape, not a trace
    const todayYear = new Date().getFullYear();

    const layout = {
        ...PLOTLY_LAYOUT_BASE,
        title: { text: 'Children Aged 0-5: Population Projections', font: { size: 16 } },
        xaxis: { title: 'Year', dtick: 2 },
        yaxis: { title: 'Population (0-5)', tickformat: ',.0f' },
        legend: { orientation: 'h', y: -0.15 },
        shapes: [{
            type: 'line', x0: todayYear, x1: todayYear,
            y0: 0, y1: 1, yref: 'paper',
            line: { color: '#94a3b8', width: 1, dash: 'dash' },
        }],
    };

    Plotly.newPlot('chart-forecast', traces, layout, PLOTLY_CONFIG);
}


function renderForecastSummary(projections, activeSeries) {
    const grid = document.getElementById('forecast-summary-grid');
    if (!grid) return;
    grid.innerHTML = '';

    const years = projections.projection_years;
    const idx2026 = years.indexOf(2026);
    const idx2031 = years.indexOf(2031);
    const idx2036 = years.indexOf(2036);

    for (const [state, data] of Object.entries(projections.states)) {
        const pop = data[activeSeries]?.population_0_5;
        if (!pop || idx2026 < 0) continue;

        const growth2031 = idx2031 >= 0
            ? ((pop[idx2031] - pop[idx2026]) / pop[idx2026] * 100).toFixed(1)
            : 'N/A';
        const growth2036 = idx2036 >= 0
            ? ((pop[idx2036] - pop[idx2026]) / pop[idx2026] * 100).toFixed(1)
            : 'N/A';

        const div = document.createElement('div');
        div.className = 'p-3 rounded bg-slate-50';
        div.innerHTML = `
            <p class="font-semibold text-slate-700">${state}</p>
            <p class="text-xs text-slate-500">2031: <span class="font-medium ${parseFloat(growth2031) > 0 ? 'text-green-600' : 'text-red-600'}">${growth2031 > 0 ? '+' : ''}${growth2031}%</span></p>
            <p class="text-xs text-slate-500">2036: <span class="font-medium ${parseFloat(growth2036) > 0 ? 'text-green-600' : 'text-red-600'}">${growth2036 > 0 ? '+' : ''}${growth2036}%</span></p>
        `;
        grid.appendChild(div);
    }
}


function renderScatterChart(scores) {
    const rankings = scores.rankings || [];

    const data = [{
        x: rankings.map(r => r.current_supply_density),
        y: rankings.map(r => r.demand_growth_pct),
        text: rankings.map(r => r.state),
        customdata: rankings.map(r => r.centre_count),
        mode: 'markers+text',
        type: 'scatter',
        textposition: 'top center',
        marker: {
            size: rankings.map(r => Math.max(10, r.centre_count / 3)),
            color: rankings.map(r => {
                if (r.opportunity_score >= 70) return '#059669';
                if (r.opportunity_score >= 40) return '#d97706';
                return '#dc2626';
            }),
            opacity: 0.8,
            line: { color: '#fff', width: 1 },
        },
        hovertemplate: '%{text}<br>Supply Density: %{x}<br>Demand Growth: %{y}%<br>Centres: %{customdata}<extra></extra>',
    }];

    const layout = {
        ...PLOTLY_LAYOUT_BASE,
        title: { text: 'Opportunity Matrix', font: { size: 16 } },
        xaxis: { title: 'Supply Density (centres per 1,000 children 0-5)' },
        yaxis: { title: 'Demand Growth % (2026-2031)' },
        // Quadrant lines at median
        shapes: rankings.length > 0 ? [{
            type: 'line',
            x0: median(rankings.map(r => r.current_supply_density)),
            x1: median(rankings.map(r => r.current_supply_density)),
            y0: 0, y1: 1, yref: 'paper',
            line: { color: '#cbd5e1', width: 1, dash: 'dot' },
        }, {
            type: 'line',
            y0: median(rankings.map(r => r.demand_growth_pct)),
            y1: median(rankings.map(r => r.demand_growth_pct)),
            x0: 0, x1: 1, xref: 'paper',
            line: { color: '#cbd5e1', width: 1, dash: 'dot' },
        }] : [],
    };

    Plotly.newPlot('chart-scatter', data, layout, PLOTLY_CONFIG);
}


function median(arr) {
    const sorted = [...arr].sort((a, b) => a - b);
    const mid = Math.floor(sorted.length / 2);
    return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}
```

- [ ] **Step 2: Verify charts render**

Run: `make build && make serve`
Open `http://localhost:8000` — confirm:
- Portfolio tab: donut chart shows state distribution
- Forecast tab: line chart with confidence bands, state toggles work
- Opportunity tab: scatter chart with coloured bubbles

- [ ] **Step 3: Commit**

```bash
git add site/js/charts.js
git commit -m "feat: Plotly.js charts — donut, forecast with confidence bands, opportunity scatter"
```

---

### Task 8: Leaflet map

**Files:**
- Create: `site/js/map.js`
- Create: `site/assets/geo/aus_states.geojson`

- [ ] **Step 1: Download simplified Australian state boundaries GeoJSON**

Search for a simplified (~50KB) Australian state boundaries GeoJSON. Good candidates:
- `https://raw.githubusercontent.com/rowanhogan/australian-states/master/states.geojson`
- Or create a simplified version from ABS ASGS boundaries

Download and save to `site/assets/geo/aus_states.geojson`. Verify it contains state/territory polygons with a `STATE_NAME` or equivalent property.

- [ ] **Step 2: Implement site/js/map.js**

```javascript
// Leaflet map for Arena Demand Scout

let mapInstance = null;

function initMap(scores) {
    const container = document.getElementById('map-container');
    if (!container) return;

    // Destroy existing map if re-rendering
    if (mapInstance) {
        mapInstance.remove();
        mapInstance = null;
    }

    mapInstance = L.map(container).setView([-28, 134], 4);

    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://carto.com/">CARTO</a>',
        maxZoom: 10,
    }).addTo(mapInstance);

    // Build score lookup
    const scoreLookup = {};
    for (const r of (scores.rankings || [])) {
        scoreLookup[r.state] = r;
    }

    // Load GeoJSON
    fetch('assets/geo/aus_states.geojson')
        .then(r => r.json())
        .then(geojson => {
            L.geoJSON(geojson, {
                style: feature => {
                    const stateName = feature.properties.STATE_NAME
                        || feature.properties.name
                        || feature.properties.STE_NAME21
                        || '';
                    const abbr = stateAbbr(stateName);
                    const entry = scoreLookup[abbr];
                    return {
                        fillColor: entry ? scoreToColor(entry.opportunity_score) : '#e2e8f0',
                        weight: 1,
                        opacity: 1,
                        color: '#94a3b8',
                        fillOpacity: 0.7,
                    };
                },
                onEachFeature: (feature, layer) => {
                    const stateName = feature.properties.STATE_NAME
                        || feature.properties.name
                        || feature.properties.STE_NAME21
                        || 'Unknown';
                    const abbr = stateAbbr(stateName);
                    const entry = scoreLookup[abbr];

                    if (entry) {
                        layer.bindPopup(`
                            <div class="text-sm">
                                <p class="font-bold">${stateName} (${abbr})</p>
                                <p>Centres: ${entry.centre_count}</p>
                                <p>Demand Growth: ${entry.demand_growth_pct}%</p>
                                <p>Supply Density: ${entry.current_supply_density}</p>
                                <p>Score: <strong>${entry.opportunity_score}</strong> (${entry.verdict})</p>
                            </div>
                        `);
                    }

                    layer.on('mouseover', () => layer.setStyle({ fillOpacity: 0.9, weight: 2 }));
                    layer.on('mouseout', () => layer.setStyle({ fillOpacity: 0.7, weight: 1 }));
                },
            }).addTo(mapInstance);
        })
        .catch(err => console.error('Failed to load GeoJSON:', err));
}


function scoreToColor(score) {
    if (score >= 70) return '#059669';  // green
    if (score >= 40) return '#d97706';  // amber
    return '#dc2626';                    // red
}


const STATE_ABBR_MAP = {
    'new south wales': 'NSW',
    'victoria': 'VIC',
    'queensland': 'QLD',
    'south australia': 'SA',
    'western australia': 'WA',
    'tasmania': 'TAS',
    'northern territory': 'NT',
    'australian capital territory': 'ACT',
};

function stateAbbr(name) {
    // Handle already-abbreviated
    if (name.length <= 3) return name.toUpperCase();
    return STATE_ABBR_MAP[name.toLowerCase()] || name;
}
```

- [ ] **Step 3: Verify map renders**

Run: `make serve`
Open `http://localhost:8000`, click Map tab. Confirm:
- Australia map visible with state boundaries
- States coloured by opportunity score (green/amber/red)
- Click a state → popup with stats
- Hover highlights state

- [ ] **Step 4: Commit**

```bash
git add site/js/map.js site/assets/geo/aus_states.geojson
git commit -m "feat: Leaflet choropleth map with state opportunity scores"
```

---

## Chunk 6: E2E Tests + Deployment

### Task 9: Playwright E2E tests

**Files:**
- Create: `tests/test_e2e.py`

- [ ] **Step 1: Install Playwright browsers**

Run: `uv run playwright install chromium`

- [ ] **Step 2: Write E2E tests**

Create `tests/test_e2e.py`:

```python
"""E2E tests — verify the static site renders correctly."""

import subprocess
import time
import urllib.request
import urllib.error
import pytest
from pathlib import Path
from playwright.sync_api import sync_playwright

SITE_DIR = Path(__file__).parent.parent / "site"
PORT = 8765


def _wait_for_server(url: str, timeout: float = 5.0) -> None:
    """Poll until the server responds or timeout."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1)
            return
        except (urllib.error.URLError, ConnectionError):
            time.sleep(0.2)
    raise RuntimeError(f"Server at {url} did not start within {timeout}s")


@pytest.fixture(scope="module")
def server():
    """Start a local HTTP server for the static site."""
    proc = subprocess.Popen(
        ["python", "-m", "http.server", str(PORT)],
        cwd=SITE_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://localhost:{PORT}"
    _wait_for_server(url)
    yield url
    proc.terminate()
    proc.wait()


@pytest.fixture(scope="module")
def page(server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        pg = browser.new_page()
        pg.goto(server)
        pg.wait_for_selector("[x-data]", timeout=5000)
        # Wait for data to load
        pg.wait_for_function("() => !document.querySelector('[x-data]').__x.$data.loading", timeout=10000)
        yield pg
        browser.close()


def test_page_title(page):
    assert "Arena Demand Scout" in page.title()


def test_header_visible(page):
    header = page.locator("header h1")
    assert header.is_visible()
    assert "Arena Demand Scout" in header.text_content()


def test_four_tabs_present(page):
    tabs = page.locator("nav button")
    assert tabs.count() == 4


def test_portfolio_tab_shows_table(page):
    page.locator("nav button", has_text="Portfolio Overview").click()
    page.wait_for_timeout(500)
    table = page.locator("section table")
    assert table.first.is_visible()


def test_portfolio_tab_shows_donut_chart(page):
    page.locator("nav button", has_text="Portfolio Overview").click()
    page.wait_for_timeout(500)
    chart = page.locator("#chart-donut .plot-container")
    assert chart.is_visible()


def test_forecast_tab_shows_chart(page):
    page.locator("nav button", has_text="Demand Forecast").click()
    page.wait_for_timeout(500)
    chart = page.locator("#chart-forecast .plot-container")
    assert chart.is_visible()


def test_forecast_state_toggles(page):
    page.locator("nav button", has_text="Demand Forecast").click()
    page.wait_for_timeout(500)
    buttons = page.locator("section button")
    assert buttons.count() > 1  # "All" + at least one state


def test_opportunity_tab_shows_table_and_chart(page):
    page.locator("nav button", has_text="Opportunity Scoring").click()
    page.wait_for_timeout(500)
    table = page.locator("section table")
    chart = page.locator("#chart-scatter .plot-container")
    assert table.first.is_visible()
    assert chart.is_visible()


def test_map_tab_renders(page):
    page.locator("nav button", has_text="Map").click()
    page.wait_for_timeout(1000)
    map_el = page.locator("#map-container .leaflet-container")
    assert map_el.is_visible()


def test_series_toggle_updates_charts(page):
    page.locator("nav button", has_text="Demand Forecast").click()
    page.wait_for_timeout(500)
    # Click "High" series
    page.locator("header button", has_text="High").click()
    page.wait_for_timeout(500)
    # Chart should still be visible (re-rendered with new data)
    chart = page.locator("#chart-forecast .plot-container")
    assert chart.is_visible()
```

- [ ] **Step 3: Run E2E tests**

Run: `make build && uv run pytest tests/test_e2e.py -v`
Expected: All 10 tests PASS

- [ ] **Step 4: Commit**

```bash
git add tests/test_e2e.py
git commit -m "test: Playwright E2E tests for all four tabs, charts, and controls"
```

---

### Task 10: GitHub Actions deployment

**Files:**
- Create: `.github/workflows/deploy.yml`

- [ ] **Step 1: Create the workflow file**

```yaml
name: Deploy to GitHub Pages

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Set up Python
        run: uv python install 3.12

      - name: Install dependencies
        run: uv sync

      - name: Run build pipeline
        run: uv run python build.py

      - name: Run tests
        run: uv run pytest tests/ -v --ignore=tests/test_e2e.py

      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: site/

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

- [ ] **Step 2: Commit**

```bash
mkdir -p .github/workflows
git add .github/workflows/deploy.yml
git commit -m "ci: GitHub Actions workflow for build + deploy to Pages"
```

---

### Task 11: Final integration run

- [ ] **Step 1: Clean build from scratch**

```bash
make clean && make build
```

Expected: All JSON files generated in site/data/

- [ ] **Step 2: Run all unit + integration tests**

```bash
make test
```

Expected: All tests PASS, zero warnings

- [ ] **Step 3: Run E2E tests**

```bash
make test-e2e
```

Expected: All tests PASS

- [ ] **Step 4: Visual verification**

Run: `make serve`
Open `http://localhost:8000`. Walk through all 4 tabs, toggle series, toggle states, click map states. Verify everything works.

- [ ] **Step 5: Final commit if any fixes were needed**

```bash
git add -A && git commit -m "fix: final integration fixes"
```
