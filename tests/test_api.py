import pytest
from fastapi.testclient import TestClient
from src.main import app, limiter
from src.limiters.fixed_window import FixedWindowRateLimiter
from src.limiters.sliding_window import SlidingWindowRateLimiter

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


def test_sliding_window_unit_logic():
    """
    Unit test for SlidingWindowRateLimiter to verify sliding log time logic
    using a mock clock.
    """
    current_time = 100.0
    def mock_clock():
        return current_time

    # Config: 2 requests per 10 seconds
    unit_limiter = SlidingWindowRateLimiter(limit=2, window=10, clock=mock_clock)
    client_id = "test_user_2"

    # Request 1 (T=100.0) -> Allowed
    allowed, remaining, reset_at = unit_limiter.check_rate_limit(client_id)
    assert allowed is True
    assert remaining == 1
    assert reset_at == 110

    # Request 2 (T=105.0) -> Allowed
    current_time = 105.0
    allowed, remaining, reset_at = unit_limiter.check_rate_limit(client_id)
    assert allowed is True
    assert remaining == 0
    assert reset_at == 110

    # Request 3 (T=108.0) -> Blocked (limit is 2, active window [98, 108] has T=100 and T=105)
    current_time = 108.0
    allowed, remaining, reset_at = unit_limiter.check_rate_limit(client_id)
    assert allowed is False
    assert remaining == 0
    assert reset_at == 110

    # Request 4 (T=110.1) -> Allowed (active window [100.1, 110.1] has only T=105. T=100 has expired!)
    # Log becomes [105.0, 110.1]
    current_time = 110.1
    allowed, remaining, reset_at = unit_limiter.check_rate_limit(client_id)
    assert allowed is True
    assert remaining == 0
    assert reset_at == 115  # Oldest is now 105.0, reset is 105.0 + 10 = 115

    # Request 5 (T=112.0) -> Blocked (active window [102.0, 112.0] contains 105.0 and 110.1, which is 2 requests)
    current_time = 112.0
    allowed, remaining, reset_at = unit_limiter.check_rate_limit(client_id)
    assert allowed is False
    assert remaining == 0
    assert reset_at == 115


def test_fixed_vs_sliding_boundary_burst():
    """
    Directly compare Fixed Window and Sliding Window under boundary burst traffic.
    """
    current_time = 99.0
    def mock_clock():
        return current_time

    # Both configured for 2 requests per 10 seconds
    fixed_limiter = FixedWindowRateLimiter(limit=2, window=10, clock=mock_clock)
    sliding_limiter = SlidingWindowRateLimiter(limit=2, window=10, clock=mock_clock)
    client_id = "test_user_3"

    # --- Step 1: Burst of 2 requests at the end of the current fixed window (T=99.0) ---
    assert fixed_limiter.check_rate_limit(client_id)[0] is True
    assert fixed_limiter.check_rate_limit(client_id)[0] is True

    assert sliding_limiter.check_rate_limit(client_id)[0] is True
    assert sliding_limiter.check_rate_limit(client_id)[0] is True

    # --- Step 2: Burst of 2 requests at the start of the next fixed window (T=101.0) ---
    current_time = 101.0

    # Fixed Window allows both, because it's a new window ([100, 110]).
    # Thus, Fixed Window allowed 4 requests in a 2-second span (T=99 to T=101).
    assert fixed_limiter.check_rate_limit(client_id)[0] is True
    assert fixed_limiter.check_rate_limit(client_id)[0] is True

    # Sliding Window blocks both, because the window [91, 101] already contains the 2 requests from T=99.0.
    # Sliding Window correctly enforces the limit over the sliding interval.
    assert sliding_limiter.check_rate_limit(client_id)[0] is False
    assert sliding_limiter.check_rate_limit(client_id)[0] is False

