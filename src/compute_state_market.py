"""Compute state-level market statistics from SA2 supply and population data."""

from collections import defaultdict


def compute_state_market_stats(
    population: dict,
    supply: dict,
    portfolio: dict,
    sa2_scores: dict,
) -> dict:
    """Aggregate SA2 data to state level for market overview.

    Returns per-state: total centres, places, children per centre,
    Arena market share, underserved SA2 count.
    """
    state_agg = defaultdict(lambda: {
        "total_centres": 0,
        "total_places": 0,
        "long_day_care": 0,
        "family_day_care": 0,
        "pop_0_4": 0,
    })

    for sa2_code, entry in population.items():
        state = entry["state_abbr"]
        state_agg[state]["pop_0_4"] += entry["pop_0_4"]
        s = supply.get(sa2_code, {})
        state_agg[state]["total_centres"] += s.get("centre_count", 0)
        state_agg[state]["total_places"] += s.get("approved_places", 0)
        state_agg[state]["long_day_care"] += s.get("long_day_care", 0)
        state_agg[state]["family_day_care"] += s.get("family_day_care", 0)

    # Underserved SA2 counts (demand_score >= 60)
    underserved = defaultdict(int)
    total_sa2 = defaultdict(int)
    for sa2 in sa2_scores.get("sa2_scores", []):
        total_sa2[sa2["state_abbr"]] += 1
        if sa2["demand_score"] >= 60:
            underserved[sa2["state_abbr"]] += 1

    result = {}
    for state, agg in state_agg.items():
        arena_centres = portfolio.get("states", {}).get(state, {}).get("centres", 0)
        centres = agg["total_centres"]
        places = agg["total_places"]
        pop = agg["pop_0_4"]

        result[state] = {
            "pop_0_4": pop,
            "total_centres": centres,
            "total_places": places,
            "long_day_care": agg["long_day_care"],
            "family_day_care": agg["family_day_care"],
            "children_per_centre": round(pop / centres, 1) if centres > 0 else 0,
            "children_per_place": round(pop / places, 2) if places > 0 else 0,
            "arena_centres": arena_centres,
            "arena_market_share_pct": round(arena_centres / centres * 100, 2) if centres > 0 else 0,
            "underserved_sa2": underserved.get(state, 0),
            "total_sa2": total_sa2.get(state, 0),
        }

    return {"states": result}
