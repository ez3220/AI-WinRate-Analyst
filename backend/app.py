from datetime import date, datetime
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from db import database_url, latest_odds, latest_weather, list_games
from quant_engine import TeamInput, Market, evaluate
from live_api import router as live_router
from runtime_config import cors_origins, validate_runtime

app = FastAPI(title='AI WinRate Analyst API', version='4.0.0')
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_credentials=False,
    allow_methods=['GET', 'POST'],
    allow_headers=['*'],
)
app.include_router(live_router)


class TeamPayload(BaseModel):
    pitcher_era: Optional[float] = None
    pitcher_whip: Optional[float] = None
    last5_era: Optional[float] = None
    last5_whip: Optional[float] = None
    ops: Optional[float] = None
    runs_per_game: Optional[float] = None
    bullpen_score: Optional[float] = Field(default=None, ge=0, le=100)
    lineup_strength: Optional[float] = Field(default=None, ge=0, le=100)
    weather_adjustment: float = 0.0


class EvaluateRequest(BaseModel):
    away: TeamPayload
    home: TeamPayload
    decimal_odds: Optional[float] = Field(default=None, gt=1)
    total: Optional[float] = None


@app.get('/health')
def health():
    return {'status': 'ok', 'version': '4.0.0'}


@app.get('/health/ready')
def readiness():
    result = validate_runtime()
    if not result['ready']:
        raise HTTPException(status_code=503, detail=result)
    return result


@app.get('/games')
def games(league: str = 'baseball_mlb'):
    if league != 'baseball_mlb':
        return {'games': [], 'status': 'unsupported_league'}
    taipei_today = datetime.now(ZoneInfo('Asia/Taipei')).date().isoformat()
    if not database_url():
        raise HTTPException(status_code=503, detail='Database is not configured')
    rows = list_games(taipei_today)
    return {'games': rows, 'source': 'v4_postgresql', 'date': taipei_today}


@app.get('/games/{game_id}/market')
def game_market(game_id: str):
    if not database_url():
        raise HTTPException(status_code=503, detail='Database is not configured')
    return {
        'game_id': game_id,
        'odds': latest_odds(game_id),
        'weather': latest_weather(game_id),
        'source': 'v4_postgresql',
    }


@app.get('/predictions')
def predictions():
    return {'predictions': [], 'status': 'awaiting_live_sync'}


@app.get('/top3')
def top3():
    return {'recommendations': [], 'status': 'awaiting_live_sync'}


@app.post('/evaluate')
def evaluate_game(req: EvaluateRequest):
    result = evaluate(
        TeamInput(**req.away.model_dump()),
        TeamInput(**req.home.model_dump()),
        Market(req.decimal_odds, req.total),
    )
    return result.__dict__


@app.get('/version')
def version():
    return {'api': '4.0.0', 'model': 'V4', 'date': date.today().isoformat()}
