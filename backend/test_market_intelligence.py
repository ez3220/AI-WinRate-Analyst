import pytest
from market_intelligence import implied_probability, clv_percent, movement_signal, edge_vs_market, ev


def test_implied_probability():
    assert implied_probability(2.0) == 0.5


def test_positive_clv_when_entry_price_is_better():
    assert clv_percent(2.10, 1.90) > 0


def test_movement_signal():
    assert movement_signal(2.10, 1.90) == 'SHORTENED'
    assert movement_signal(1.90, 2.10) == 'DRIFTED'


def test_ev():
    assert ev(0.55, 2.10) > 0


def test_invalid_odds():
    with pytest.raises(ValueError):
        implied_probability(1.0)
