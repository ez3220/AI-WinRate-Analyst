from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


def test_health():
    r = client.get('/health')
    assert r.status_code == 200
    assert r.json()['status'] == 'ok'


def test_evaluate_without_odds_is_no_bet():
    payload = {
        'away': {'pitcher_era': 3.4, 'pitcher_whip': 1.1, 'ops': .78, 'runs_per_game': 4.8, 'bullpen_score': 80, 'lineup_strength': 80},
        'home': {'pitcher_era': 4.7, 'pitcher_whip': 1.4, 'ops': .69, 'runs_per_game': 3.9, 'bullpen_score': 50, 'lineup_strength': 55}
    }
    r = client.post('/evaluate', json=payload)
    assert r.status_code == 200
    assert r.json()['decision'] == 'NO BET'
