CREATE TABLE IF NOT EXISTS sync_runs (
    sync_id BIGSERIAL PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    game_date DATE NOT NULL,
    source TEXT NOT NULL,
    status TEXT NOT NULL,
    games_fetched INTEGER NOT NULL DEFAULT 0,
    odds_fetched INTEGER NOT NULL DEFAULT 0,
    weather_fetched INTEGER NOT NULL DEFAULT 0,
    error TEXT
);
CREATE INDEX IF NOT EXISTS idx_sync_runs_date_time ON sync_runs(game_date, started_at DESC);

CREATE TABLE IF NOT EXISTS games (
    id TEXT PRIMARY KEY,
    sport TEXT NOT NULL,
    game_date DATE,
    start_time TIMESTAMPTZ,
    away_team_id TEXT,
    away_team_name TEXT,
    home_team_id TEXT,
    home_team_name TEXT,
    venue_id TEXT,
    venue_name TEXT,
    venue_lat NUMERIC,
    venue_lon NUMERIC,
    status TEXT NOT NULL DEFAULT 'scheduled',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_games_date_time ON games(game_date,start_time);

CREATE TABLE IF NOT EXISTS odds_snapshots (
    id BIGSERIAL PRIMARY KEY,
    game_id TEXT NOT NULL REFERENCES games(id),
    snapshot_at TIMESTAMPTZ NOT NULL,
    source TEXT NOT NULL DEFAULT 'odds_provider',
    bookmaker TEXT NOT NULL,
    market TEXT NOT NULL,
    outcome TEXT NOT NULL,
    point NUMERIC,
    decimal_odds NUMERIC NOT NULL,
    implied_probability NUMERIC,
    UNIQUE(game_id,snapshot_at,source,bookmaker,market,outcome,point)
);
CREATE INDEX IF NOT EXISTS idx_odds_game_time ON odds_snapshots(game_id,snapshot_at DESC);

CREATE TABLE IF NOT EXISTS weather_snapshots (
    id BIGSERIAL PRIMARY KEY,
    game_id TEXT NOT NULL REFERENCES games(id),
    snapshot_at TIMESTAMPTZ NOT NULL,
    forecast_at TIMESTAMPTZ NOT NULL,
    source TEXT NOT NULL,
    temperature_c NUMERIC,
    wind_mph NUMERIC,
    wind_direction_deg NUMERIC,
    precipitation_probability NUMERIC,
    condition TEXT,
    UNIQUE(game_id,snapshot_at,forecast_at,source)
);
CREATE INDEX IF NOT EXISTS idx_weather_game_time ON weather_snapshots(game_id,forecast_at DESC);

CREATE TABLE IF NOT EXISTS bets (
    bet_id TEXT PRIMARY KEY,
    placed_at TIMESTAMPTZ NOT NULL,
    game_id TEXT NOT NULL,
    market TEXT NOT NULL,
    outcome TEXT NOT NULL,
    entry_odds NUMERIC NOT NULL,
    stake_units NUMERIC NOT NULL,
    model_probability NUMERIC NOT NULL,
    closing_odds NUMERIC,
    profit_units NUMERIC,
    settled BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_bets_placed ON bets(placed_at DESC);
