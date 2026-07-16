"""Custom exceptions for the QuillBot SDK.

Every exception inherits from QuillBotError so callers can catch broadly
or narrowly as they prefer.
"""


class QuillBotError(Exception):
    """Base exception for all QuillBot SDK errors."""


class AuthenticationError(QuillBotError):
    """Raised when the useridtoken is missing, expired, or rejected (HTTP 401/408)."""


class RateLimitError(QuillBotError):
    """Raised when QuillBot returns rate-limit headers or HTTP 429.

    Attributes:
        retry_after: Seconds to wait before retrying, if the server provided
                     a Retry-After header.
    """

    def __init__(self, message: str, retry_after: int | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class APIError(QuillBotError):
    """Raised for any unexpected HTTP error from the QuillBot backend.

    Attributes:
        status_code: The HTTP status code returned.
        body: The raw response body, if available.
    """

    def __init__(
        self, message: str, status_code: int, body: str | None = None
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.body = body
