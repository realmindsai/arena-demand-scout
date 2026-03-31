# Arena Demand Scout — Design Spec

**Date:** 2026-03-31
**Status:** Approved
**Author:** DW + Claude

## Purpose

A static, interactive dashboard that overlays Arena REIT's public portfolio data against ABS population projections for children aged 0–5. Identifies which Australian states represent the highest-priority expansion opportunities for early learning centre (ELC) investment.

Built as a proof-of-concept to demonstrate AI-assisted development speed and analytical capability to Justin Bailey at Arena REIT. Uses only publicly available data — zero internal Arena information required.

## Architecture

```
BUILD PIPELINE (Python)                    STATIC SITE (GitHub Pages)
─────────────────────────                  ─────────────────────────
scrape_arena.py → arena_portfolio.json     site/
fetch_abs.py    → abs_projections.json       ├── index.html (4 tabs)
                  abs_erp_current.json       ├── css/style.css
compute_scores.py → opportunity_scores.json  ├── js/app.js, charts.js, map.js
                                             └── data/*.json (generated)
All JSON → site/data/
```

**Build pipeline:** Python scripts run via `uv run build.py`. Downloads ABS XLSX files, scrapes Arena's public portfolio page, processes everything into clean JSON. Runs locally or in a GitHub Action.

**Static site:** Single HTML page with four tabs. Alpine.js for reactive state (tab switching, filters). Plotly.js for charts. Leaflet.js for maps. Tailwind CSS via CDN for styling. Deployed to GitHub Pages.

## Data Pipeline

### Arena Portfolio Data (`scrape_arena.py`)

**Source:** Arena REIT ASX investor presentations and annual/half-year results PDFs. The portfolio website (arena.com.au/our-portfolio/) is JS-rendered with no machine-readable data — do not scrape it. Instead, the script parses the latest ASX results presentation PDF (downloaded from announcements.asx.com.au or arena.com.au/investors/).

**Fallback:** If PDF parsing proves unreliable, maintain a hand-curated `src/data/arena_portfolio_source.json` committed to the repo, with a comment noting the source document and date. The script then just copies/validates this file.

**Extracts:**
- Number of ELC centres per state
- Property valuations per state
- Metro vs regional percentage split
- Development pipeline count (centres under construction)

**Output:** `arena_portfolio.json`

```json
{
  "as_at": "2026-03-31",
  "source": "Arena REIT HY2026 Results Presentation",
  "states": {
    "VIC": {
      "centres": 79,
      "valuation_m": 512.3,
      "metro_pct": 72,
      "development_pipeline": 5
    }
  },
  "national": {
    "total_centres": 274,
    "total_valuation_m": 1842.0,
    "development_pipeline": 29
  }
}
```

### ABS Fetcher (`fetch_abs.py`)

**Sources:**
- ABS Population Projections 2022–2071 (XLSX tables A1–C9, one per state per series)
- ABS Estimated Resident Population Sep 2025 (XLSX tables 3101051–3101059)
- Summary/components file for capital city vs rest-of-state splits

**Download URLs:**
- Projections: `https://www.abs.gov.au/statistics/people/population/population-projections-australia/2022-base-2071/3222_Table_{SERIES}{NUM}.xlsx` (e.g. `3222_Table_B2.xlsx` for VIC medium series)
- ERP: `https://www.abs.gov.au/statistics/people/population/national-state-and-territory-population/latest-release` — download the single-year-of-age data cube. Exact filenames must be verified at build time as they change per release quarter.
- Summary: `Projected population, components of change and summary statistics, 2022 (base) to 2071.xlsx`

**Processing:** Reads XLSX Data1/Data2 sheets, sums single-year-of-age columns for ages 0 through 5, outputs annual totals per state. Projections capped at 2036 (10-year horizon).

**State mapping (projections tables only):** Table suffix 1=NSW, 2=VIC, 3=QLD, 4=SA, 5=WA, 6=TAS, 7=NT, 8=ACT, 9=Australia. ERP data uses a different file structure — the build script must discover the correct files from the ABS download page.

**Output:** `abs_projections.json`

```json
{
  "base_year": 2022,
  "projection_years": [2022, 2023, "...", 2036],
  "states": {
    "VIC": {
      "series_b": { "population_0_5": [405000, 408200, "...", 442000] },
      "series_a": { "..." },
      "series_c": { "..." }
    }
  },
  "erp_actual": {
    "VIC": {
      "population_0_5": [403500],
      "as_at": "2025-09-30"
    }
  }
}
```

### Opportunity Scorer (`compute_scores.py`)

**Inputs:** `arena_portfolio.json` + `abs_projections.json`

**Calculates per state:**
- Centre count — passed through from `arena_portfolio.json` (used for scatter chart bubble sizing)
- Demand growth % — projected 0–5 population change, 2026 to 2031, Series B
- Supply density — Arena centres per 1,000 children aged 0–5
- Opportunity score — deterministic composite:
  ```
  normalised_growth = (demand_growth_pct - min) / (max - min)  # 0–1 across states
  normalised_gap    = 1 - (supply_density - min) / (max - min) # 0–1, inverted (lower density = higher score)
  raw_score         = (0.6 * normalised_growth) + (0.4 * normalised_gap)
  opportunity_score = round(raw_score * 100)                   # 0–100
  ```
  Verdict thresholds: >= 70 "High priority", >= 40 "Medium priority", < 40 "Low priority"

**Output:** `opportunity_scores.json`

```json
{
  "rankings": [
    {
      "state": "VIC",
      "centre_count": 79,
      "demand_growth_pct": 8.2,
      "current_supply_density": 0.19,
      "opportunity_score": 87,
      "verdict": "High priority"
    }
  ]
}
```

## Frontend

### Global Controls (persistent across tabs)

- Projection series toggle: A (High) / B (Medium) / C (Low) — defaults to B
- Header with app title and data freshness timestamp

### Tab 1: Portfolio Overview

- Summary cards: total centres, total valuation, pipeline count
- State breakdown table: State | Centres | Valuation ($M) | Metro % | Pipeline
- Plotly donut chart: centre distribution by state

### Tab 2: Demand Forecast

- Plotly line chart: 0–5 population trajectory per state
  - Series B as solid line, A/C as shaded confidence band
  - Vertical dashed line at 2026 ("today") separating actual ERP from projections
- State selector: Alpine.js toggle buttons, default all states overlaid
- Year range slider: 2022–2036
- Summary stats table below chart: "VIC: +8.2% by 2031, +14.1% by 2036"

### Tab 3: Opportunity Scoring

- Heat-map table: rows = states (sorted by score desc), columns = demand growth %, supply density, score
- Cells colour-coded green/amber/red
- Plotly scatter: X = supply density, Y = demand growth %, bubble size = centre count
- Top-left quadrant (high demand, low supply) = best opportunities

### Tab 4: Map

- Leaflet map of Australia
- Choropleth overlay by state, coloured by opportunity score
- **GeoJSON source:** Simplified Australian state boundaries (~50KB). Use a public simplified GeoJSON (e.g. `github.com/rowanhogan/australian-states/blob/master/states.geojson` or equivalent). Committed to `site/assets/geo/aus_states.geojson` — not fetched at runtime. This directory is NOT gitignored (unlike `site/data/` which is generated).
- Click state → popup with key stats
- Optional: individual markers for childcare centres if ACECQA/data.gov.au data is available

## Styling

- Tailwind CSS via CDN — no build step for styles
- Colour palette: navy/white/teal base, green→amber→red for scoring
- Neutral "analytical tool" aesthetic — not Arena-branded
- Desktop-first, responsive as a bonus
- System font stack (no external font loading)

## Deployment

- GitHub Pages from `main` branch `/site` directory
- `build.py` is the single entry point: runs all data scripts, writes to `site/data/`
- Optional GitHub Action: on push → run build → deploy
- URL: `https://<org>.github.io/arena-demand-scout/`

## Testing

- **Unit tests:** Each data script tested for XLSX parsing correctness, JSON output schema, score calculation accuracy
- **Integration test:** `build.py` end-to-end — produces all JSON files, validates against schema
- **E2E test:** Playwright opens static site, verifies all four tabs render, charts load, filters respond
- Framework: `pytest` + `playwright`

## Project Structure

```
arena-demand-scout/
├── build.py
├── src/
│   ├── scrape_arena.py
│   ├── fetch_abs.py
│   ├── compute_scores.py
│   └── data/
│       └── arena_portfolio_source.json  (hand-curated fallback, committed)
├── site/
│   ├── index.html
│   ├── css/style.css
│   ├── js/
│   │   ├── app.js
│   │   ├── charts.js
│   │   └── map.js
│   ├── assets/
│   │   └── geo/aus_states.geojson  (committed, not generated)
│   └── data/               (gitignored, generated by build)
├── tests/
│   ├── test_scrape_arena.py
│   ├── test_fetch_abs.py
│   ├── test_compute_scores.py
│   └── test_e2e.py
├── pyproject.toml
├── Makefile
└── .github/workflows/deploy.yml
```

## Out of Scope

- AI/LLM chat component — scrapped
- Internal Arena data (tenant occupancy, lease terms)
- Sub-state geographic granularity (SA2/SA3 level)
- Real-time data feeds
