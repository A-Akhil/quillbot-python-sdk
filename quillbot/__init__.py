"""quillbot -- Lightweight Python SDK for QuillBot."""

from quillbot.client import QuillBot
from quillbot.models import ParaphraseResult, SynonymMap, SummarizeResult
from quillbot.exceptions import (
    QuillBotError,
    AuthenticationError,
    RateLimitError,
    APIError,
)

__all__ = [
    "QuillBot",
    "ParaphraseResult",
    "SynonymMap",
    "SummarizeResult",
    "QuillBotError",
    "AuthenticationError",
    "RateLimitError",
    "APIError",
]
