import os


class ProviderConfig:
    def __init__(self):
        self.mlb_base_url = os.getenv('MLB_BASE_URL', 'https://statsapi.mlb.com/api/v1')
        self.odds_base_url = os.getenv('ODDS_BASE_URL', 'https://api.the-odds-api.com/v4')
        self.weather_base_url = os.getenv('WEATHER_BASE_URL')
        self.mlb_api_key = os.getenv('MLB_API_KEY')
        self.odds_api_key = os.getenv('ODDS_API_KEY')
        self.weather_api_key = os.getenv('WEATHER_API_KEY')

    def validate(self):
        missing = []
        for name in ('odds_api_key',):
            if not getattr(self, name):
                missing.append(name)
        return {
            'ready': not missing,
            'missing': missing,
            'weather_ready': bool(self.weather_base_url),
        }
