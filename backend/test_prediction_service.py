from datetime import datetime, timezone

from prediction_service import _latest_h2h_odds, _latest_market_odds, _side_for_outcome, _poisson_cdf


def test_side_matching():
    game = {'away_team_name': 'New York Yankees', 'home_team_name': 'Boston Red Sox'}
    assert _side_for_outcome('New York Yankees', game) == 'away'
    assert _side_for_outcome('Boston Red Sox', game) == 'home'
    assert _side_for_outcome('Unknown Team', game) is None


def test_latest_h2h_odds_keeps_best_price_per_outcome():
    t1 = datetime(2026, 8, 11, 10, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 8, 11, 10, 5, tzinfo=timezone.utc)
    rows = [
        {'market': 'h2h', 'bookmaker': 'A', 'outcome': 'Home', 'snapshot_at': t1, 'decimal_odds': 1.90},
        {'market': 'h2h', 'bookmaker': 'A', 'outcome': 'Home', 'snapshot_at': t2, 'decimal_odds': 1.85},
        {'market': 'h2h', 'bookmaker': 'B', 'outcome': 'Home', 'snapshot_at': t2, 'decimal_odds': 1.95},
        {'market': 'totals', 'bookmaker': 'A', 'outcome': 'Over', 'snapshot_at': t2, 'decimal_odds': 2.00},
    ]
    result = _latest_h2h_odds(rows)
    assert len(result) == 1
    assert result[0]['outcome'] == 'Home'
    assert result[0]['decimal_odds'] == 1.95


def test_latest_totals_keeps_point_and_best_price():
    t = datetime(2026, 8, 11, 10, 5, tzinfo=timezone.utc)
    rows = [
        {'market': 'totals', 'bookmaker': 'A', 'outcome': 'Over', 'point': 8.5, 'snapshot_at': t, 'decimal_odds': 1.90},
        {'market': 'totals', 'bookmaker': 'B', 'outcome': 'Over', 'point': 8.5, 'snapshot_at': t, 'decimal_odds': 1.95},
        {'market': 'totals', 'bookmaker': 'A', 'outcome': 'Under', 'point': 8.5, 'snapshot_at': t, 'decimal_odds': 1.90},
    ]
    result = _latest_market_odds(rows, 'totals')
    assert len(result) == 2
    assert max(r['decimal_odds'] for r in result if r['outcome'] == 'Over') == 1.95


def test_poisson_cdf_bounds_and_zero_rate():
    assert _poisson_cdf(-1, 8.0) == 0.0
    assert _poisson_cdf(0, 0.0) == 1.0
    assert 0.0 < _poisson_cdf(8, 8.0) < 1.0
