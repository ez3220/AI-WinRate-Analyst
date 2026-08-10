"""V3.9 live-odds normalization and movement analysis."""
from dataclasses import dataclass
from typing import Iterable, Optional

@dataclass(frozen=True)
class OddsPoint:
    captured_at: str
    bookmaker: str
    market: str
    outcome: str
    point: Optional[float]
    decimal_odds: float


def movement(old: OddsPoint, new: OddsPoint) -> dict:
    delta = new.decimal_odds - old.decimal_odds
    direction = 'SHORTENED' if delta < 0 else 'DRIFTED' if delta > 0 else 'UNCHANGED'
    return {'delta': round(delta, 4), 'direction': direction}


def latest_by_outcome(rows: Iterable[OddsPoint]):
    latest = {}
    for row in rows:
        key = (row.bookmaker, row.market, row.outcome, row.point)
        if key not in latest or row.captured_at > latest[key].captured_at:
            latest[key] = row
    return list(latest.values())
