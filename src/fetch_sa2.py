"""Fetch and parse SA2-level population data and boundaries."""

import json
import httpx
import openpyxl
from pathlib import Path

CACHE_DIR = Path(".abs_cache")

SA2_XLSX_FILENAME = "32350DS0001_2024.xlsx"
SA2_XLSX_URL = (
    "https://www.abs.gov.au/statistics/people/population/"
    "regional-population-age-sex/2024/32350DS0001_2024.xlsx"
)

# XLSX structure (Table 3 — Persons)
SA2_XLSX_SHEET = "Table 3"
SA2_XLSX_DATA_START_ROW = 7
STATE_CODE_COL = 0
STATE_NAME_COL = 1
SA2_CODE_COL = 8
SA2_NAME_COL = 9
SA2_POP_0_4_COL = 10

# ABS ArcGIS endpoint for SA2 boundaries (ASGS 2021 edition)
ARCGIS_SA2_URL = (
    "https://geo.abs.gov.au/arcgis/rest/services/ASGS2021/SA2/MapServer/0/query"
)
ARCGIS_PAGE_SIZE = 2000
ARCGIS_SIMPLIFY_OFFSET = 0.01  # ~1km simplification

STATE_CODE_TO_ABBR = {
    "1": "NSW", "2": "VIC", "3": "QLD", "4": "SA",
    "5": "WA", "6": "TAS", "7": "NT", "8": "ACT",
}


def download_sa2_xlsx(cache_dir: Path | None = None) -> Path:
    """Download SA2 population XLSX if not cached."""
    cache = cache_dir or CACHE_DIR
    dest = cache / SA2_XLSX_FILENAME
    if dest.exists():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    resp = httpx.get(SA2_XLSX_URL, follow_redirects=True, timeout=60)
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    return dest


def parse_sa2_population_xlsx(xlsx_path: Path) -> dict:
    """Parse ABS Cat 3235.0 XLSX for SA2-level 0-4 population.

    Returns: {sa2_code: {sa2_code, sa2_name, state_code, state_name, state_abbr, pop_0_4}}
    """
    wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
    ws = wb[SA2_XLSX_SHEET]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()

    result = {}
    for row in rows[SA2_XLSX_DATA_START_ROW:]:
        if not row or not row[SA2_CODE_COL]:
            continue

        state_code = str(row[STATE_CODE_COL])
        sa2_name = str(row[SA2_NAME_COL] or "")

        # Skip Other Territories and total/summary rows
        if state_code == "9":
            continue
        if "Total" in sa2_name:
            continue

        sa2_code = str(row[SA2_CODE_COL])
        pop_0_4 = row[SA2_POP_0_4_COL]
        if pop_0_4 is None:
            pop_0_4 = 0

        result[sa2_code] = {
            "sa2_code": sa2_code,
            "sa2_name": sa2_name,
            "state_code": state_code,
            "state_name": str(row[STATE_NAME_COL]),
            "state_abbr": STATE_CODE_TO_ABBR.get(state_code, ""),
            "pop_0_4": int(pop_0_4),
        }

    return result


def fetch_sa2_boundaries(cache_dir: Path | None = None) -> dict:
    """Fetch simplified SA2 boundaries from ABS ArcGIS REST API.

    Returns GeoJSON FeatureCollection with simplified polygons.
    Caches the result to avoid repeated API calls.
    """
    cache = cache_dir or CACHE_DIR
    cache.mkdir(parents=True, exist_ok=True)
    cached = cache / "sa2_boundaries.geojson"
    if cached.exists():
        return json.loads(cached.read_text())

    all_features = []
    offset = 0

    while True:
        print(f"  Fetching SA2 boundaries (offset={offset})...")
        resp = httpx.get(
            ARCGIS_SA2_URL,
            params={
                "where": "state_code_2021 IN ('1','2','3','4','5','6','7','8')",
                "outFields": "sa2_code_2021,sa2_name_2021,state_code_2021,state_name_2021,area_albers_sqkm",
                "outSR": "4326",
                "f": "geojson",
                "maxAllowableOffset": str(ARCGIS_SIMPLIFY_OFFSET),
                "resultOffset": str(offset),
                "resultRecordCount": str(ARCGIS_PAGE_SIZE),
            },
            timeout=120,
        )
        resp.raise_for_status()
        page = resp.json()
        features = page.get("features", [])
        if not features:
            break
        all_features.extend(features)
        offset += len(features)
        if len(features) < ARCGIS_PAGE_SIZE:
            break

    geojson = {"type": "FeatureCollection", "features": all_features}
    cached.write_text(json.dumps(geojson))
    print(f"  Cached {len(all_features)} SA2 boundaries to {cached}")
    return geojson


def merge_population_into_geojson(geojson: dict, population: dict) -> dict:
    """Merge SA2 population data into GeoJSON feature properties.

    Adds: pop_0_4, state_abbr, children_per_sqkm
    """
    for feature in geojson["features"]:
        props = feature["properties"]
        sa2_code = str(props.get("sa2_code_2021", ""))

        pop_entry = population.get(sa2_code, {})
        pop_0_4 = pop_entry.get("pop_0_4", 0)
        state_abbr = pop_entry.get("state_abbr", STATE_CODE_TO_ABBR.get(str(props.get("state_code_2021", "")), ""))

        area = props.get("area_albers_sqkm", 0) or 1  # avoid division by zero
        children_per_sqkm = round(pop_0_4 / area, 2) if area > 0 else 0

        props["pop_0_4"] = pop_0_4
        props["state_abbr"] = state_abbr
        props["children_per_sqkm"] = children_per_sqkm

    return geojson


def build_sa2_data(cache_dir: Path | None = None) -> tuple[dict, dict]:
    """Full SA2 pipeline: download XLSX, fetch boundaries, merge.

    Returns: (merged_geojson, population_dict)
    """
    cache = cache_dir or CACHE_DIR

    print("Downloading SA2 population XLSX...")
    xlsx_path = download_sa2_xlsx(cache_dir=cache)

    print("Parsing SA2 population data...")
    population = parse_sa2_population_xlsx(xlsx_path)
    print(f"  Found {len(population)} SA2 regions")

    print("Fetching SA2 boundaries from ABS ArcGIS...")
    geojson = fetch_sa2_boundaries(cache_dir=cache)
    print(f"  Got {len(geojson['features'])} boundary features")

    print("Merging population into boundaries...")
    merged = merge_population_into_geojson(geojson, population)

    return merged, population
