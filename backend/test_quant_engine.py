from quant_engine import TeamInput, Market, evaluate


def test_no_odds_is_no_bet():
    a = TeamInput(pitcher_era=3.5, pitcher_whip=1.15, last5_era=3.2, ops=.76, runs_per_game=4.8, bullpen_score=75, lineup_strength=75)
    h = TeamInput(pitcher_era=4.4, pitcher_whip=1.35, last5_era=4.8, ops=.70, runs_per_game=4.0, bullpen_score=55, lineup_strength=60)
    p = evaluate(a, h, Market())
    assert p.decision == 'NO BET'
    assert p.ev is None


def test_positive_price_can_create_value():
    a = TeamInput(pitcher_era=3.0, pitcher_whip=1.05, last5_era=2.8, ops=.80, runs_per_game=5.2, bullpen_score=85, lineup_strength=85)
    h = TeamInput(pitcher_era=4.8, pitcher_whip=1.40, last5_era=5.0, ops=.68, runs_per_game=3.8, bullpen_score=50, lineup_strength=55)
    p = evaluate(a, h, Market(decimal_odds=2.20))
    assert p.ev is not None
    assert p.probability > .5


def test_projection_exists():
    t = TeamInput(runs_per_game=4.5, pitcher_era=4.0, bullpen_score=70)
    p = evaluate(t, t, Market())
    assert p.projected_total > 0
