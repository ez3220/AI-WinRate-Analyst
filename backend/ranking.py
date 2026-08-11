"""EV ranking and upset radar. Pure ranking only; no data fetching."""
from __future__ import annotations


def rank_ev(rows: list[dict], limit: int = 3) -> list[dict]:
    eligible = [r for r in rows if r.get('status') == 'scored' and r.get('ev') is not None and r.get('decision') in {'BET', 'LEAN'}]
    return sorted(eligible, key=lambda r: (r.get('ev') or -1, r.get('edge') or -1, r.get('ai_score') or -1), reverse=True)[:limit]


def upset_score(model_probability: float | None, market_probability: float | None) -> float | None:
    if model_probability is None or market_probability is None:
        return None
    # Positive only when the model materially disagrees with the market.
    edge = model_probability - market_probability
    if edge <= 0:
        return 0.0
    return round(min(100.0, edge * 200.0), 1)


def rank_upsets(rows: list[dict], limit: int = 3) -> list[dict]:
    scored = []
    for row in rows:
        score = upset_score(row.get('probability'), row.get('market_probability'))
        if score is not None and score >= 10:
            item = dict(row)
            item['upset_score'] = score
            scored.append(item)
    return sorted(scored, key=lambda r: (r['upset_score'], r.get('ev') or -1), reverse=True)[:limit]
