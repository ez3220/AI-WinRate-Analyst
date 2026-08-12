from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException

from backtest_service import run_backtest
from db import list_calibration_runs

router = APIRouter(prefix='/backtest', tags=['backtest'])


def _parse(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f'invalid ISO-8601 datetime: {value}') from exc


@router.get('/runs')
def calibration_runs(model_version: Optional[str] = None, limit: int = 50):
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=400, detail='limit must be between 1 and 200')
    return {'runs': list_calibration_runs(model_version=model_version, limit=limit)}


@router.post('/run')
def execute_backtest(model_version: Optional[str] = None,
                    cutoff_start: Optional[str] = None,
                    cutoff_end: Optional[str] = None,
                    persist: bool = True):
    start = _parse(cutoff_start)
    end = _parse(cutoff_end)
    if start and end and start >= end:
        raise HTTPException(status_code=400, detail='cutoff_start must be before cutoff_end')
    try:
        result = run_backtest(model_version=model_version, cutoff_start=start, cutoff_end=end, persist=persist)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {'status': 'ok', 'run': result}
