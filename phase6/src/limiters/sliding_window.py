import time
import threading
from typing import Tuple, Dict, List, Callable
from src.limiters.base import BaseRateLimiter

class SlidingWindowRateLimiter(BaseRateLimiter):
    """
    In-memory implementation of the Sliding Window Log rate-limiting algorithm.
    """
    def __init__(self, limit: int, window: int, clock: Callable[[], float] = time.time):
        """
        Args:
            limit: Maximum number of requests allowed within the window.
            window: Time window size in seconds.
            clock: A callable returning the current time in seconds (defaults to time.time).
        """
        self.limit = limit
        self.window = window
        self.clock = clock
        # Store layout: {client_id: [timestamps]}
        self.store: Dict[str, List[float]] = {}
        self.lock = threading.Lock()

    def check_rate_limit(self, client_id: str) -> Tuple[bool, int, int]:
        now = self.clock()
        window_start = now - self.window

        with self.lock:
            if client_id not in self.store:
                self.store[client_id] = [now]
                remaining = self.limit - 1
                reset_at = now + self.window
                return True, remaining, int(reset_at)

            # Retrieve and filter the request timestamps to only keep active ones
            log = self.store[client_id]
            filtered_log = [t for t in log if t > window_start]

            if len(filtered_log) < self.limit:
                # Allow the request and record the timestamp
                filtered_log.append(now)
                self.store[client_id] = filtered_log
                remaining = self.limit - len(filtered_log)
                reset_at = filtered_log[0] + self.window
                return True, remaining, int(reset_at)
            else:
                # Block the request
                self.store[client_id] = filtered_log
                reset_at = filtered_log[0] + self.window if filtered_log else now + self.window
                return False, 0, int(reset_at)
