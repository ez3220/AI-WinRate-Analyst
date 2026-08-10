from ingestion import normalize_odds, normalize_game, dedupe_odds


def test_normalize_game():
    row = normalize_game({'id': 123, 'sport': 'MLB', 'status': 'scheduled'})
    assert row['id'] == '123'
    assert row['sport'] == 'mlb'


def test_normalize_odds_calculates_implied_probability():
    row = normalize_odds({'game_id': 1, 'bookmaker': 'x', 'market': 'h2h', 'outcome': 'A', 'decimal_odds': 2.0})
    assert row['implied_probability'] == 0.5


def test_dedupe_odds():
    raw = {'game_id': '1', 'bookmaker': 'x', 'market': 'h2h', 'outcome': 'A', 'point': None, 'decimal_odds': 2.0}
    assert len(dedupe_odds([raw, raw])) == 1
