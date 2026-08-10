from datetime import date
from typing import Optional
from fastapi import FastAPI
from pydantic import BaseModel, Field
from quant_engine import TeamInput, Market, evaluate
from live_api import router as live_router

app = FastAPI(title='AI WinRate Analyst API', version='4.0.0')
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

@app.post('/evaluate')
def evaluate_game(req: EvaluateRequest):
    result = evaluate(TeamInput(**req.away.model_dump()), TeamInput(**req.home.model_dump()), Market(req.decimal_odds, req.total))
    return result.__dict__

@app.get('/version')
def version():
    return {'api': '4.0.0', 'model': 'V4', 'date': date.today().isoformat()}
