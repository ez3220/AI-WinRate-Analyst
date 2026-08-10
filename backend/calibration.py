"""Probability calibration metrics for model validation."""
from typing import Iterable, Tuple


def brier_score(rows: Iterable[Tuple[float, int]]) -> float:
    values = list(rows)
    if not values:
        return 0.0
    return sum((p - y) ** 2 for p, y in values) / len(values)


def calibration_bins(rows: Iterable[Tuple[float, int]], bins: int = 10):
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
