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
