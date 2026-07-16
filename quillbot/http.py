"""Low-level HTTP transport for the QuillBot SDK.

Wraps ``httpx.Client`` with the exact headers, cookies, and error handling
that QuillBot's Node.js backend expects.  Every request is routed through
``post_json`` which handles authentication headers, response parsing, and
error translation into SDK exceptions.
"""

from __future__ import annotations

from typing import Any

import httpx

from quillbot.auth import Credentials
from quillbot.exceptions import APIError, AuthenticationError, RateLimitError

# The base URL shared by all QuillBot API endpoints.
BASE_URL = "https://quillbot.com"

# Default headers that every request must carry.
_DEFAULT_HEADERS: dict[str, str] = {
    "user-agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
    ),
    "accept": "application/json, text/plain, */*",
    "content-type": "application/json",
    "origin": BASE_URL,
    "webapp-version": "44.1.0",
}


class HttpClient:
    """Thin wrapper around ``httpx.Client`` tuned for QuillBot.

    This class is an internal implementation detail.  Users interact with
    the public ``QuillBot`` class in ``client.py``.
    """

    def __init__(self, credentials: Credentials, timeout: float = 30.0) -> None:
        cookies: dict[str, str] = {
            "useridtoken": credentials.useridtoken,
        }
        if credentials.connect_sid:
            cookies["connect.sid"] = credentials.connect_sid

        headers = {
            **_DEFAULT_HEADERS,
            "useridtoken": credentials.useridtoken,
        }

        self._client = httpx.Client(
            base_url=BASE_URL,
            headers=headers,
            cookies=cookies,
            timeout=timeout,
            follow_redirects=True,
        )

    # -- public interface ----------------------------------------------------

    def post_json(
        self,
        path: str,
        payload: dict[str, Any],
        *,
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Send a JSON POST and return the parsed response body.

        Args:
            path: API path relative to BASE_URL (e.g. ``/api/paraphraser/...``).
            payload: JSON-serialisable request body.
            extra_headers: Per-request header overrides.

        Returns:
            The parsed JSON response as a dict.

        Raises:
            AuthenticationError: On 401 or 408 (SESSION_FAILED).
            RateLimitError: On 429 or when ``x-ratelimit-limit`` is exceeded.
            APIError: On any other non-2xx response.
        """
        headers = extra_headers or {}
        response = self._client.post(path, json=payload, headers=headers)
        return self._handle_response(response)

    def close(self) -> None:
        """Release the underlying connection pool."""
        self._client.close()

    # -- context manager -----------------------------------------------------

    def __enter__(self) -> "HttpClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    # -- internal ------------------------------------------------------------

    @staticmethod
    def _handle_response(response: httpx.Response) -> dict[str, Any]:
        """Translate HTTP status codes into SDK exceptions."""
        status = response.status_code

        if 200 <= status < 300:
            return response.json()

        body = response.text

        if status in (401, 408):
            raise AuthenticationError(
                f"Authentication failed (HTTP {status}). "
                "Your useridtoken may be expired. "
                f"Response: {body[:200]}"
            )

        if status == 429:
            retry_after_raw = response.headers.get("retry-after")
            retry_after = int(retry_after_raw) if retry_after_raw else None
            raise RateLimitError(
                f"Rate limited (HTTP 429). Retry after {retry_after}s.",
                retry_after=retry_after,
            )

        raise APIError(
            f"QuillBot API error (HTTP {status}): {body[:300]}",
            status_code=status,
            body=body,
        )
