import concurrent.futures
from src.limiters.fixed_window import FixedWindowRateLimiter
from src.limiters.sliding_window import SlidingWindowRateLimiter
from src.limiters.token_bucket import TokenBucketRateLimiter

def test_fixed_window_concurrency():
    """
    Stress test FixedWindowRateLimiter with concurrent requests.
    Verifies that locking prevents race conditions and strictly allows exactly the limit (10).
    """
    limiter = FixedWindowRateLimiter(limit=10, window=60)
    client_id = "concurrent_client_fw"

    num_threads = 100
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(limiter.check_rate_limit, client_id) for _ in range(num_threads)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    # Count how many requests were allowed
    allowed_count = sum(1 for is_allowed, _, _ in results if is_allowed)
    
    # Strictly check that the thread-safe implementation allowed exactly the limit
    assert allowed_count == 10


def test_sliding_window_concurrency():
    """
    Stress test SlidingWindowRateLimiter with concurrent requests.
    Verifies that locking prevents list corruption and strictly allows exactly the limit (10).
    """
    limiter = SlidingWindowRateLimiter(limit=10, window=60)
    client_id = "concurrent_client_sw"

    num_threads = 100
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(limiter.check_rate_limit, client_id) for _ in range(num_threads)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    allowed_count = sum(1 for is_allowed, _, _ in results if is_allowed)
    assert allowed_count == 10


def test_token_bucket_concurrency():
    """
    Stress test TokenBucketRateLimiter with concurrent requests.
    Verifies that locking prevents refill rate conflicts and strictly allows exactly the capacity (10).
    """
    # Capacity = 10, Refill = 1.0 tokens/second (no refills during the instant thread execution)
    limiter = TokenBucketRateLimiter(capacity=10, refill_rate=1.0)
    client_id = "concurrent_client_tb"

    num_threads = 100
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(limiter.check_rate_limit, client_id) for _ in range(num_threads)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    allowed_count = sum(1 for is_allowed, _, _ in results if is_allowed)
    assert allowed_count == 10
