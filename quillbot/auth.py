"""Authentication utilities for the QuillBot SDK.

The only credential required by QuillBot's API is the Firebase JWT
called ``useridtoken``.  It is sent both as an HTTP header and as a cookie.
The ``connect.sid`` session cookie is optional but improves reliability.

This module provides helpers to load credentials from environment variables
or from a simple dict, keeping credential handling in one place.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Credentials:
    """Immutable container for QuillBot authentication tokens.

    Attributes:
        useridtoken: Firebase JWT issued by QuillBot's auth system.
        connect_sid: Express session cookie (optional, but recommended).
    """

    useridtoken: str
    connect_sid: str | None = None

    # -- factory helpers -----------------------------------------------------

    @classmethod
    def from_env(
        cls,
        token_var: str = "QUILLBOT_TOKEN",
        sid_var: str = "QUILLBOT_SID",
    ) -> "Credentials":
        """Build credentials from environment variables.

        Args:
            token_var: Name of the env var holding the useridtoken.
            sid_var: Name of the env var holding connect.sid (optional).

        Raises:
            ValueError: If the token env var is unset or empty.
        """
        token = os.environ.get(token_var, "").strip()
        if not token:
            raise ValueError(
                f"Environment variable {token_var!r} is not set. "
                "Export your QuillBot useridtoken before using the SDK."
            )
        sid = os.environ.get(sid_var, "").strip() or None
        return cls(useridtoken=token, connect_sid=sid)

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "Credentials":
        """Build credentials from a plain dictionary.

        Expected keys: ``useridtoken`` (required), ``connect_sid`` (optional).
        """
        token = data.get("useridtoken", "").strip()
        if not token:
            raise ValueError("'useridtoken' is required in the credentials dict.")
        return cls(
            useridtoken=token,
            connect_sid=data.get("connect_sid"),
        )
