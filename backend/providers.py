"""V3.7 provider adapter interfaces.
Concrete credentials stay in environment variables; adapters can be wired to approved data providers.
"""
import os
from typing import Any, Dict, Iterable, Protocol
import httpx

class Provider(Protocol):
    def games(self, game_date: str) -> Iterable[Dict[str, Any]]: ...
    def odds(self, game_date: str) -> Iterable[Dict[str, Any]]: ...

class HttpProvider:
    def __init__(self, base_url: str, api_key_env: str):
        self.base_url = base_url.rstrip('/')
        self.api_key_env = api_key_env

    def _headers(self):
        key = os.getenv(self.api_key_env)
        if not key:
            raise RuntimeError(f'{self.api_key_env} is not configured')
        return {'Authorization': f'Bearer {key}'}

    def get(self, path: str, params: Dict[str, Any] | None = None):
        with httpx.Client(timeout=20) as client:
            response = client.get(f'{self.base_url}/{path.lstrip("/")}', params=params, headers=self._headers())
            response.raise_for_status()
            return response.json()
