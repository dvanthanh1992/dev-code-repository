import pytest
from unittest.mock import MagicMock
import app.redis_client as redis_client

# Automatically patch the redis_instance for routes
@pytest.fixture(autouse=True)
def mock_redis_instance_in_routes():
    # Create the mock Redis instance
    mock_redis = MagicMock()
    # Set the return value for info
    mock_redis.info.return_value = {"connected_clients": 3, "uptime_in_seconds": 1234}
    # Set a fixed return value for incr
    mock_redis.incr.return_value = 10

    # Override the redis_instance in the redis_client module with the mock
    redis_client.redis_instance = mock_redis

@pytest.fixture
def client():
    from app import create_app
    app = create_app()
    app.testing = True
    with app.test_client() as client:
        yield client
