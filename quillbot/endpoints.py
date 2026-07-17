"""Raw endpoint wrappers for QuillBot's HTTP API.

Each function maps 1-to-1 to a QuillBot API endpoint.  They accept an
``HttpClient``, build the correct payload, call the endpoint, and return
the raw JSON dict.  No response parsing happens here -- that is the job
of ``client.py`` which converts raw dicts into typed ``models``.

Keeping endpoint wrappers separate makes it easy to add new endpoints
later without touching the public API or response parsing.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from quillbot.http import HttpClient


# ---------------------------------------------------------------------------
# Paraphraser
# ---------------------------------------------------------------------------

_PARAPHRASER_HEADERS = {
    "platform-type": "webapp",
    "qb-product": "PARAPHRASER",
    "qb-dialect": "en-us",
    "referer": "https://quillbot.com/paraphrasing-tool",
}


class ParaphraseMode(int, Enum):
    """Common paraphrase rewriting modes."""
    FLUENCY = 0
    STANDARD = 2
    CREATIVE = 6
    SHORTEN = 7
    EXPAND = 8
    FORMAL = 9
    SIMPLE = 10
    NARRATIVE = 12
    HUMANIZER = 12
    ACADEMIC = 99
    CUSTOM = 100


class Language(str, Enum):
    """Available input languages for paraphrasing and translation."""
    AFRIKAANS = "af"
    CHINESE_SIMPLIFIED = "zh"
    DANISH = "da"
    DUTCH = "nl"
    ENGLISH_AU = "en-AU"
    ENGLISH_CA = "en-CA"
    ENGLISH_UK = "en-GB"
    ENGLISH_US = "en-US"
    ENGLISH = "en"
    FRENCH = "fr"
    GERMAN = "de"
    HINDI = "hi"
    INDONESIAN = "id"
    ITALIAN = "it"
    JAPANESE = "ja"
    MALAY = "ms"
    NORWEGIAN = "no"
    POLISH = "pl"
    PORTUGUESE_BR = "pt"
    ROMANIAN = "ro"
    RUSSIAN = "ru"
    SPANISH = "es"
    SWEDISH = "sv"
    TAGALOG = "tl"
    TURKISH = "tr"
    UKRAINIAN = "uk"
    VIETNAMESE = "vi"


def single_paraphrase(
    client: HttpClient,
    text: str,
    *,
    mode: int | ParaphraseMode = ParaphraseMode.STANDARD,
    strength: int | None = None,
    frozen_words: list[str] | None = None,
    dialect: str = "US",
    input_lang: str | Language = Language.ENGLISH,
) -> dict[str, Any]:
    """Call ``POST /api/paraphraser/single-paraphrase/{mode}``.

    Args:
        client: Authenticated HTTP client.
        text: The sentence to paraphrase.
        mode: Paraphrase mode id (99 = Custom, 0 = Standard, etc.).
        strength: Rewriting aggressiveness. Valid values:
            0, 2, 6, 7, 8, 9, 10, 12, 13, 15, 16, 99, 100, 101, 201, 202, 203.
        frozen_words: Words to leave unchanged.
        dialect: Target English dialect (``"US"`` or ``"UK"``).
        input_lang: Source language code.

    Returns:
        Raw JSON response dict.
    """
    if strength is None:
        strength = int(mode)
        
    payload: dict[str, Any] = {
        "text": text,
        "strength": strength,
        "autoflip": False,
        "wikify": False,
        "fthresh": -1,
        "inputLang": input_lang.value if hasattr(input_lang, "value") else input_lang,
        "quoteIndex": -1,
        "frozenWords": frozen_words or [],
        "nBeams": 4,
        "freezeQuotes": True,
        "preferActive": False,
        "dialect": dialect,
        "promptVersion": "v2",
        "multilingualModelVersion": "v2",
    }
    if mode == 99:
        payload["customModeName"] = ""

    headers = dict(_PARAPHRASER_HEADERS)
    if mode == 12:
        headers["qb-product"] = "AI_HUMANIZER"
        headers["referer"] = "https://quillbot.com/ai-humanizer"

    return client.post_json(
        f"/api/paraphraser/single-paraphrase/{int(mode)}",
        payload,
        extra_headers=headers,
    )


def paraphrase_thesaurus(
    client: HttpClient,
    phrases: list[str],
    *,
    mode: int = 99,
) -> dict[str, Any]:
    """Call ``POST /api/paraphraser/paraphrase-thesaurus``.

    Fetches bulk synonyms for the phrases in the paraphrased output.

    Args:
        client: Authenticated HTTP client.
        phrases: List of phrase strings.
        mode: Paraphrase mode id.

    Returns:
        Raw JSON response dict.
    """
    payload: dict[str, Any] = {
        "phrases": phrases,
        "mode": mode,
    }
    return client.post_json(
        "/api/paraphraser/paraphrase-thesaurus",
        payload,
        extra_headers=_PARAPHRASER_HEADERS,
    )


def paraphrase_phrase(
    client: HttpClient,
    text: str,
    phrases: list[str],
    *,
    mode: int = 99,
    w1: float = 0.6,
    w2: float = 0.4,
) -> dict[str, Any]:
    """Call ``POST /api/utils/paraphrase-phrase``.

    Fetches context-aware synonyms for a specific sentence.

    Args:
        client: Authenticated HTTP client.
        text: The full sentence containing the word.
        phrases: The chunked phrases of the sentence.
        mode: Paraphrase mode id.
        w1: Weight parameter (controls suggestion style).
        w2: Weight parameter (controls suggestion style).

    Returns:
        Raw JSON response dict.
    """
    payload: dict[str, Any] = {
        "phrases": phrases,
        "text": text,
        "w1": w1,
        "w2": w2,
        "mode": mode,
    }
    return client.post_json(
        "/api/utils/paraphrase-phrase",
        payload,
        extra_headers=_PARAPHRASER_HEADERS,
    )


def chunker(
    client: HttpClient,
    text: str,
) -> dict[str, Any]:
    """Call ``POST /api/paraphraser/chunker``.

    Splits a sentence into the phrase tokens that QuillBot uses for
    synonym lookups and rendering.

    Args:
        client: Authenticated HTTP client.
        text: The sentence to tokenize.

    Returns:
        Raw JSON response dict containing ``data.segments.phrases``.
    """
    payload: dict[str, Any] = {"text": text}
    return client.post_json(
        "/api/paraphraser/chunker",
        payload,
        extra_headers=_PARAPHRASER_HEADERS,
    )


def sentence_splitter(
    client: HttpClient,
    text: str,
) -> dict[str, Any]:
    """Call ``POST /api/utils/sentence-spiltter``.

    Splits a large paragraph into individual sentences using QuillBot's backend.

    Args:
        client: Authenticated HTTP client.
        text: The text to split.

    Returns:
        Raw JSON response dict containing ``data.sentences``.
    """
    payload: dict[str, Any] = {"text": text, "fallback": True}
    return client.post_json(
        "/api/utils/sentence-spiltter",
        payload,
        extra_headers=_PARAPHRASER_HEADERS,
    )


# ---------------------------------------------------------------------------
# Summarizer
# ---------------------------------------------------------------------------

_SUMMARIZER_HEADERS = {
    "platform-type": "webapp",
    "qb-product": "SUMMARIZER",
    "referer": "https://quillbot.com/summarize",
}


def summarize(
    client: HttpClient,
    text: str,
    *,
    summary_type: str = "abs",
    ratio: float = 0.2,
    length: str = "short",
) -> dict[str, Any]:
    """Call ``POST /api/summarizer/summarize-para/{summary_type}``.

    Args:
        client: Authenticated HTTP client.
        text: The text to summarize.
        summary_type: Algorithm -- ``"abs"`` (abstractive) or ``"key"``
            (key-sentences / extractive).
        ratio: Target compression ratio (0.0-1.0).
        length: Desired length hint (``"short"``, ``"concise"``, ``"long"``).

    Returns:
        Raw JSON response dict.
    """
    payload: dict[str, Any] = {
        "para": text,
        "type": summary_type,
        "ratio": ratio,
        "length": length,
    }
    return client.post_json(
        f"/api/summarizer/summarize-para/{summary_type}",
        payload,
        extra_headers=_SUMMARIZER_HEADERS,
    )
