"""V4.1 bet ledger and CLV tracking."""
from dataclasses import dataclass
from typing import Optional, Iterable

@dataclass
class BetRecord:
    bet_id: str
    placed_at: str
    game_id: str
    market: str
    outcome: str
    entry_odds: float
    stake_units: float
    model_probability: float
    closing_odds: Optional[float] = None
    profit_units: Optional[float] = None
    settled: bool = False


def clv(entry_odds: float, closing_odds: Optional[float]) -> Optional[float]:
    if closing_odds is None or entry_odds <= 1 or closing_odds <= 1:
        return None
    return (1 / closing_odds - 1 / entry_odds) * 100


def settle(record: BetRecord, won: bool) -> BetRecord:
    if record.settled:
        raise ValueError('bet is already settled')
    record.profit_units = record.stake_units * (record.entry_odds - 1) if won else -record.stake_units
    record.settled = True
    return record


def ledger_summary(records: Iterable[BetRecord]) -> dict:
    rows = list(records)
    settled = [r for r in rows if r.settled and r.profit_units is not None]
    profit = sum(r.profit_units for r in settled)
    stake = sum(r.stake_units for r in settled)
    wins = sum(1 for r in settled if r.profit_units > 0)
    clvs = [clv(r.entry_odds, r.closing_odds) for r in settled]
    clvs = [x for x in clvs if x is not None]
    return {
        'bets': len(settled),
        'wins': wins,
        'losses': len(settled) - wins,
        'hit_rate': wins / len(settled) if settled else 0.0,
        'profit_units': profit,
        'roi': profit / stake if stake else 0.0,
        'average_clv_percent': sum(clvs) / len(clvs) if clvs else None,
    }
