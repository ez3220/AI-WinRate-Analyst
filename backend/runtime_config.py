import os

# Never expose these values to Flutter or browser JavaScript.
REQUIRED = ('DATABASE_URL', 'ODDS_API_KEY', 'WEATHER_API_KEY')
OPTIONAL = ('MLB_API_KEY', 'CORS_ORIGINS')


def validate_runtime() -> dict:
    missing = [key for key in REQUIRED if not os.getenv(key)]
    return {
        'ready': not missing,
        'missing': missing,
        'secrets_server_side': True,
    }


def cors_origins() -> list[str]:
    raw = os.getenv('CORS_ORIGINS', 'https://ez3220.github.io')
    return [item.strip() for item in raw.split(',') if item.strip()]
