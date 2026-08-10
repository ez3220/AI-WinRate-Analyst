from live_odds import OddsPoint, movement, latest_by_outcome


def test_movement_shortened():
    a = OddsPoint('2026-08-10T10:00:00Z', 'book', 'h2h', 'A', None, 2.10)
    b = OddsPoint('2026-08-10T10:15:00Z', 'book', 'h2h', 'A', None, 1.90)
    assert movement(a, b)['direction'] == 'SHORTENED'
    assert movement(a, b)['delta'] == -0.2


def test_latest_by_outcome():
    rows = [
        OddsPoint('2026-08-10T10:00:00Z', 'book', 'h2h', 'A', None, 2.10),
        OddsPoint('2026-08-10T10:15:00Z', 'book', 'h2h', 'A', None, 1.90),
    ]
    latest = latest_by_outcome(rows)
    assert len(latest) == 1
    assert latest[0].decimal_odds == 1.90
