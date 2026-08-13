import pytest
from fastapi.testclient import TestClient
from src.main import app, limiter
from src.limiters.fixed_window import FixedWindowRateLimiter

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_limiter_store():
    """
    Fixture to clear the rate limiter's internal memory store before each test.
    This guarantees test isolation.
    """
    limiter.store.clear()


def test_api_test_under_limit():
    """
    Verify that requests within the rate limit (<= 10) return HTTP 200 and decrement remaining.
    """
    for i in range(1, 11):
        response = client.get("/api/test")
        assert response.status_code == 200
        assert response.headers["X-RateLimit-Limit"] == "10"
        assert int(response.headers["X-RateLimit-Remaining"]) == 10 - i
        assert "X-RateLimit-Reset" in response.headers


def test_api_test_over_limit():
    """
    Verify that the 11th request yields HTTP 429 and includes proper rate limit headers.
    """
    # Consume 10 requests
    for _ in range(10):
        client.get("/api/test")
        
    # The 11th request must fail with 429
    response = client.get("/api/test")
    assert response.status_code == 429
    assert response.json()["detail"] == "Rate limit exceeded. Try again later."
    assert response.headers["X-RateLimit-Limit"] == "10"
    assert response.headers["X-RateLimit-Remaining"] == "0"
    assert "X-RateLimit-Reset" in response.headers


def test_fixed_window_unit_logic():
    """
    Unit test for FixedWindowRateLimiter to verify time window boundary crossing
    using a mock clock.
    """
    current_time = 100.0
    def mock_clock():
        return current_time

    # Config: 2 requests per 10 seconds
    unit_limiter = FixedWindowRateLimiter(limit=2, window=10, clock=mock_clock)
    client_id = "test_user_1"

    # Request 1 (T=100.0) -> Allowed, Remaining = 1, Reset = 110
    allowed, remaining, reset_at = unit_limiter.check_rate_limit(client_id)
    assert allowed is True
    assert remaining == 1
    assert reset_at == 110

    # Request 2 (T=102.5) -> Allowed, Remaining = 0, Reset = 110
    current_time = 102.5
    allowed, remaining, reset_at = unit_limiter.check_rate_limit(client_id)
    assert allowed is True
    assert remaining == 0
    assert reset_at == 110

    # Request 3 (T=105.0) -> Blocked (Remaining = 0, Reset = 110)
    current_time = 105.0
    allowed, remaining, reset_at = unit_limiter.check_rate_limit(client_id)
    assert allowed is False
    assert remaining == 0
    assert reset_at == 110

    # Request 4 (T=110.1) -> Allowed (Window resets! Reset = 120, Remaining = 1)
    current_time = 110.1
    allowed, remaining, reset_at = unit_limiter.check_rate_limit(client_id)
    assert allowed is True
    assert remaining == 1
    assert reset_at == 120
