from result_ingestion import _is_final, _result_row
from datetime import datetime, timezone


def test_final_status_is_accepted():
    assert _is_final('Final')
    assert _is_final('Game Over')
    assert _is_final('Completed Early')


def test_non_final_status_is_rejected():
    assert not _is_final('Scheduled')
    assert not _is_final('In Progress')


def test_result_requires_both_scores():
    now = datetime(2026, 8, 11, tzinfo=timezone.utc)
    game = {'id': '1', 'status': 'Final', 'away_score': 4, 'home_score': 2}
    result = _result_row(game, now)
    assert result['game_id'] == '1'
    assert result['away_runs'] == 4
    assert result['home_runs'] == 2
    assert result['status'] == 'final'

    game['home_score'] = None
    assert _result_row(game, now) is None
