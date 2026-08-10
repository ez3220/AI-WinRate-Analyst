# V3.1 Quant Data Layer

This directory defines the production data model for historical games, pitcher/bullpen/lineup/weather snapshots, odds snapshots, predictions and settled results.

## Pipeline

`MLB / Odds / Weather / Injury feeds -> snapshots -> prediction engine -> BET/LEAN/NO BET -> settlement -> ROI/backtest`

## Important

The browser-only GitHub Pages build remains a front end. Historical persistence and secrets must be handled by a backend/database; API keys must not be committed to the repository.

## Model principles

- Prediction probability and betting value are separate metrics.
- EV is only calculated when a real market price exists.
- `NO BET` is a valid model output.
- Confidence stars describe model signal strength, not guaranteed win probability.
- Backtesting must use time-ordered, out-of-sample data to avoid look-ahead bias.
