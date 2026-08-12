"""Point-in-time probability calibration and backtest metrics.

Callers must supply predictions created from snapshots available before first
pitch. This module never fetches data and cannot introduce future information.
"""
from math import log
from typing import Iterable, Tuple, Optional


def _clip(p: float) -> float:
    return max(1e-6, min(1.0 - 1e-6, float(p)))


def brier_score(rows: Iterable[Tuple[float, int]]) -> Optional[float]:
    values = list(rows)
    if not values:
        return None
    return sum((_clip(p) - int(y)) ** 2 for p, y in values) / len(values)


def log_loss(rows: Iterable[Tuple[float, int]]) -> Optional[float]:
    values = list(rows)
    if not values:
        return None
    total = 0.0
    for p, y in values:
        p = _clip(p)
        y = int(y)
        total += -(y * log(p) + (1 - y) * log(1 - p))
    return total / len(values)


def calibration_bins(rows: Iterable[Tuple[float, int]], bins: int = 10):
    if bins <= 0:
        raise ValueError("bins must be positive")
    values = list(rows)
    result = []
    for i in range(bins):
        lo, hi = i / bins, (i + 1) / bins
        bucket = [(p, y) for p, y in values if lo <= p < hi or (i == bins - 1 and p == hi)]
        if bucket:
            result.append({
                'lower': lo,
                'upper': hi,
                'count': len(bucket),
                'predicted': sum(p for p, _ in bucket) / len(bucket),
                'actual': sum(y for _, y in bucket) / len(bucket),
            })
    return result


def roi_units(results: Iterable[Tuple[bool, float]], stake: float = 1.0) -> Optional[float]:
    """Profit / amount staked for settled decimal-odds bets."""
    if stake <= 0:
        raise ValueError("stake must be positive")
    values = list(results)
    if not values:
        return None
    profit = sum((odds - 1.0) * stake if won else -stake for won, odds in values)
    return profit / (len(values) * stake)
