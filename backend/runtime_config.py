import os

REQUIRED = ('DATABASE_URL', 'MLB_API_KEY', 'ODDS_API_KEY')
OPTIONAL = ('WEATHER_API_KEY',)

def validate_runtime() -> dict:
    missing = [k for k in REQUIRED if not os.getenv(k)]
    return {'ready': not missing, 'missing': missing}
