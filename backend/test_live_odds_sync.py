from datetime import datetime, timezone

from live_odds_sync import _game_rows


def test_game_rows_match_odds_event_shape():
    rows = _game_rows([{
        'id': 'abc123',
        'sport_key': 'baseball_mlb',
        'commence_time': '2026-09-07T23:10:00Z',
        'away_team': 'Away Team',
        'home_team': 'Home Team',
    }])
    assert rows[0]['id'] == 'abc123'
    assert rows[0]['sport'] == 'baseball_mlb'
    assert rows[0]['away_team_name'] == 'Away Team'
    assert rows[0]['home_team_name'] == 'Home Team'
    assert rows[0]['start_time'] == datetime(2026, 9, 7, 23, 10, tzinfo=timezone.utc)
    assert rows[0]['status'] == 'scheduled'
