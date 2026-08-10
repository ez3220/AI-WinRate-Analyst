# V3.9 Live Market Layer

V3.9 adds a deterministic odds movement layer on top of timestamped snapshots.

It identifies the latest price per bookmaker/market/outcome/point and classifies movement as:
- `SHORTENED`: decimal price decreased
- `DRIFTED`: decimal price increased
- `UNCHANGED`: no price change

This is a market-observation layer, not a claim that every price move is informed money. Movement should be combined with model probability, liquidity/context and timestamped evidence before generating a betting signal.

No provider credentials are stored in source control.
