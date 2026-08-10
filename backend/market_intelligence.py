"""V4.0 market intelligence: CLV and price-movement signals."""
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class Price:
    decimal_odds: float
    captured_at: str


def implied_probability(decimal_odds: float) -> float:
    if decimal_odds <= 1:
        raise ValueError('decimal_odds must be > 1')
    return 1.0 / decimal_odds


def clv_percent(entry_odds: float, close_odds: float) -> float:
    """Positive CLV means the bettor obtained a better price than the close."""
    entry_p = implied_probability(entry_odds)
    close_p = implied_probability(close_odds)
    return (close_p - entry_p) * 100.0


def movement_signal(previous: float, current: float) -> str:
    if current < previous:
        return 'SHORTENED'
    if current > previous:
        return 'DRIFTED'
    return 'UNCHANGED'


def edge_vs_market(model_probability: float, decimal_odds: float) -> float:
    return model_probability - implied_probability(decimal_odds)


def ev(model_probability: float, decimal_odds: float) -> float:
    return model_probability * decimal_odds - 1.0


def market_score(model_probability: float, current_odds: float, open_odds: Optional[float] = None) -> dict:
    result = {
        'model_probability': model_probability,
        'market_probability': implied_probability(current_odds),
        'edge': edge_vs_market(model_probability, current_odds),
        'ev': ev(model_probability, current_odds),
    }
    if open_odds and open_odds > 1:
        result['open_to_current_signal'] = movement_signal(open_odds, current_odds)
    return result
