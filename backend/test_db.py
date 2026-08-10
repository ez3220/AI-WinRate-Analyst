import pytest
from db import database_url


def test_database_url_requires_configuration(monkeypatch):
    monkeypatch.delenv('DATABASE_URL', raising=False)
    with pytest.raises(RuntimeError):
        database_url()
