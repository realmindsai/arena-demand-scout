"""Compute SA2-level geographic demand scores."""


def get_sa2_verdict(score: int) -> str:
    if score >= 70:
        return "High opportunity"
    elif score >= 40:
        return "Medium opportunity"
    return "Low opportunity"


def compute_sa2_scores(merged_geojson: dict) -> dict:
    """Score each SA2 region by demand (children) vs supply (centres).

    Uses percentile ranking across three factors:
        - children_per_sqkm (40%): density of demand
        - pop_0_4 (30%): raw market size
        - supply_gap (30%): inverse of places_per_child (fewer places = higher opportunity)

    Formula:
        raw_score = 0.4 * density_pctile + 0.3 * pop_pctile + 0.3 * supply_gap_pctile
        demand_score = round(raw_score * 100)           # 0-100
    """
    entries = []
    for feature in merged_geojson["features"]:
        props = feature["properties"]
        pop_0_4 = props.get("pop_0_4", 0)
        density = props.get("children_per_sqkm", 0)
        centre_count = props.get("centre_count", 0)
        approved_places = props.get("approved_places", 0)
        places_per_child = props.get("places_per_child", 0)

        entries.append({
            "sa2_code": str(props.get("sa2_code_2021", "")),
            "sa2_name": str(props.get("sa2_name_2021", "")),
            "state_abbr": props.get("state_abbr", ""),
            "pop_0_4": pop_0_4,
            "children_per_sqkm": density,
            "centre_count": centre_count,
            "approved_places": approved_places,
            "places_per_child": places_per_child,
        })

    if not entries:
        return {"sa2_scores": [], "total_sa2_regions": 0}

    n = len(entries)

    # Compute percentile ranks
    density_sorted = sorted(range(n), key=lambda i: entries[i]["children_per_sqkm"])
    pop_sorted = sorted(range(n), key=lambda i: entries[i]["pop_0_4"])
    # Supply gap: lower places_per_child = higher opportunity (inverted rank)
    supply_sorted = sorted(range(n), key=lambda i: entries[i]["places_per_child"], reverse=True)

    density_rank = [0] * n
    pop_rank = [0] * n
    supply_rank = [0] * n
    for rank, idx in enumerate(density_sorted):
        density_rank[idx] = rank
    for rank, idx in enumerate(pop_sorted):
        pop_rank[idx] = rank
    for rank, idx in enumerate(supply_sorted):
        supply_rank[idx] = rank

    for i, entry in enumerate(entries):
        density_pctile = density_rank[i] / max(n - 1, 1)
        pop_pctile = pop_rank[i] / max(n - 1, 1)
        supply_pctile = supply_rank[i] / max(n - 1, 1)
        raw_score = 0.4 * density_pctile + 0.3 * pop_pctile + 0.3 * supply_pctile
        entry["demand_score"] = max(0, min(100, round(raw_score * 100)))
        entry["verdict"] = get_sa2_verdict(entry["demand_score"])

    entries.sort(key=lambda e: e["demand_score"], reverse=True)

    return {
        "sa2_scores": entries,
        "total_sa2_regions": len(entries),
    }
