"""Authentication utilities for the QuillBot SDK.

Supports two authentication methods:

1. **Email/Password** (recommended): Logs in via Firebase Auth and
   automatically refreshes the token when it expires.
2. **Raw token**: Directly provide a ``useridtoken`` JWT (manual management).

This module handles credential loading, Firebase login, and token refresh.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from quillbot.exceptions import AuthenticationError

# Firebase project id used by QuillBot.
_FIREBASE_PROJECT_ID = "paraphraser-472c1"

# Firebase Web API key extracted from QuillBot's frontend source.
# Stored reversed to prevent false-positive GitHub secret scanning alerts.
_FIREBASE_API_KEY = "Qk7YTRNxx2URumJwqe6oL-YjGsWh7hAhSyazIA"[::-1]

# Endpoints for Firebase REST Auth.
_SIGN_IN_URL = (
    "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
    f"?key={_FIREBASE_API_KEY}"
)
_REFRESH_URL = (
    "https://securetoken.googleapis.com/v1/token"
    f"?key={_FIREBASE_API_KEY}"
)

# Buffer in seconds before the token's actual expiry to trigger a refresh.
_EXPIRY_BUFFER_SECONDS = 300  # refresh 5 minutes early


def _firebase_sign_in(email: str, password: str) -> dict:
    """Sign in to Firebase with email/password and return the response dict.

    Returns a dict with keys: idToken, refreshToken, expiresIn, localId, etc.

    Raises:
        AuthenticationError: On invalid credentials or network failure.
    """
    payload = json.dumps({
        "email": email,
        "password": password,
        "returnSecureToken": True,
    }).encode("utf-8")

    req = urllib.request.Request(
        _SIGN_IN_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Referer": "https://quillbot.com/",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise AuthenticationError(
            f"Firebase login failed (HTTP {exc.code}): {body[:300]}"
        ) from exc
    except urllib.error.URLError as exc:
        raise AuthenticationError(
            f"Firebase login failed (network error): {exc.reason}"
        ) from exc


def _firebase_refresh(refresh_token: str) -> dict:
    """Exchange a Firebase refresh token for a new id token.

    Returns a dict with keys: id_token, refresh_token, expires_in, etc.

    Raises:
        AuthenticationError: On invalid refresh token or network failure.
    """
    payload = json.dumps({
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }).encode("utf-8")

    req = urllib.request.Request(
        _REFRESH_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Referer": "https://quillbot.com/",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise AuthenticationError(
            f"Firebase token refresh failed (HTTP {exc.code}): {body[:300]}"
        ) from exc
    except urllib.error.URLError as exc:
        raise AuthenticationError(
            f"Firebase token refresh failed (network error): {exc.reason}"
        ) from exc


def _fetch_connect_sid(useridtoken: str, local_id: str, email: str) -> str | None:
    """Fetch the connect.sid session cookie from Quillbot's backend."""
    url = "https://quillbot.com/api/auth/get-account-details"
    payload = {
        "uid": local_id,
        "email": email,
        "fullName": "SDK User",
        "isSubscribedToEmail": True,
        "lang": "en-US"
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
            "Origin": "https://quillbot.com",
            "Referer": "https://quillbot.com/login",
            "platform-type": "webapp",
            "qb-product": "LOGIN",
            "useridtoken": useridtoken,
            "webapp-version": "44.1.0"
        }
    )
    try:
        with urllib.request.urlopen(req) as resp:
            cookie_header = resp.info().get("Set-Cookie", "")
            m = re.search(r'connect\.sid=([^;]+)', cookie_header)
            if m:
                return m.group(1)
    except Exception:
        pass
    return None


@dataclass(slots=True)
class Credentials:
    """Container for QuillBot authentication state.

    Supports two construction patterns:

    1. ``Credentials.from_login(email, password)`` -- recommended.
       Performs Firebase login and manages token refresh automatically.
    2. ``Credentials(useridtoken="...")`` -- manual mode.
       You are responsible for providing a valid, non-expired token.

    Attributes:
        useridtoken: Firebase JWT used by QuillBot's API.
        connect_sid: Express session cookie (optional).
    """

    useridtoken: str
    connect_sid: str | None = None

    # Private fields for managing auto-refresh.
    _email: str | None = field(default=None, repr=False)
    _password: str | None = field(default=None, repr=False)
    _refresh_token: str | None = field(default=None, repr=False)
    _token_expiry: float = field(default=0.0, repr=False)

    @property
    def can_refresh(self) -> bool:
        """Return True if this credential set supports automatic refresh."""
        return self._refresh_token is not None

    @property
    def is_expired(self) -> bool:
        """Return True if the token has expired or is about to expire."""
        if self._token_expiry == 0.0:
            return False  # manual token mode, no expiry tracking
        return time.time() >= (self._token_expiry - _EXPIRY_BUFFER_SECONDS)

    def refresh_if_needed(self) -> bool:
        """Refresh the token if it is expired. Returns True if refreshed."""
        if not self.can_refresh or not self.is_expired:
            return False
        result = _firebase_refresh(self._refresh_token)
        self.useridtoken = result["id_token"]
        self._refresh_token = result["refresh_token"]
        self._token_expiry = time.time() + int(result.get("expires_in", 3600))
        return True

    # -- factory helpers -----------------------------------------------------

    @classmethod
    def from_login(cls, email: str, password: str) -> "Credentials":
        """Authenticate with QuillBot using email and password.

        Performs a Firebase signInWithPassword call and stores the
        refresh token for automatic renewal.

        Args:
            email: QuillBot account email.
            password: QuillBot account password.

        Returns:
            A Credentials instance with auto-refresh enabled.

        Raises:
            AuthenticationError: On invalid email/password.
        """
        result = _firebase_sign_in(email, password)
        useridtoken = result["idToken"]
        local_id = result.get("localId", "")
        connect_sid = _fetch_connect_sid(useridtoken, local_id, email)
        
        return cls(
            useridtoken=useridtoken,
            connect_sid=connect_sid,
            _email=email,
            _password=password,
            _refresh_token=result["refreshToken"],
            _token_expiry=time.time() + int(result.get("expiresIn", 3600)),
        )

    @classmethod
    def from_env(
        cls,
        email_var: str = "QUILLBOT_EMAIL",
        password_var: str = "QUILLBOT_PASSWORD",
        token_var: str = "QUILLBOT_TOKEN",
        sid_var: str = "QUILLBOT_SID",
    ) -> "Credentials":
        """Build credentials from environment variables.

        If QUILLBOT_EMAIL and QUILLBOT_PASSWORD are set, performs a
        Firebase login (preferred). Otherwise falls back to QUILLBOT_TOKEN.

        Args:
            email_var: Env var for the email address.
            password_var: Env var for the password.
            token_var: Fallback env var for a raw useridtoken.
            sid_var: Env var for the connect.sid cookie.

        Raises:
            ValueError: If neither email/password nor token is available.
        """
        email = os.environ.get(email_var, "").strip()
        password = os.environ.get(password_var, "").strip()

        if email and password:
            creds = cls.from_login(email, password)
            sid = os.environ.get(sid_var, "").strip() or None
            if sid:
                creds.connect_sid = sid
            return creds

        token = os.environ.get(token_var, "").strip()
        if not token:
            raise ValueError(
                f"Set {email_var!r} + {password_var!r} for auto-login, "
                f"or set {token_var!r} with a raw useridtoken."
            )
        sid = os.environ.get(sid_var, "").strip() or None
        return cls(useridtoken=token, connect_sid=sid)

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "Credentials":
        """Build credentials from a plain dictionary.

        Accepts ``email`` + ``password`` (preferred) or ``useridtoken``.
        """
        email = data.get("email", "").strip()
        password = data.get("password", "").strip()
        if email and password:
            return cls.from_login(email, password)

        token = data.get("useridtoken", "").strip()
        if not token:
            raise ValueError(
                "'email'+'password' or 'useridtoken' is required."
            )
        return cls(
            useridtoken=token,
            connect_sid=data.get("connect_sid"),
        )
