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

    try:
        idx_2026 = years.index(2026)
    except ValueError:
        idx_2026 = 4

    try:
        idx_2031 = years.index(2031)
    except ValueError:
        idx_2031 = 9

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
