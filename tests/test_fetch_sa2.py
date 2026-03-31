"""Tests for SA2 population data fetching and parsing."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.fetch_sa2 import (
    parse_sa2_population_xlsx,
    merge_population_into_geojson,
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
