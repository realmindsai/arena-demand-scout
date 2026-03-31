"""Tests for SA2 population data fetching and parsing."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.fetch_sa2 import (
    parse_sa2_population_xlsx,
    merge_population_into_geojson,
    haversine_km,
    compute_centroids,
    compute_catchment_accessibility,
    SA2_XLSX_DATA_START_ROW,
    SA2_POP_0_4_COL,
    SA2_CODE_COL,
    SA2_NAME_COL,
    STATE_CODE_COL,
    STATE_NAME_COL,
)


@pytest.fixture
def sample_sa2_population():
    """Minimal SA2 population data for testing."""
    return {
        "101021007": {
            "sa2_code": "101021007",
            "sa2_name": "Braidwood",
            "state_code": "1",
            "state_name": "New South Wales",
            "state_abbr": "NSW",
            "pop_0_4": 208,
        },
        "201011001": {
            "sa2_code": "201011001",
            "sa2_name": "Alfredton",
            "state_code": "2",
            "state_name": "Victoria",
            "state_abbr": "VIC",
            "pop_0_4": 520,
        },
    }


@pytest.fixture
def sample_sa2_geojson():
    """Minimal SA2 GeoJSON for testing."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "sa2_code_2021": "101021007",
                    "sa2_name_2021": "Braidwood",
                    "state_code_2021": "1",
                    "state_name_2021": "New South Wales",
                    "area_albers_sqkm": 3418.35,
                },
                "geometry": {"type": "Polygon", "coordinates": [[[149.0, -35.0], [149.5, -35.0], [149.5, -35.5], [149.0, -35.0]]]},
            },
            {
                "type": "Feature",
                "properties": {
                    "sa2_code_2021": "201011001",
                    "sa2_name_2021": "Alfredton",
                    "state_code_2021": "2",
                    "state_name_2021": "Victoria",
                    "area_albers_sqkm": 15.2,
                },
                "geometry": {"type": "Polygon", "coordinates": [[[143.8, -37.5], [143.9, -37.5], [143.9, -37.6], [143.8, -37.5]]]},
            },
        ],
    }


class TestParseSa2PopulationXlsx:
    def test_parses_real_xlsx_if_available(self):
        """Parse real SA2 XLSX if cached."""
        xlsx_path = Path(".abs_cache/32350DS0001_2024.xlsx")
        if not xlsx_path.exists():
            pytest.skip("SA2 XLSX not cached")

        result = parse_sa2_population_xlsx(xlsx_path)

        assert len(result) > 2000, f"Expected >2000 SA2 regions, got {len(result)}"

        # Check a known SA2
        braidwood = result.get("101021007")
        assert braidwood is not None, "Braidwood SA2 not found"
        assert braidwood["sa2_name"] == "Braidwood"
        assert braidwood["state_abbr"] == "NSW"
        assert braidwood["pop_0_4"] > 0

    def test_excludes_other_territories(self):
        """State code 9 (Other Territories) should be excluded."""
        xlsx_path = Path(".abs_cache/32350DS0001_2024.xlsx")
        if not xlsx_path.exists():
            pytest.skip("SA2 XLSX not cached")

        result = parse_sa2_population_xlsx(xlsx_path)
        for sa2 in result.values():
            assert sa2["state_code"] != "9", f"Other Territories SA2 found: {sa2}"

    def test_excludes_total_rows(self):
        """Rows with 'Total' in SA2 name should be excluded."""
        xlsx_path = Path(".abs_cache/32350DS0001_2024.xlsx")
        if not xlsx_path.exists():
            pytest.skip("SA2 XLSX not cached")

        result = parse_sa2_population_xlsx(xlsx_path)
        for sa2 in result.values():
            assert "Total" not in sa2["sa2_name"], f"Total row included: {sa2}"

    def test_all_entries_have_required_fields(self):
        """Every SA2 entry must have all required fields."""
        xlsx_path = Path(".abs_cache/32350DS0001_2024.xlsx")
        if not xlsx_path.exists():
            pytest.skip("SA2 XLSX not cached")

        result = parse_sa2_population_xlsx(xlsx_path)
        required = {"sa2_code", "sa2_name", "state_code", "state_name", "state_abbr", "pop_0_4"}
        for code, entry in result.items():
            assert required.issubset(entry.keys()), f"Missing fields in {code}: {required - entry.keys()}"
            assert entry["pop_0_4"] >= 0


class TestMergePopulationIntoGeojson:
    def test_merges_population_data(self, sample_sa2_population, sample_sa2_geojson):
        """Population data gets merged into GeoJSON properties."""
        result = merge_population_into_geojson(sample_sa2_geojson, sample_sa2_population)

        features = result["features"]
        assert len(features) == 2

        braidwood = features[0]["properties"]
        assert braidwood["pop_0_4"] == 208
        assert braidwood["state_abbr"] == "NSW"
        assert "children_per_sqkm" in braidwood
        assert braidwood["children_per_sqkm"] == round(208 / 3418.35, 2)

    def test_filters_features_without_population(self, sample_sa2_geojson):
        """Features with no matching population data are kept but flagged."""
        empty_pop = {}
        result = merge_population_into_geojson(sample_sa2_geojson, empty_pop)
        # Features without population data should still be present but with pop_0_4=0
        for f in result["features"]:
            assert f["properties"]["pop_0_4"] == 0

    def test_computes_density(self, sample_sa2_population, sample_sa2_geojson):
        """children_per_sqkm is correctly computed."""
        result = merge_population_into_geojson(sample_sa2_geojson, sample_sa2_population)

        alfredton = result["features"][1]["properties"]
        assert alfredton["children_per_sqkm"] == round(520 / 15.2, 2)


class TestHaversineKm:
    def test_zero_distance(self):
        assert haversine_km(-33.87, 151.21, -33.87, 151.21) == 0.0

    def test_sydney_to_melbourne(self):
        dist = haversine_km(-33.87, 151.21, -37.81, 144.96)
        assert 700 < dist < 900

    def test_short_distance(self):
        """Two points ~1km apart."""
        dist = haversine_km(-33.87, 151.21, -33.879, 151.21)
        assert 0.5 < dist < 2.0


class TestComputeCentroids:
    def test_computes_centroids(self, sample_sa2_geojson):
        centroids = compute_centroids(sample_sa2_geojson)
        assert "101021007" in centroids
        assert "201011001" in centroids
        lat, lon = centroids["101021007"]
        assert -36 < lat < -34
        assert 148 < lon < 150

    def test_skips_null_geometry(self):
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "properties": {"sa2_code_2021": "999"}, "geometry": None},
            ],
        }
        centroids = compute_centroids(geojson)
        assert "999" not in centroids


class TestComputeCatchmentAccessibility:
    @pytest.fixture
    def nearby_setup(self):
        """Two SA2s within 5km of each other, one with supply."""
        centroids = {
            "A": (-33.87, 151.21),
            "B": (-33.88, 151.22),  # ~1.5km away
        }
        supply = {
            "B": {"centre_count": 2, "approved_places": 100},
        }
        population = {
            "A": {"pop_0_4": 500},
            "B": {"pop_0_4": 300},
        }
        return centroids, supply, population

    def test_nearby_sa2_gets_accessibility(self, nearby_setup):
        centroids, supply, population = nearby_setup
        result = compute_catchment_accessibility(centroids, supply, population, radius_km=5.0)
        assert result["A"]["catchment_ppc"] > 0
        assert result["B"]["catchment_ppc"] > 0

    def test_supply_sa2_has_higher_accessibility(self, nearby_setup):
        centroids, supply, population = nearby_setup
        result = compute_catchment_accessibility(centroids, supply, population, radius_km=5.0)
        assert result["B"]["catchment_ppc"] >= result["A"]["catchment_ppc"]

    def test_distant_sa2_gets_zero(self):
        centroids = {
            "A": (-33.87, 151.21),
            "B": (-37.81, 144.96),  # Melbourne — far away
        }
        supply = {"B": {"centre_count": 1, "approved_places": 50}}
        population = {"A": {"pop_0_4": 500}, "B": {"pop_0_4": 300}}
        result = compute_catchment_accessibility(centroids, supply, population, radius_km=5.0)
        assert result["A"]["catchment_ppc"] == 0

    def test_no_supply_gives_zero(self):
        centroids = {"A": (-33.87, 151.21)}
        supply = {}
        population = {"A": {"pop_0_4": 500}}
        result = compute_catchment_accessibility(centroids, supply, population, radius_km=5.0)
        assert result["A"]["catchment_ppc"] == 0
        assert result["A"]["accessible_places"] == 0
