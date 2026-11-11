from app.models import ScoreResult

# How much each factor counts (adds up to 100). These are our own choice.
WEIGHTS = {"demand": 30, "competition": 25, "market": 20, "economics": 25}
DEMAND = {"high": 100, "medium": 65, "low": 25}        # "unclear" is not in the table on purpose
COMPETITION = {"low": 90, "medium": 65, "high": 35}    # less competition = better for us
NEUTRAL = 40   # points given to a factor we have no data for

def score_idea(demand, competitors, finance) -> ScoreResult:
    pts: dict[str, int | None] = {
        "demand": DEMAND.get(demand.demand_level) if demand else None,
        "competition": COMPETITION.get(competitors.competition_level) if competitors else None,
        "market": None, "economics": None,
    }
    if finance:
        # Market: yearly revenue we could realistically win (SOM, in USD)
        s = finance.som
        pts["market"] = 100 if s >= 1_000_000 else 75 if s >= 250_000 else 50 if s >= 50_000 else 25
        # Economics: LTV:CAC ratio, and whether we can ever break even
        r = finance.ltv_cac_ratio
        if finance.break_even_users is None:
            pts["economics"] = 10
        elif r is not None:
            pts["economics"] = 100 if r >= 3 else 70 if r >= 2 else 40 if r >= 1 else 15

    unknown = [k for k, v in pts.items() if v is None]
    final = {k: (v if v is not None else NEUTRAL) for k, v in pts.items()}
    total = round(sum(WEIGHTS[k] * final[k] for k in WEIGHTS) / 100)

    # Too many unknowns means a number would look more certain than it is
    if len(unknown) >= 2:
        verdict = "Insufficient data"
    else:
        verdict = "Go" if total >= 70 else "Pivot" if total >= 45 else "No-Go"
    return ScoreResult(total=total, verdict=verdict, breakdown=final, unknown_factors=unknown)