import os

class ProviderConfig:
    def __init__(self):
        self.mlb_base_url = os.getenv('MLB_BASE_URL')
        self.odds_base_url = os.getenv('ODDS_BASE_URL')
        self.weather_base_url = os.getenv('WEATHER_BASE_URL')
        self.mlb_api_key = os.getenv('MLB_API_KEY')
        self.odds_api_key = os.getenv('ODDS_API_KEY')
        self.weather_api_key = os.getenv('WEATHER_API_KEY')

    def validate(self):
        missing=[]
        for name in ('mlb_base_url','odds_base_url','mlb_api_key','odds_api_key'):
            if not getattr(self,name): missing.append(name)
        return {'ready': not missing, 'missing': missing}
