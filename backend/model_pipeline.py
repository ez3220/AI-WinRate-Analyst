"""V4 scoring pipeline: features -> deterministic quant -> EV guardrails.

The pipeline fails closed when the point-in-time feature set is incomplete.
"""
from dataclasses import asdict
from feature_builder import build_matchup_features
from quant_engine import Market, TeamInput, evaluate


def score_matchup(away: dict, home: dict, decimal_odds: float | None = None, total: float | None = None) -> dict:
    features = build_matchup_features(away, home)
    if not features['complete']:
        return {
            'status': 'insufficient_data',
            'decision': 'NO BET',
            'reason': 'point_in_time_feature_completeness_below_50_percent',
            'away_completeness': features['away_completeness'],
            'home_completeness': features['home_completeness'],
        }

    result = evaluate(
        TeamInput(**asdict(features['away'])),
        TeamInput(**asdict(features['home'])),
        Market(decimal_odds, total),
    )
    return {
        'status': 'scored',
        'decision': result.decision,
        'probability': result.probability,
        'market_probability': result.market_probability,
        'edge': result.edge,
        'ev': result.ev,
        'ai_score': result.ai_score,
        'projected_total': result.projected_total,
        'away_completeness': features['away_completeness'],
        'home_completeness': features['home_completeness'],
    }
