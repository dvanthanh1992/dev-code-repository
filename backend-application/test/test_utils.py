import os
from app.utils import get_env_variable

def test_get_env_variable_existing(monkeypatch):
    monkeypatch.setenv("TEST_ENV", "hello")
    assert get_env_variable("TEST_ENV") == "hello"

def test_get_env_variable_default():
    assert get_env_variable("NON_EXISTING_ENV", "default") == "default"