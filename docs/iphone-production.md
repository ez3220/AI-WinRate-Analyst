# iPhone production setup

The frontend is Flutter Web and the backend is FastAPI + PostgreSQL. GitHub Pages serves the Flutter build; Render hosts the backend and database.

## One-time setup from iPhone

1. Open Render and connect the GitHub repository `ez3220/AI-WinRate-Analyst`.
2. Create a **Blueprint** from the repository. Render reads the root `render.yaml` and creates the web service and PostgreSQL database.
3. In the backend service environment, set `ODDS_API_KEY` to a valid The Odds API key. Keep all provider keys server-side.
4. Wait for the backend to deploy and confirm `/health` returns HTTP 200.
5. In GitHub repository Settings → Secrets and variables → Actions, add:
   - `DATABASE_URL`: Render Postgres connection string
   - `ODDS_API_KEY`: The Odds API key
   - optional `MLB_API_KEY`, `WEATHER_API_KEY`, `MLB_BASE_URL`, `ODDS_BASE_URL`, `WEATHER_BASE_URL`
6. Run the `V4 live sync` workflow once with **Run workflow** to populate the first snapshots.
7. GitHub Pages then builds the Flutter app against the default backend URL `https://ai-winrate-backend.onrender.com`. If Render assigns a different URL, set the GitHub Actions secret `API_BASE_URL` to that URL.
8. Open the GitHub Pages URL on iPhone Safari, then **Share → Add to Home Screen**.

## Data rules

- No provider key is embedded in Flutter or GitHub Pages.
- Missing baseball inputs produce `NO BET`, not fabricated numbers.
- Every odds/weather/stats snapshot stores a timestamp and source.
- Backtests require `prediction.snapshot_at < games.start_time`.

## Free-tier warning

Render free web services sleep after 15 minutes of inactivity, and free Postgres expires after 30 days. Use the free tier for testing; upgrade the database/service for a durable production deployment.
