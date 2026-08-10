import pytest
from providers import HttpProvider


def test_provider_requires_secret(monkeypatch):
    monkeypatch.delenv('TEST_PROVIDER_KEY', raising=False)
    provider = HttpProvider('https://example.invalid', 'TEST_PROVIDER_KEY')
    with pytest.raises(RuntimeError):
        provider._headers()
