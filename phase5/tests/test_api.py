import pytest
from fastapi.testclient import TestClient
from src.main import app, limiter
from src.limiters.fixed_window import FixedWindowRateLimiter
from src.limiters.sliding_window import SlidingWindowRateLimiter
from src.limiters.token_bucket import TokenBucketRateLimiter

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


def test_token_bucket_unit_logic():
    """
    Unit test for TokenBucketRateLimiter verifying burst, empty, refill, and sustained traffic patterns.
    """
    current_time = 100.0
    def mock_clock():
        return current_time

    # Config: capacity=5, refill_rate=2.0 tokens/second (1 token per 0.5 seconds)
    limiter = TokenBucketRateLimiter(capacity=5, refill_rate=2.0, clock=mock_clock)
    client_id = "test_user_tb"

    # --- 1. Burst Traffic ---
    # We send 5 rapid requests at T=100.0. All should be allowed.
    # Remaining tokens: 4, 3, 2, 1, 0
    for expected_remaining in [4, 3, 2, 1, 0]:
        allowed, remaining, reset_at = limiter.check_rate_limit(client_id)
        assert allowed is True
        assert remaining == expected_remaining
        # Reset time should increase as tokens decrease: T + (capacity - tokens) / refill_rate
        expected_reset = 100.0 + (5.0 - remaining) / 2.0
        assert reset_at == int(expected_reset)

    # --- 2. Empty Bucket ---
    # The 6th request at T=100.0 should be blocked (0 tokens)
    allowed, remaining, reset_at = limiter.check_rate_limit(client_id)
    assert allowed is False
    assert remaining == 0
    assert reset_at == int(100.0 + 5.0 / 2.0)  # 102.5 -> 102

    # --- 3. Token Refill ---
    # Advance time to T=101.5 (1.5 seconds elapsed -> 3.0 tokens refilled).
    # Request 1 at T=101.5 allowed, consuming 1 token. Remaining tokens: 2.0.
    current_time = 101.5
    allowed, remaining, reset_at = limiter.check_rate_limit(client_id)
    assert allowed is True
    assert remaining == 2
    assert reset_at == int(101.5 + (5.0 - 2.0) / 2.0)  # 103

    # Consume the remaining 2 refilled tokens
    assert limiter.check_rate_limit(client_id)[0] is True  # Remaining: 1
    assert limiter.check_rate_limit(client_id)[0] is True  # Remaining: 0
    assert limiter.check_rate_limit(client_id)[0] is False # Blocked (0 tokens)

    # --- 4. Sustained Traffic ---
    # Request sequentially at T=102.0, T=102.5, T=103.0 (every 0.5s).
    # In each step, 0.5s * 2.0 = 1.0 token is refilled, and immediately consumed.
    # Therefore, all requests should be allowed and remaining tokens should be 0.
    for t in [102.0, 102.5, 103.0]:
        current_time = t
        allowed, remaining, reset_at = limiter.check_rate_limit(client_id)
        assert allowed is True
        assert remaining == 0


