"""Tests for SA2-level geographic scoring."""

import pytest
from src.compute_sa2_scores import compute_sa2_scores, get_sa2_verdict


class TestComputeSa2Scores:
    @pytest.fixture
    def sample_geojson(self):
        """GeoJSON with merged population data."""
        return {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "sa2_code_2021": "101021007",
                        "sa2_name_2021": "Rural Area",
                        "state_code_2021": "1",
                        "state_abbr": "NSW",
                        "area_albers_sqkm": 3000.0,
                        "pop_0_4": 200,
                        "children_per_sqkm": 0.07,
                    },
                    "geometry": {"type": "Polygon", "coordinates": [[[149, -35], [150, -35], [150, -36], [149, -35]]]},
                },
                {
                    "type": "Feature",
                    "properties": {
                        "sa2_code_2021": "201011001",
                        "sa2_name_2021": "Dense Suburb",
                        "state_code_2021": "2",
                        "state_abbr": "VIC",
                        "area_albers_sqkm": 5.0,
                        "pop_0_4": 800,
                        "children_per_sqkm": 160.0,
                    },
                    "geometry": {"type": "Polygon", "coordinates": [[[144, -37], [145, -37], [145, -38], [144, -37]]]},
                },
                {
                    "type": "Feature",
                    "properties": {
                        "sa2_code_2021": "301011001",
                        "sa2_name_2021": "Medium Town",
                        "state_code_2021": "3",
                        "state_abbr": "QLD",
                        "area_albers_sqkm": 50.0,
                        "pop_0_4": 500,
                        "children_per_sqkm": 10.0,
                    },
                    "geometry": {"type": "Polygon", "coordinates": [[[153, -27], [154, -27], [154, -28], [153, -27]]]},
                },
            ],
        }

    def test_returns_scored_list(self, sample_geojson):
        result = compute_sa2_scores(sample_geojson)
        assert "sa2_scores" in result
        assert len(result["sa2_scores"]) == 3

    def test_scores_sorted_descending(self, sample_geojson):
        result = compute_sa2_scores(sample_geojson)
        scores = [s["demand_score"] for s in result["sa2_scores"]]
        assert scores == sorted(scores, reverse=True)

    def test_score_range_0_100(self, sample_geojson):
        result = compute_sa2_scores(sample_geojson)
        for entry in result["sa2_scores"]:
            assert 0 <= entry["demand_score"] <= 100

    def test_higher_pop_gets_higher_score(self, sample_geojson):
        result = compute_sa2_scores(sample_geojson)
        by_code = {s["sa2_code"]: s for s in result["sa2_scores"]}
        # Dense Suburb (800 kids, 160/sqkm) should score higher than Rural Area (200 kids, 0.07/sqkm)
        assert by_code["201011001"]["demand_score"] > by_code["101021007"]["demand_score"]

    def test_has_required_fields(self, sample_geojson):
        result = compute_sa2_scores(sample_geojson)
        required = {"sa2_code", "sa2_name", "state_abbr", "pop_0_4", "children_per_sqkm", "demand_score", "verdict"}
        for entry in result["sa2_scores"]:
            assert required.issubset(entry.keys()), f"Missing: {required - entry.keys()}"

    def test_includes_summary_stats(self, sample_geojson):
        result = compute_sa2_scores(sample_geojson)
        assert "total_sa2_regions" in result
        assert result["total_sa2_regions"] == 3


class TestGetSa2Verdict:
    def test_high(self):
        assert get_sa2_verdict(80) == "High demand"

    def test_medium(self):
        assert get_sa2_verdict(50) == "Medium demand"

    def test_low(self):
        assert get_sa2_verdict(20) == "Low demand"

    def test_boundary_high(self):
        assert get_sa2_verdict(70) == "High demand"

    def test_boundary_medium(self):
        assert get_sa2_verdict(40) == "Medium demand"
