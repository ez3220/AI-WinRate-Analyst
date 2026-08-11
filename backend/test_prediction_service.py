from datetime import datetime, timezone

from prediction_service import _latest_h2h_odds, _side_for_outcome


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
