from jobs import run_sync


def test_run_sync_records_timestamps(monkeypatch):
    monkeypatch.setattr('jobs.sync_provider', lambda games, odds: {'games_written': 1, 'odds_written': 2})
    result = run_sync(lambda: [], lambda: [])
    assert result['games_written'] == 1
    assert result['odds_written'] == 2
    assert result['started_at']
    assert result['finished_at']
