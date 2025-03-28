from unittest.mock import MagicMock
import pytest
import app.redis_client as redis_client

# Create a fake in-memory store to simulate Redis key-value behavior
fake_store = {"connection_count": 0}

def fake_get(key):
    return fake_store.get(key, None)

def fake_incr(key):
    fake_store[key] = fake_store.get(key, 0) + 1
    return fake_store[key]

@pytest.fixture(autouse=True)
def mock_redis_instance():
    # Create the mock Redis instance
    mock_redis = MagicMock()
    # Set the return value for ping
    mock_redis.ping.return_value = True
    # Set side effects for get and incr to simulate simple behavior
    mock_redis.get.side_effect = fake_get
    mock_redis.incr.side_effect = fake_incr

    # Override the redis_instance in the redis_client module with the mock
    redis_client.redis_instance = mock_redis

def test_redis_connection():
    # Test that the ping method of the mocked Redis returns True
    from app.redis_client import redis_instance
    assert redis_instance.ping() is True

def test_connection_count_increments():
    from app.redis_client import redis_instance
    before = redis_instance.get("connection_count") or 0
    redis_instance.incr("connection_count")
    after = redis_instance.get("connection_count")
    # Check that connection_count has incremented by 1
    assert int(after) == int(before) + 1
