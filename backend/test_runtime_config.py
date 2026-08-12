from runtime_config import cors_origins, validate_runtime


def test_runtime_requires_only_database_and_odds(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'postgresql://example')
    monkeypatch.setenv('ODDS_API_KEY', 'example')
    monkeypatch.delenv('WEATHER_API_KEY', raising=False)
    result = validate_runtime()
    assert result['ready'] is True
    assert result['missing'] == []


def test_cors_normalizes_trailing_slash(monkeypatch):
    monkeypatch.setenv('CORS_ORIGINS', 'https://ez3220.github.io/, https://example.com')
    assert cors_origins() == ['https://ez3220.github.io', 'https://example.com']
