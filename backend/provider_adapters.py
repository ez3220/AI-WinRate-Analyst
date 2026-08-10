"""Provider adapters with explicit endpoint contracts; no fake live data."""
from typing import Any, Dict
from providers import HttpProvider

class MLBAdapter:
    def __init__(self, base_url: str, api_key_env: str = 'MLB_API_KEY'):
        self.provider = HttpProvider(base_url, api_key_env)
    def games(self, game_date: str):
        return self.provider.get('/games', {'date': game_date})

class OddsAdapter:
    def __init__(self, base_url: str, api_key_env: str = 'ODDS_API_KEY'):
        self.provider = HttpProvider(base_url, api_key_env)
    def odds(self, game_date: str):
        return self.provider.get('/odds', {'date': game_date})

class WeatherAdapter:
    def __init__(self, base_url: str, api_key_env: str = 'WEATHER_API_KEY'):
        self.provider = HttpProvider(base_url, api_key_env)
    def forecast(self, lat: float, lon: float):
        return self.provider.get('/forecast', {'lat': lat, 'lon': lon})
