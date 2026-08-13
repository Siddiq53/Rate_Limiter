import time
from typing import Tuple, Dict, Callable
from src.limiters.base import BaseRateLimiter

class FixedWindowRateLimiter(BaseRateLimiter):
    """
    In-memory implementation of the Fixed Window rate-limiting algorithm.
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
        # Store layout: {client_id: (window_id, count)}
        self.store: Dict[str, Tuple[int, int]] = {}

    def check_rate_limit(self, client_id: str) -> Tuple[bool, int, int]:
        now = self.clock()
        
        # Calculate current window ID
        current_window_id = int(now / self.window)
        # Calculate when the current window ends
        reset_at = (current_window_id + 1) * self.window

        if client_id not in self.store:
            # Client first request - register in current window with count 1
            self.store[client_id] = (current_window_id, 1)
            remaining = self.limit - 1
            return True, remaining, int(reset_at)

        last_window_id, count = self.store[client_id]

        if current_window_id != last_window_id:
            # Boundary crossed: reset count for the new window
            self.store[client_id] = (current_window_id, 1)
            remaining = self.limit - 1
            return True, remaining, int(reset_at)

        # Within the same window
        if count < self.limit:
            new_count = count + 1
            self.store[client_id] = (current_window_id, new_count)
            remaining = self.limit - new_count
            return True, remaining, int(reset_at)
        else:
            # Limit exceeded
            return False, 0, int(reset_at)
