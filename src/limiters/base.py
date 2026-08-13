from abc import ABC, abstractmethod
from typing import Tuple

class BaseRateLimiter(ABC):
    """
    Abstract Base Class for rate limiters.
    All rate limiter implementations must inherit from this class and implement
    the check_rate_limit method.
    """

    @abstractmethod
    def check_rate_limit(self, client_id: str) -> Tuple[bool, int, int]:
        """
        Evaluate if a request from a client should be allowed or rate-limited.

        Args:
            client_id: A unique identifier for the client (e.g., IP address, API key).

        Returns:
            A tuple of (is_allowed, remaining, reset_at):
            - is_allowed (bool): True if the request is permitted, False if rate-limited.
            - remaining (int): The number of requests remaining in the current window.
            - reset_at (int): Unix timestamp (seconds) when the current window resets.
        """
        pass
