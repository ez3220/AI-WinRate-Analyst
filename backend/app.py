from datetime import date, datetime
from typing import Optional
from zoneinfo import ZoneInfo

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

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
async def games(league: str = 'baseball_mlb'):
    if league != 'baseball_mlb':
        return {'games': [], 'status': 'unsupported_league'}
    taipei_today = datetime.now(ZoneInfo('Asia/Taipei')).date().isoformat()
    url = 'https://statsapi.mlb.com/api/v1/schedule'
    params = {
        'sportId': 1,
        'date': taipei_today,
        'hydrate': 'team,probablePitcher,venue',
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f'MLB provider unavailable: {exc}') from exc

    normalized = []
    for game in [g for d in payload.get('dates', []) for g in d.get('games', [])]:
        away = game.get('teams', {}).get('away', {})
        home = game.get('teams', {}).get('home', {})
        normalized.append({
            'gamePk': game.get('gamePk'),
            'gameDate': game.get('gameDate'),
            'status': game.get('status', {}).get('detailedState'),
            'away': away.get('team', {}).get('name'),
            'home': home.get('team', {}).get('name'),
            'away_pitcher': away.get('probablePitcher', {}).get('fullName'),
            'home_pitcher': home.get('probablePitcher', {}).get('fullName'),
            'venue': game.get('venue', {}).get('name'),
        })
    return {'games': normalized, 'source': 'MLB Stats API', 'date': taipei_today}


@app.get('/predictions')
def predictions():
    # No fabricated recommendations. The live-sync/quant pipeline owns this endpoint.
    return {'predictions': [], 'status': 'awaiting_live_sync'}


@app.get('/top3')
def top3():
    # No fabricated Top 3. Return empty until live-sync data is persisted and scored.
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
