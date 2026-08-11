"""DB-backed V4 prediction service.

No provider calls are made here. It consumes only point-in-time snapshots already
stored in PostgreSQL, then feeds the deterministic quant engine and EV ranking.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from db import list_games, matchup_snapshot
from model_pipeline import score_matchup
from ranking import rank_ev, rank_upsets


def _norm_name(value: Any) -> str:
    if value is None:
        return ''
    return ''.join(ch for ch in str(value).lower() if ch.isalnum())


def _side_for_outcome(outcome: str, game: dict[str, Any]) -> str | None:
    key = _norm_name(outcome)
    away = _norm_name(game.get('away_team_name'))
    home = _norm_name(game.get('home_team_name'))
    if key and (key == away or key in away or away in key):
        return 'away'
    if key and (key == home or key in home or home in key):
        return 'home'
    return None


def _latest_h2h_odds(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        if row.get('market') != 'h2h' or not row.get('outcome'):
            continue
        key = (str(row.get('bookmaker')), str(row.get('outcome')))
        old = latest.get(key)
        if old is None or row.get('snapshot_at') > old.get('snapshot_at'):
            latest[key] = row
    # Keep the best currently available price for each outcome.
    best: dict[str, dict[str, Any]] = {}
    for row in latest.values():
        outcome = str(row['outcome'])
        old = best.get(outcome)
        if old is None or float(row['decimal_odds']) > float(old['decimal_odds']):
            best[outcome] = row
    return list(best.values())


def _candidate(game: dict[str, Any], snapshot: dict[str, Any], odds: dict[str, Any]) -> dict[str, Any]:
    stats = snapshot['stats']
    away_stats = next((r for r in stats if r.get('side') == 'away'), {})
    home_stats = next((r for r in stats if r.get('side') == 'home'), {})
    scored = score_matchup(away_stats, home_stats)
    if scored.get('status') != 'scored':
        return {
            'status': 'insufficient_data',
            'decision': 'NO BET',
            'game_id': game['id'],
            'away_team': game.get('away_team_name'),
            'home_team': game.get('home_team_name'),
            'market': 'h2h',
            'outcome': odds.get('outcome'),
            'reason': scored.get('reason'),
            'away_completeness': scored.get('away_completeness'),
            'home_completeness': scored.get('home_completeness'),
        }

    side = _side_for_outcome(str(odds['outcome']), game)
    if side is None:
        return {
            'status': 'unmatched_market',
            'decision': 'NO BET',
            'game_id': game['id'],
            'market': 'h2h',
            'outcome': odds.get('outcome'),
        }

    probability = scored['probability'] if side == 'home' else 1.0 - scored['probability']
    decimal_odds = float(odds['decimal_odds'])
    market_probability = 1.0 / decimal_odds
    edge = probability - market_probability
    ev = probability * decimal_odds - 1.0
    ai_score = max(0.0, min(100.0, 50.0 + (probability - 0.5) * 100.0 + edge * 50.0))
    if ev >= 0.08 and edge >= 0.04:
        decision = 'BET'
    elif ev > 0:
        decision = 'LEAN'
    else:
        decision = 'NO BET'

    return {
        'status': 'scored',
        'decision': decision,
        'game_id': game['id'],
        'away_team': game.get('away_team_name'),
        'home_team': game.get('home_team_name'),
        'market': 'h2h',
        'outcome': odds.get('outcome'),
        'side': side,
        'bookmaker': odds.get('bookmaker'),
        'snapshot_at': odds.get('snapshot_at'),
        'decimal_odds': decimal_odds,
        'probability': round(probability, 6),
        'market_probability': round(market_probability, 6),
        'edge': round(edge, 6),
        'ev': round(ev, 6),
        'ai_score': round(ai_score, 2),
        'away_completeness': scored['away_completeness'],
        'home_completeness': scored['home_completeness'],
    }


def build_predictions(game_date: str, limit: int = 100) -> list[dict[str, Any]]:
    rows = []
    for game in list_games(game_date, limit):
        snapshot = matchup_snapshot(str(game['id']))
        if not snapshot:
            continue
        for odds in _latest_h2h_odds(snapshot['odds']):
            rows.append(_candidate(game, snapshot, odds))
    return rows


def prediction_report(game_date: str, limit: int = 100) -> dict[str, Any]:
    rows = build_predictions(game_date, limit)
    scored = [r for r in rows if r.get('status') == 'scored']
    return {
        'date': game_date,
        'generated_at': datetime.utcnow().isoformat() + 'Z',
        'predictions': rows,
        'top3': rank_ev(scored, 3),
        'upset_radar': rank_upsets(scored, 3),
        'count': len(rows),
        'scored_count': len(scored),
        'market_scope': ['h2h'],
        'status': 'ready' if scored else 'awaiting_complete_snapshots',
    }
