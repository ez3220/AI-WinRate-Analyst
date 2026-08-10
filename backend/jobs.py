"""V3.8 scheduled job orchestration.
Jobs are provider-agnostic and safe to run from cron/GitHub Actions/cloud schedulers.
"""
from datetime import datetime, timezone
from sync import sync_provider


def run_sync(fetch_games, fetch_odds):
    started = datetime.now(timezone.utc)
    result = sync_provider(fetch_games, fetch_odds)
    result['started_at'] = started.isoformat()
    result['finished_at'] = datetime.now(timezone.utc).isoformat()
    return result
