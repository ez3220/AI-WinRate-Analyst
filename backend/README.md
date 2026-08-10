# V3.2 Backend Data Engine

Production boundary for AI-WinRate-Analyst.

## Responsibilities

- Keep provider API keys server-side.
- Ingest MLB schedule/team/player data.
- Persist timestamped odds snapshots.
- Persist weather/injury/bullpen snapshots.
- Run the prediction engine against a point-in-time dataset.
- Settle predictions after games finish.
- Calculate ROI, EV, hit rate, max drawdown and calibration.

## API contract

`GET /health`

`GET /games?date=YYYY-MM-DD&sport=mlb`

`GET /games/{game_id}`

`GET /predictions?date=YYYY-MM-DD&limit=3`

`GET /odds/{game_id}`

`GET /performance?from=YYYY-MM-DD&to=YYYY-MM-DD`

`POST /ingest/odds`

`POST /settle/{game_id}`

The web client should call the backend rather than expose provider credentials in JavaScript.

## Required environment variables

`MLB_API_KEY`

`ODDS_API_KEY`

`WEATHER_API_KEY`

`DATABASE_URL`

Never commit real values to GitHub.
