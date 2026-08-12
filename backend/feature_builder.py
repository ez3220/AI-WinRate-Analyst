"""Point-in-time feature construction for the V4 quant pipeline.

This module never invents missing baseball inputs. A feature is either backed by
an input snapshot or remains None; callers can then enforce minimum completeness.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class TeamFeatures:
    pitcher_era: Optional[float] = None
    pitcher_whip: Optional[float] = None
    last5_era: Optional[float] = None
    last5_whip: Optional[float] = None
    ops: Optional[float] = None
    runs_per_game: Optional[float] = None
    bullpen_score: Optional[float] = None
    lineup_strength: Optional[float] = None
    weather_adjustment: float = 0.0

    @property
    def completeness(self) -> float:
        values = (
            self.pitcher_era, self.pitcher_whip, self.last5_era,
            self.last5_whip, self.ops, self.runs_per_game,
            self.bullpen_score, self.lineup_strength,
        )
        return sum(v is not None for v in values) / len(values)


def _number(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def build_team_features(row: dict) -> TeamFeatures:
    return TeamFeatures(
        pitcher_era=_number(row.get('pitcher_era')),
        pitcher_whip=_number(row.get('pitcher_whip')),
        last5_era=_number(row.get('last5_era')),
        last5_whip=_number(row.get('last5_whip')),
        ops=_number(row.get('ops')),
        runs_per_game=_number(row.get('runs_per_game')),
        bullpen_score=_number(row.get('bullpen_score')),
        lineup_strength=_number(row.get('lineup_strength')),
        weather_adjustment=_number(row.get('weather_adjustment')) or 0.0,
    )


def build_matchup_features(away: dict, home: dict) -> dict:
    away_f = build_team_features(away)
    home_f = build_team_features(home)
    return {
        'away': away_f,
        'home': home_f,
        'away_completeness': away_f.completeness,
        'home_completeness': home_f.completeness,
        'complete': away_f.completeness >= 0.5 and home_f.completeness >= 0.5,
    }
