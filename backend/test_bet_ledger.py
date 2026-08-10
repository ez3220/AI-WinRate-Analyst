import pytest
from bet_ledger import BetRecord, clv, settle, ledger_summary


def make_bet():
    return BetRecord('b1', '2026-08-10T10:00:00Z', 'g1', 'h2h', 'A', 2.10, 1.0, .55, 1.90)


def test_clv_positive():
    assert clv(2.10, 1.90) > 0


def test_settlement_win():
    bet = settle(make_bet(), True)
    assert bet.settled is True
    assert bet.profit_units == pytest.approx(1.10)


def test_summary():
    bet = settle(make_bet(), True)
    summary = ledger_summary([bet])
    assert summary['bets'] == 1
    assert summary['hit_rate'] == 1.0
    assert summary['roi'] == pytest.approx(1.10)


def test_cannot_settle_twice():
    bet = settle(make_bet(), False)
    with pytest.raises(ValueError):
        settle(bet, True)
