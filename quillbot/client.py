"""Public API for the QuillBot SDK.

Usage::

    from quillbot import QuillBot

    bot = QuillBot(useridtoken="...")
    result = bot.paraphrase("The quick brown fox jumps over the lazy dog.")
    print(result.paraphrased_text)
    print(result.synonyms)

The ``QuillBot`` class is the only object most users need to import.
Internally it delegates to the HTTP client and endpoint wrappers.
"""

from __future__ import annotations

from typing import Any

from quillbot.auth import Credentials
from quillbot.http import HttpClient
from quillbot import endpoints
from quillbot.models import ParaphraseResult, SummarizeResult, SynonymMap


class QuillBot:
    """Lightweight client that exposes QuillBot's capabilities over HTTP.

    This class owns an authenticated HTTP session and provides methods that
    mirror QuillBot's features: paraphrasing, synonym retrieval, and
    summarisation.

    It does *not* contain any decision-making logic.  The caller decides
    which word to replace, which suggestion to pick, and how many
    iterations to run.

    Args:
        useridtoken: Firebase JWT from a logged-in QuillBot session.
        connect_sid: Express ``connect.sid`` session cookie (optional).
        timeout: HTTP request timeout in seconds.
    """

    def __init__(
        self,
        useridtoken: str,
        *,
        connect_sid: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        creds = Credentials(useridtoken=useridtoken, connect_sid=connect_sid)
        self._http = HttpClient(creds, timeout=timeout)

    # -- lifecycle -----------------------------------------------------------

    def close(self) -> None:
        """Release the underlying HTTP connection pool."""
        self._http.close()

    def __enter__(self) -> "QuillBot":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    # -- paraphrasing --------------------------------------------------------

    def paraphrase(
        self,
        text: str,
        *,
        mode: int = 99,
        strength: int = 9,
        frozen_words: list[str] | None = None,
        fetch_synonyms: bool = True,
    ) -> ParaphraseResult:
        """Paraphrase *text* and optionally pre-fetch synonyms.

        Args:
            text: The sentence or paragraph to rewrite.
            mode: QuillBot mode id (99=Custom, 0=Standard, etc.).
            strength: Rewriting aggressiveness (0-10).
            frozen_words: Words that must not be changed.
            fetch_synonyms: When ``True`` (default), automatically call the
                thesaurus endpoint to populate ``result.synonyms``.

        Returns:
            A :class:`ParaphraseResult` containing the rewritten text,
            alternative candidates, and (if requested) a pre-fetched
            synonym map.
        """
        raw = endpoints.single_paraphrase(
            self._http,
            text,
            mode=mode,
            strength=strength,
            frozen_words=frozen_words,
        )

        # Extract the primary paraphrase and alternatives from the response.
        paraphrased_text, alternatives, phrases = self._parse_paraphrase(raw)

        # Optionally fetch bulk synonyms for the paraphrased output.
        synonyms: SynonymMap = {}
        if fetch_synonyms and phrases:
            synonyms = self._fetch_thesaurus(paraphrased_text, phrases, mode=mode)

        return ParaphraseResult(
            original_text=text,
            paraphrased_text=paraphrased_text,
            alternatives=alternatives,
            synonyms=synonyms,
            phrases=phrases,
            raw=raw,
        )

    # -- synonyms ------------------------------------------------------------

    def get_synonyms(
        self,
        text: str,
        phrases: list[str],
        *,
        mode: int = 99,
    ) -> SynonymMap:
        """Fetch context-aware synonyms for a sentence.

        This mirrors the ``paraphrase-phrase`` endpoint that the QuillBot
        frontend calls when a user clicks a word.

        Args:
            text: The full sentence.
            phrases: The chunked phrases (as returned in
                :attr:`ParaphraseResult.phrases`).
            mode: Paraphrase mode id.

        Returns:
            A :data:`SynonymMap` mapping each phrase to its suggestions.
        """
        raw = endpoints.paraphrase_phrase(
            self._http, text, phrases, mode=mode
        )
        suggestions: dict[str, list[str]] = (
            raw.get("data", {}).get("suggestions", {})
        )
        return suggestions

    # -- summarisation -------------------------------------------------------

    def summarize(
        self,
        text: str,
        *,
        summary_type: str = "abs",
        ratio: float = 0.2,
        length: str = "short",
    ) -> SummarizeResult:
        """Summarize *text*.

        Args:
            text: The text to condense.
            summary_type: ``"abs"`` (abstractive) or ``"key"`` (extractive).
            ratio: Target compression ratio (0.0-1.0).
            length: Desired length hint (``"short"``, ``"concise"``, ``"long"``).

        Returns:
            A :class:`SummarizeResult` containing the summary.
        """
        raw = endpoints.summarize(
            self._http,
            text,
            summary_type=summary_type,
            ratio=ratio,
            length=length,
        )
        summary = raw.get("data", {}).get("summary", "")
        return SummarizeResult(
            original_text=text,
            summary=summary,
            summary_type=summary_type,
            raw=raw,
        )

    # -- internal helpers ----------------------------------------------------

    @staticmethod
    def _parse_paraphrase(
        raw: dict[str, Any],
    ) -> tuple[str, list[str], list[str]]:
        """Extract text, alternatives, and phrases from the raw response.

        The response structure from ``/single-paraphrase`` nests the
        paraphrased sentences inside ``data[].paras_<N>[].alt`` where
        ``<N>`` varies by mode (e.g. ``paras_100`` for mode 99).

        Returns:
            A tuple of (primary_text, alternative_texts, phrase_tokens).
        """
        data_list = raw.get("data", [])
        if not data_list:
            return "", [], []

        first_entry = data_list[0] if isinstance(data_list, list) else data_list

        # Find the paras_* key dynamically (paras_10, paras_100, etc.)
        paras: list[dict[str, Any]] = []
        for key, value in first_entry.items():
            if key.startswith("paras_") and isinstance(value, list):
                paras = value
                break

        primary = paras[0].get("alt", "") if paras else ""
        alternatives = [p.get("alt", "") for p in paras[1:]]

        # QuillBot also returns segmentation data we can use as phrases.
        segments = first_entry.get("segments", {})
        phrases_data = segments.get("phrases", [])
        phrases = [p.get("phrase", "") for p in phrases_data] if phrases_data else []

        # If no segments in the response, split the primary text on whitespace
        # as a fallback so the thesaurus endpoint still works.
        if not phrases and primary:
            phrases = primary.split()

        return primary, alternatives, phrases

    def _fetch_thesaurus(
        self,
        text: str,
        phrases: list[str],
        *,
        mode: int = 99,
    ) -> SynonymMap:
        """Call the bulk thesaurus endpoint and merge the result."""
        raw = endpoints.paraphrase_thesaurus(
            self._http,
            phrases=phrases,
            mode=mode,
        )
        # The response nests suggestions differently than paraphrase-phrase.
        # It returns per-sentence data; we merge all of them.
        synonyms: SynonymMap = {}
        data = raw.get("data", {})
        if isinstance(data, list):
            for entry in data:
                synonyms.update(entry.get("suggestions", {}))
        elif isinstance(data, dict):
            synonyms.update(data.get("suggestions", {}))
        return synonyms
