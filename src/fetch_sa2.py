"""Fetch and parse SA2-level population data and boundaries."""

import json
import math
import httpx
import openpyxl
from pathlib import Path

CACHE_DIR = Path(".abs_cache")

SA2_XLSX_FILENAME = "32350DS0001_2024.xlsx"
SA2_POPULATION_SOURCE = Path(__file__).parent / "data" / "sa2_population_source.json"
SA2_SUPPLY_SOURCE = Path(__file__).parent / "data" / "sa2_childcare_supply.json"

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


def load_sa2_population(cache_dir: Path | None = None) -> dict:
    """Load SA2 population data — from XLSX if cached, else from committed JSON.

    Prefers cached XLSX (local dev) but falls back to committed
    src/data/sa2_population_source.json for CI where the XLSX isn't available.
    """
    cache = cache_dir or CACHE_DIR
    xlsx_path = cache / SA2_XLSX_FILENAME
    if xlsx_path.exists():
        return parse_sa2_population_xlsx(xlsx_path)
    return json.loads(SA2_POPULATION_SOURCE.read_text())


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


def load_sa2_supply() -> dict:
    """Load childcare supply data per SA2 (from ACECQA national register).

    Returns: {sa2_code: {centre_count, approved_places, long_day_care}}
    """
    return json.loads(SA2_SUPPLY_SOURCE.read_text())


def merge_population_into_geojson(geojson: dict, population: dict, supply: dict | None = None) -> dict:
    """Merge SA2 population and supply data into GeoJSON feature properties.

    Adds: pop_0_4, state_abbr, children_per_sqkm, centre_count, approved_places,
          long_day_care, places_per_child
    """
    supply = supply or {}

    for feature in geojson["features"]:
        props = feature["properties"]
        sa2_code = str(props.get("sa2_code_2021", ""))

        pop_entry = population.get(sa2_code, {})
        pop_0_4 = pop_entry.get("pop_0_4", 0)
        state_abbr = pop_entry.get("state_abbr", STATE_CODE_TO_ABBR.get(str(props.get("state_code_2021", "")), ""))

        area = props.get("area_albers_sqkm", 0) or 1
        children_per_sqkm = round(pop_0_4 / area, 2) if area > 0 else 0

        props["pop_0_4"] = pop_0_4
        props["state_abbr"] = state_abbr
        props["children_per_sqkm"] = children_per_sqkm

        # Supply data from ACECQA
        supply_entry = supply.get(sa2_code, {})
        centre_count = supply_entry.get("centre_count", 0)
        approved_places = supply_entry.get("approved_places", 0)
        long_day_care = supply_entry.get("long_day_care", 0)
        places_per_child = round(approved_places / pop_0_4, 2) if pop_0_4 > 0 else 0

        props["centre_count"] = centre_count
        props["approved_places"] = approved_places
        props["long_day_care"] = long_day_care
        props["places_per_child"] = places_per_child

    return geojson


CATCHMENT_RADIUS_KM = 5.0  # ~15 min drive in urban areas


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between two lat/lon points."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def compute_centroids(geojson: dict) -> dict:
    """Compute centroid (avg lat/lon) for each SA2 polygon.

    Returns: {sa2_code: (lat, lon)}
    """
    centroids = {}
    for feature in geojson["features"]:
        sa2_code = str(feature["properties"].get("sa2_code_2021", ""))
        geom = feature.get("geometry")
        if not geom:
            continue
        coords = geom.get("coordinates", [])

        all_points = []
        if geom["type"] == "MultiPolygon":
            for polygon in coords:
                for ring in polygon:
                    all_points.extend(ring)
        elif geom["type"] == "Polygon":
            for ring in coords:
                all_points.extend(ring)

        if all_points:
            avg_lon = sum(p[0] for p in all_points) / len(all_points)
            avg_lat = sum(p[1] for p in all_points) / len(all_points)
            centroids[sa2_code] = (avg_lat, avg_lon)

    return centroids


def compute_catchment_accessibility(
    centroids: dict,
    supply: dict,
    population: dict,
    radius_km: float = CATCHMENT_RADIUS_KM,
) -> dict:
    """Simplified Two-Step Floating Catchment Area (2SFCA) method.

    Step 1: For each SA2 with supply, compute supply-to-demand ratio
            within the catchment radius (supply / nearby population).
    Step 2: For each SA2, sum the supply ratios of all nearby supply
            SA2s within the catchment — this is the accessibility index.

    Uses Gaussian distance decay: w(d) = exp(-d²/β²) where β = radius/2.

    Reference: Luo & Wang (2003), "Measures of spatial accessibility
    to health care in a GIS environment"

    Returns: {sa2_code: {"accessible_places": float, "catchment_ppc": float}}
    """
    beta = radius_km / 2.0
    # Pre-filter: ~0.045° latitude per km at Australian latitudes
    lat_thresh = radius_km / 111.0
    lon_thresh = radius_km / 85.0  # ~85 km per degree longitude at -30°

    sa2_codes = list(centroids.keys())

    # Step 1: compute supply-to-demand ratio Rj for each supply SA2 j
    supply_ratios = {}
    supply_sa2s = [(code, supply[code]) for code in sa2_codes
                   if code in supply and supply[code].get("approved_places", 0) > 0]

    for code_j, supply_j in supply_sa2s:
        if code_j not in centroids:
            continue
        lat_j, lon_j = centroids[code_j]
        places_j = supply_j["approved_places"]

        # Sum demand within catchment
        catchment_demand = 0
        for code_k in sa2_codes:
            pop_k = population.get(code_k, {}).get("pop_0_4", 0)
            if pop_k == 0:
                continue
            lat_k, lon_k = centroids.get(code_k, (0, 0))
            if abs(lat_k - lat_j) > lat_thresh or abs(lon_k - lon_j) > lon_thresh:
                continue
            dist = haversine_km(lat_j, lon_j, lat_k, lon_k)
            if dist <= radius_km:
                weight = math.exp(-(dist ** 2) / (beta ** 2))
                catchment_demand += pop_k * weight

        if catchment_demand > 0:
            supply_ratios[code_j] = places_j / catchment_demand
        else:
            supply_ratios[code_j] = 0

    # Step 2: for each SA2, sum supply ratios within catchment
    result = {}
    for code_i in sa2_codes:
        if code_i not in centroids:
            result[code_i] = {"accessible_places": 0, "catchment_ppc": 0}
            continue
        lat_i, lon_i = centroids[code_i]
        pop_i = population.get(code_i, {}).get("pop_0_4", 0)

        accessibility = 0.0
        for code_j, _ in supply_sa2s:
            if code_j not in centroids or code_j not in supply_ratios:
                continue
            lat_j, lon_j = centroids[code_j]
            if abs(lat_j - lat_i) > lat_thresh or abs(lon_j - lon_i) > lon_thresh:
                continue
            dist = haversine_km(lat_i, lon_i, lat_j, lon_j)
            if dist <= radius_km:
                weight = math.exp(-(dist ** 2) / (beta ** 2))
                accessibility += supply_ratios[code_j] * weight

        result[code_i] = {
            "accessible_places": round(accessibility * pop_i, 1) if pop_i > 0 else 0,
            "catchment_ppc": round(accessibility, 3),
        }

    return result


def build_sa2_data(cache_dir: Path | None = None) -> tuple[dict, dict]:
    """Full SA2 pipeline: download XLSX, fetch boundaries, merge.

    Returns: (merged_geojson, population_dict)
    """
    cache = cache_dir or CACHE_DIR

    print("Loading SA2 population data...")
    population = load_sa2_population(cache_dir=cache)
    print(f"  Found {len(population)} SA2 regions")

    print("Fetching SA2 boundaries from ABS ArcGIS...")
    geojson = fetch_sa2_boundaries(cache_dir=cache)
    print(f"  Got {len(geojson['features'])} boundary features")

    print("Loading childcare supply data (ACECQA)...")
    supply = load_sa2_supply()
    print(f"  {len(supply)} SA2 regions with childcare centres")

    print("Merging population + supply into boundaries...")
    merged = merge_population_into_geojson(geojson, population, supply)

    print("Computing 2SFCA catchment accessibility (5km radius)...")
    centroids = compute_centroids(merged)
    catchment = compute_catchment_accessibility(centroids, supply, population)
    # Merge catchment data into GeoJSON properties
    for feature in merged["features"]:
        sa2_code = str(feature["properties"].get("sa2_code_2021", ""))
        ca = catchment.get(sa2_code, {})
        feature["properties"]["accessible_places"] = ca.get("accessible_places", 0)
        feature["properties"]["catchment_ppc"] = ca.get("catchment_ppc", 0)
    print(f"  Computed catchment accessibility for {len(catchment)} SA2 regions")

    return merged, population
