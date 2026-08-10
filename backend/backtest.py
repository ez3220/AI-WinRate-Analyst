"""Walk-forward backtest utilities for settled prediction records."""
from dataclasses import dataclass
from typing import Iterable, List

@dataclass
class Bet:
    date: str
    ev: float
    profit_units: float
    decision: str = 'BET'

@dataclass
class BacktestReport:
    bets: int
    wins: int
    losses: int
    hit_rate: float
    profit_units: float
    roi: float
    max_drawdown: float


def backtest(records: Iterable[Bet], min_ev: float = 0.0) -> BacktestReport:
    selected: List[Bet] = [r for r in records if r.decision == 'BET' and r.ev >= min_ev]
    if not selected:
        return BacktestReport(0, 0, 0, 0.0, 0.0, 0.0, 0.0)
    wins = sum(1 for r in selected if r.profit_units > 0)
    profit = sum(r.profit_units for r in selected)
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for r in sorted(selected, key=lambda x: x.date):
        equity += r.profit_units
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    return BacktestReport(
        bets=len(selected),
        wins=wins,
        losses=len(selected) - wins,
        hit_rate=wins / len(selected),
        profit_units=profit,
        roi=profit / len(selected),
        max_drawdown=max_dd,
    )
