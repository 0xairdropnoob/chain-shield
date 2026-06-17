"""
Chain Sentinel — Custom Exceptions
"""


class ChainSentinelError(Exception):
    """Base exception for Chain Sentinel SDK."""

    def __init__(self, message: str, status_code: int = None, response_body: dict = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_body = response_body

    def __str__(self) -> str:
        if self.status_code:
            return f"[{self.status_code}] {self.message}"
        return self.message


class RateLimitError(ChainSentinelError):
    """Raised when rate limit is exceeded (HTTP 429)."""

    def __init__(self, message: str, retry_after: int = None, **kwargs):
        super().__init__(message, status_code=429, **kwargs)
        self.retry_after = retry_after


class AuthenticationError(ChainSentinelError):
    """Raised when API key is invalid or missing (HTTP 401)."""

    def __init__(self, message: str = "Invalid or missing API key", **kwargs):
        super().__init__(message, status_code=401, **kwargs)


class NotFoundError(ChainSentinelError):
    """Raised when a resource is not found (HTTP 404)."""

    def __init__(self, message: str = "Resource not found", **kwargs):
        super().__init__(message, status_code=404, **kwargs)


class ValidationError(ChainSentinelError):
    """Raised when request validation fails (HTTP 400)."""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, status_code=400, **kwargs)
