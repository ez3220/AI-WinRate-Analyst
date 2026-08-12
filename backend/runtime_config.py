import os

# Database and odds are required for a production recommendation pipeline.
# Weather uses Open-Meteo by default and therefore does not require a key.
REQUIRED = ('DATABASE_URL', 'ODDS_API_KEY')
OPTIONAL = ('MLB_API_KEY', 'WEATHER_API_KEY', 'MLB_BASE_URL', 'ODDS_BASE_URL', 'WEATHER_BASE_URL', 'CORS_ORIGINS')


def validate_runtime() -> dict:
    missing = [key for key in REQUIRED if not os.getenv(key)]
    return {
        'ready': not missing,
        'missing': missing,
        'secrets_server_side': True,
        'weather_provider': os.getenv('WEATHER_BASE_URL', 'https://api.open-meteo.com/v1/forecast'),
    }


def cors_origins() -> list[str]:
    raw = os.getenv('CORS_ORIGINS', 'https://ez3220.github.io')
    return [item.strip().rstrip('/') for item in raw.split(',') if item.strip()]
