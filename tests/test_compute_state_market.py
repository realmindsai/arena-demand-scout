"""Tests for state-level market statistics."""

from src.compute_state_market import compute_state_market_stats


def test_computes_market_stats():
    population = {
        "101": {"sa2_code": "101", "sa2_name": "A", "state_abbr": "NSW", "pop_0_4": 500},
        "102": {"sa2_code": "102", "sa2_name": "B", "state_abbr": "NSW", "pop_0_4": 300},
        "201": {"sa2_code": "201", "sa2_name": "C", "state_abbr": "VIC", "pop_0_4": 400},
    }
    supply = {
        "101": {"centre_count": 5, "approved_places": 200, "long_day_care": 3, "family_day_care": 1},
        "102": {"centre_count": 3, "approved_places": 100, "long_day_care": 2, "family_day_care": 0},
        "201": {"centre_count": 4, "approved_places": 150, "long_day_care": 2, "family_day_care": 1},
    }
    portfolio = {"states": {"NSW": {"centres": 2}, "VIC": {"centres": 1}}}
    sa2_scores = {"sa2_scores": [
        {"sa2_code": "101", "state_abbr": "NSW", "demand_score": 75},
        {"sa2_code": "102", "state_abbr": "NSW", "demand_score": 40},
        {"sa2_code": "201", "state_abbr": "VIC", "demand_score": 65},
    ]}

    result = compute_state_market_stats(population, supply, portfolio, sa2_scores)

    nsw = result["states"]["NSW"]
    assert nsw["total_centres"] == 8
    assert nsw["total_places"] == 300
    assert nsw["pop_0_4"] == 800
    assert nsw["children_per_centre"] == 100.0
    assert nsw["arena_centres"] == 2
    assert nsw["arena_market_share_pct"] == 25.0
    assert nsw["underserved_sa2"] == 1  # only score >= 60
    assert nsw["total_sa2"] == 2

    vic = result["states"]["VIC"]
    assert vic["arena_market_share_pct"] == 25.0
    assert vic["underserved_sa2"] == 1
    assert vic["family_day_care"] == 1
