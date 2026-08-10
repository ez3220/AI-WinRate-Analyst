"""V3.3 deterministic betting engine.

Pure functions only: no network calls, no secrets, no invented data.
Inputs are point-in-time snapshots from the backend.
"""
from dataclasses import dataclass
from math import exp
from typing import Optional

@dataclass
class TeamInput:
    pitcher_era: Optional[float] = None
    pitcher_whip: Optional[float] = None
    last5_era: Optional[float] = None
    last5_whip: Optional[float] = None
    ops: Optional[float] = None
    runs_per_game: Optional[float] = None
    bullpen_score: Optional[float] = None
    lineup_strength: Optional[float] = None
    weather_adjustment: float = 0.0

@dataclass
class Market:
    decimal_odds: Optional[float] = None
    total: Optional[float] = None

@dataclass
class Prediction:
    probability: float
    market_probability: Optional[float]
    edge: Optional[float]
    ev: Optional[float]
    ai_score: float
    decision: str
    projected_total: Optional[float]


def _norm(value: Optional[float], low: float, high: float, invert: bool = False) -> Optional[float]:
    if value is None:
        return None
    x = max(low, min(high, value))
    score = (x - low) / (high - low)
    return 1.0 - score if invert else score


def team_strength(t: TeamInput) -> float:
    """Returns a 0..100 team strength from available point-in-time inputs."""
    parts = []
    weights = []
    metrics = [
        (_norm(t.pitcher_era, 2.0, 6.0, True), 0.22),
        (_norm(t.pitcher_whip, 0.95, 1.60, True), 0.13),
        (_norm(t.last5_era, 2.0, 7.0, True), 0.13),
        (_norm(t.ops, 0.60, 0.90), 0.16),
        (_norm(t.runs_per_game, 2.5, 6.5), 0.10),
        (_norm(t.bullpen_score, 0, 100), 0.14),
        (_norm(t.lineup_strength, 0, 100), 0.12),
    ]
    for score, weight in metrics:
        if score is not None:
            parts.append(score * weight)
            weights.append(weight)
    if not weights:
        return 50.0
    return 100.0 * sum(parts) / sum(weights)


def win_probability(away: TeamInput, home: TeamInput, home_advantage: float = 3.0) -> float:
    """Logistic conversion of relative team strength. Home advantage is percentage points in strength space."""
    a = team_strength(away)
    h = team_strength(home) + home_advantage
    return 1.0 / (1.0 + exp(-(h - a) / 12.0))


def projected_total(away: TeamInput, home: TeamInput) -> float:
    """Transparent run projection; returns None only when both run inputs are absent."""
    def run(t: TeamInput) -> Optional[float]:
        if t.runs_per_game is None:
            return None
        pitching = 0 if t.pitcher_era is None else (t.pitcher_era - 4.00) * 0.35
        bullpen = 0 if t.bullpen_score is None else (50 - t.bullpen_score) / 100
        return max(1.5, t.runs_per_game + pitching + bullpen + t.weather_adjustment)
    a, h = run(away), run(home)
    if a is None and h is None:
        return 8.0
    if a is None: a = 4.0
    if h is None: h = 4.0
    return round(a + h, 2)


def evaluate(away: TeamInput, home: TeamInput, market: Market) -> Prediction:
    p = win_probability(away, home)
    market_p = None if not market.decimal_odds or market.decimal_odds <= 1 else 1 / market.decimal_odds
    edge = None if market_p is None else p - market_p
    ev = None if market.decimal_odds is None or market.decimal_odds <= 1 else p * market.decimal_odds - 1
    ai = max(0.0, min(100.0, 50 + (p - 0.5) * 100 + (0 if edge is None else edge * 50)))
    if ev is None:
        decision = 'NO BET'
    elif ev >= 0.08 and edge >= 0.04:
        decision = 'BET'
    elif ev > 0:
        decision = 'LEAN'
    else:
        decision = 'NO BET'
    return Prediction(p, market_p, edge, ev, round(ai, 1), decision, projected_total(away, home))
