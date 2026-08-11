"""DB-backed V4 prediction service.

Consumes only point-in-time snapshots already stored in PostgreSQL.
Totals use an explicit Poisson baseline; no provider calls are made here.
"""
from __future__ import annotations

from datetime import datetime
from math import exp, floor
from typing import Any

from db import insert_predictions, list_games, matchup_snapshot
from model_pipeline import score_matchup
from ranking import rank_ev, rank_upsets

MODEL_VERSION = 'V4.0.0'
TOTALS_MODEL_VERSION = 'V4.0.0-poisson-baseline'


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


def _latest_market_odds(rows: list[dict[str, Any]], market: str) -> list[dict[str, Any]]:
    latest: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in rows:
        if row.get('market') != market or not row.get('outcome'):
            continue
        key = (str(row.get('bookmaker')), str(row.get('outcome')), str(row.get('point')))
        old = latest.get(key)
        if old is None or row.get('snapshot_at') > old.get('snapshot_at'):
            latest[key] = row
    best: dict[tuple[str, str], dict[str, Any]] = {}
    for row in latest.values():
        key = (str(row.get('outcome')), str(row.get('point')))
        old = best.get(key)
        if old is None or float(row['decimal_odds']) > float(old['decimal_odds']):
            best[key] = row
    return list(best.values())


def _latest_h2h_odds(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return _latest_market_odds(rows, 'h2h')


def _poisson_cdf(k: int, lam: float) -> float:
    if k < 0:
        return 0.0
    if lam <= 0:
        return 1.0
    term = exp(-lam)
    total = term
    for i in range(1, k + 1):
        term *= lam / i
        total += term
    return min(1.0, max(0.0, total))


def _totals_candidate(game: dict[str, Any], snapshot: dict[str, Any], odds: dict[str, Any], projected_total: float | None) -> dict[str, Any]:
    if projected_total is None or odds.get('point') is None:
        return {'status': 'insufficient_data', 'decision': 'NO BET', 'game_id': game['id'],
                'away_team': game.get('away_team_name'), 'home_team': game.get('home_team_name'),
                'market': 'totals', 'outcome': odds.get('outcome'), 'point': odds.get('point'),
                'reason': 'projected_total_or_market_total_missing'}
    try:
        total = float(odds['point'])
        price = float(odds['decimal_odds'])
    except (TypeError, ValueError):
        return {'status': 'invalid_market', 'decision': 'NO BET', 'game_id': game['id'], 'market': 'totals'}
    if price <= 1:
        return {'status': 'invalid_market', 'decision': 'NO BET', 'game_id': game['id'], 'market': 'totals'}
    under_p = _poisson_cdf(floor(total), projected_total)
    over_p = 1.0 - under_p
    outcome = str(odds.get('outcome', '')).lower()
    probability = over_p if 'over' in outcome else under_p if 'under' in outcome else None
    if probability is None:
        return {'status': 'unmatched_market', 'decision': 'NO BET', 'game_id': game['id'], 'market': 'totals', 'outcome': odds.get('outcome')}
    market_probability = 1.0 / price
    edge = probability - market_probability
    ev = probability * price - 1.0
    decision = 'BET' if ev >= 0.08 and edge >= 0.04 else 'LEAN' if ev > 0 else 'NO BET'
    ai_score = max(0.0, min(100.0, 50.0 + edge * 100.0))
    return {'status': 'scored', 'decision': decision, 'game_id': game['id'],
            'away_team': game.get('away_team_name'), 'home_team': game.get('home_team_name'),
            'market': 'totals', 'outcome': odds.get('outcome'), 'point': total,
            'bookmaker': odds.get('bookmaker'), 'snapshot_at': odds.get('snapshot_at'),
            'decimal_odds': price, 'projected_total': round(projected_total, 2),
            'probability': round(probability, 6), 'market_probability': round(market_probability, 6),
            'edge': round(edge, 6), 'ev': round(ev, 6), 'ai_score': round(ai_score, 2),
            'model': TOTALS_MODEL_VERSION}


def _candidate(game: dict[str, Any], snapshot: dict[str, Any], odds: dict[str, Any]) -> dict[str, Any]:
    stats = snapshot['stats']
    away_stats = next((r for r in stats if r.get('side') == 'away'), {})
    home_stats = next((r for r in stats if r.get('side') == 'home'), {})
    scored = score_matchup(away_stats, home_stats)
    if scored.get('status') != 'scored':
        return {'status': 'insufficient_data', 'decision': 'NO BET', 'game_id': game['id'],
                'away_team': game.get('away_team_name'), 'home_team': game.get('home_team_name'),
                'market': 'h2h', 'outcome': odds.get('outcome'), 'reason': scored.get('reason'),
                'away_completeness': scored.get('away_completeness'), 'home_completeness': scored.get('home_completeness')}
    side = _side_for_outcome(str(odds['outcome']), game)
    if side is None:
        return {'status': 'unmatched_market', 'decision': 'NO BET', 'game_id': game['id'], 'market': 'h2h', 'outcome': odds.get('outcome')}
    probability = scored['probability'] if side == 'home' else 1.0 - scored['probability']
    decimal_odds = float(odds['decimal_odds'])
    market_probability = 1.0 / decimal_odds
    edge = probability - market_probability
    ev = probability * decimal_odds - 1.0
    ai_score = max(0.0, min(100.0, 50.0 + (probability - 0.5) * 100.0 + edge * 50.0))
    decision = 'BET' if ev >= 0.08 and edge >= 0.04 else 'LEAN' if ev > 0 else 'NO BET'
    return {'status': 'scored', 'decision': decision, 'game_id': game['id'],
            'away_team': game.get('away_team_name'), 'home_team': game.get('home_team_name'),
            'market': 'h2h', 'outcome': odds.get('outcome'), 'side': side,
            'bookmaker': odds.get('bookmaker'), 'snapshot_at': odds.get('snapshot_at'),
            'decimal_odds': decimal_odds, 'probability': round(probability, 6),
            'market_probability': round(market_probability, 6), 'edge': round(edge, 6),
            'ev': round(ev, 6), 'ai_score': round(ai_score, 2),
            'away_completeness': scored['away_completeness'], 'home_completeness': scored['home_completeness'],
            'model': MODEL_VERSION}


def _input_snapshot_at(snapshot: dict[str, Any], odds: dict[str, Any]) -> Any:
    values = [odds.get('snapshot_at')]
    values.extend(row.get('snapshot_at') for row in snapshot.get('stats', []))
    values.extend(row.get('snapshot_at') for row in snapshot.get('weather', []))
    values = [value for value in values if value is not None]
    return max(values) if values else datetime.utcnow()


def _ledger_row(candidate: dict[str, Any], snapshot: dict[str, Any], odds: dict[str, Any]) -> dict[str, Any] | None:
    if candidate.get('status') != 'scored' or not candidate.get('outcome'):
        return None
    probability = float(candidate['probability'])
    price = candidate.get('decimal_odds')
    return {'game_id': str(candidate['game_id']), 'snapshot_at': _input_snapshot_at(snapshot, odds),
            'model_version': str(candidate.get('model') or MODEL_VERSION),
            'market': str(candidate['market']), 'outcome': str(candidate['outcome']),
            'point': candidate.get('point'), 'probability': probability,
            'decimal_odds': float(price) if price is not None else None,
            'implied_probability': candidate.get('market_probability'), 'edge': candidate.get('edge'),
            'ev': candidate.get('ev'), 'recommendation': str(candidate.get('decision') or 'NO BET'),
            'source': 'v4_quant'}


def build_predictions(game_date: str, limit: int = 100) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    ledger_rows: list[dict[str, Any]] = []
    for game in list_games(game_date, limit):
        snapshot = matchup_snapshot(str(game['id']))
        if not snapshot:
            continue
        stats = snapshot['stats']
        away_stats = next((r for r in stats if r.get('side') == 'away'), {})
        home_stats = next((r for r in stats if r.get('side') == 'home'), {})
        scored = score_matchup(away_stats, home_stats)
        for odds in _latest_h2h_odds(snapshot['odds']):
            candidate = _candidate(game, snapshot, odds)
            rows.append(candidate)
            ledger = _ledger_row(candidate, snapshot, odds)
            if ledger:
                ledger_rows.append(ledger)
        for odds in _latest_market_odds(snapshot['odds'], 'totals'):
            candidate = _totals_candidate(game, snapshot, odds, scored.get('projected_total'))
            rows.append(candidate)
            ledger = _ledger_row(candidate, snapshot, odds)
            if ledger:
                ledger_rows.append(ledger)
    if ledger_rows:
        insert_predictions(ledger_rows)
    return rows


def prediction_report(game_date: str, limit: int = 100) -> dict[str, Any]:
    rows = build_predictions(game_date, limit)
    scored = [r for r in rows if r.get('status') == 'scored']
    h2h = [r for r in scored if r.get('market') == 'h2h']
    return {'date': game_date, 'generated_at': datetime.utcnow().isoformat() + 'Z',
            'predictions': rows, 'top3': rank_ev(scored, 3), 'upset_radar': rank_upsets(h2h, 3),
            'count': len(rows), 'scored_count': len(scored), 'market_scope': ['h2h', 'totals'],
            'status': 'ready' if scored else 'awaiting_complete_snapshots'}
