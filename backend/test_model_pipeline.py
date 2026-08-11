from model_pipeline import score_matchup


def test_incomplete_matchup_fails_closed():
    result = score_matchup({'pitcher_era': 3.2}, {'pitcher_era': 4.1})
    assert result['status'] == 'insufficient_data'
    assert result['decision'] == 'NO BET'


def test_complete_matchup_can_score_without_odds():
    team = {
        'pitcher_era': 3.2,
        'pitcher_whip': 1.08,
        'last5_era': 3.4,
        'last5_whip': 1.10,
        'ops': .760,
        'runs_per_game': 4.7,
        'bullpen_score': 75,
        'lineup_strength': 78,
    }
    result = score_matchup(team, team)
    assert result['status'] == 'scored'
    assert result['decision'] == 'NO BET'
    assert 0 <= result['probability'] <= 1


def test_positive_ev_requires_market_data():
    team = {
        'pitcher_era': 3.2,
        'pitcher_whip': 1.08,
        'last5_era': 3.4,
        'last5_whip': 1.10,
        'ops': .760,
        'runs_per_game': 4.7,
        'bullpen_score': 75,
        'lineup_strength': 78,
    }
    result = score_matchup(team, team, decimal_odds=2.5)
    assert result['market_probability'] == .4
    assert result['ev'] is not None
