"""Data models for QuillBot API responses.

These are simple, immutable containers that stay close to what QuillBot
returns.  They carry the data and provide thin helper methods -- no
decision-making logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Synonym helpers
# ---------------------------------------------------------------------------

SynonymMap = dict[str, list[str]]
"""Mapping of word/phrase to its list of synonym suggestions.

Example::

    {"agile": ["fast", "quick", "nimble"], "fox": ["hound", "feline"]}
"""


# ---------------------------------------------------------------------------
# Paraphrase
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ParaphraseResult:
    """Result returned by :meth:`QuillBot.paraphrase`.

    Attributes:
        original_text: The text that was submitted.
        paraphrased_text: The rewritten text returned by QuillBot.
        alternatives: Other paraphrase candidates (may be empty).
        synonyms: Pre-fetched synonym map for words in the paraphrased text.
            Populated automatically from the ``paraphrase-thesaurus`` bulk
            endpoint so callers can inspect available replacements without
            making another network call.
        phrases: The chunked phrases that QuillBot uses internally.
        raw: The full raw JSON response from ``/single-paraphrase``, kept
            for debugging and forward-compatibility.
    """

    original_text: str
    paraphrased_text: str
    alternatives: list[str] = field(default_factory=list)
    synonyms: SynonymMap = field(default_factory=dict)
    phrases: list[str] = field(default_factory=list)
    raw: dict = field(default_factory=dict, repr=False)

    def available_replacements(self, word: str) -> list[str]:
        """Return the synonym list for *word*, or an empty list."""
        return self.synonyms.get(word, [])


# ---------------------------------------------------------------------------
# Summarize
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SummarizeResult:
    """Result returned by :meth:`QuillBot.summarize`.

    Attributes:
        original_text: The text that was submitted.
        summary: The condensed text returned by QuillBot.
        summary_type: The summarisation algorithm used (e.g. ``"abs"``).
        raw: The full raw JSON response.
    """

    original_text: str
    summary: str
    summary_type: str = "abs"
    raw: dict = field(default_factory=dict, repr=False)
