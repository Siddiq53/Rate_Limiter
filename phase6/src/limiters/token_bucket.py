import time
import threading
from typing import Tuple, Dict, Callable
from src.limiters.base import BaseRateLimiter

class TokenBucketRateLimiter(BaseRateLimiter):
    """
    In-memory implementation of the Token Bucket rate-limiting algorithm.
    """
    def __init__(self, capacity: int, refill_rate: float, clock: Callable[[], float] = time.time):
        """
        Args:
            capacity: Maximum number of tokens the bucket can hold.
            refill_rate: Number of tokens added to the bucket per second.
            clock: A callable returning the current time in seconds (defaults to time.time).
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.clock = clock
        # Store layout: {client_id: (tokens, last_update_time)}
        self.store: Dict[str, Tuple[float, float]] = {}
        self.lock = threading.Lock()

    def check_rate_limit(self, client_id: str) -> Tuple[bool, int, int]:
        now = self.clock()

        with self.lock:
            if client_id not in self.store:
                # First request: initialize bucket with (capacity - 1) tokens since we consume 1 immediately
                tokens = self.capacity - 1.0
                self.store[client_id] = (tokens, now)
                reset_at = now + (self.capacity - tokens) / self.refill_rate
                return True, int(tokens), int(reset_at)

            last_tokens, last_update = self.store[client_id]

            # Calculate time elapsed and new tokens to add
            elapsed = max(0.0, now - last_update)
            refill = elapsed * self.refill_rate
            tokens = min(float(self.capacity), last_tokens + refill)

            if tokens >= 1.0:
                # Request allowed: consume 1 token and update state
                tokens -= 1.0
                self.store[client_id] = (tokens, now)
                reset_at = now + (self.capacity - tokens) / self.refill_rate
                return True, int(tokens), int(reset_at)
            else:
                # Request blocked: state is updated with refilled tokens but no tokens are consumed
                self.store[client_id] = (tokens, now)
                reset_at = now + (self.capacity - tokens) / self.refill_rate
                return False, 0, int(reset_at)
