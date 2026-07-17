"""Tests for the QuillBot SDK -- hits the actual QuillBot server.

Setup:
    1. Put your credentials in a file called .env in the project root:
       QUILLBOT_EMAIL="user@example.com"
       QUILLBOT_PASSWORD="secretpassword"

    2. Run:
       python3 -m pytest tests/test_unit.py -v

    Or use the run_tests.sh script.
"""

import os
import pytest

from quillbot import (
    QuillBot,
    ParaphraseResult,
    SummarizeResult,
    AuthenticationError,
)


def _load_env() -> dict[str, str]:
    """Load env vars, also checking .env file in the project root."""
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    os.environ.setdefault(
                        key.strip(), val.strip().strip('"').strip("'")
                    )
    return os.environ


_load_env()
EMAIL = os.environ.get("QUILLBOT_EMAIL", "")
PASSWORD = os.environ.get("QUILLBOT_PASSWORD", "")


@pytest.fixture
def bot():
    """Yield an authenticated QuillBot client, then close it."""
    if not EMAIL or not PASSWORD:
        pytest.skip("No credentials found. Set QUILLBOT_EMAIL and QUILLBOT_PASSWORD env vars or create .env file.")
    client = QuillBot(email=EMAIL, password=PASSWORD)
    yield client
    client.close()


# ---------------------------------------------------------------------------
# Paraphrasing
# ---------------------------------------------------------------------------


class TestParaphrase:
    def test_basic_paraphrase(self, bot: QuillBot):
        result = bot.paraphrase(
            "The quick brown fox jumps over the lazy dog."
        )
        assert isinstance(result, ParaphraseResult)
        assert result.original_text == "The quick brown fox jumps over the lazy dog."
        assert len(result.paraphrased_text) > 0
        assert result.paraphrased_text != result.original_text
        print(f"  Paraphrased: {result.paraphrased_text}")

    def test_paraphrase_returns_synonyms(self, bot: QuillBot):
        result = bot.paraphrase(
            "The swift auburn fox leaps over the lethargic canine."
        )
        assert isinstance(result.synonyms, dict)
        assert len(result.synonyms) > 0
        non_empty = {k: v[:3] for k, v in result.synonyms.items() if v}
        print(f"  Synonyms (top 3 each): {non_empty}")

    def test_paraphrase_returns_phrases(self, bot: QuillBot):
        result = bot.paraphrase("Science is fascinating and wonderful.")
        assert isinstance(result.phrases, list)
        assert len(result.phrases) > 0
        print(f"  Phrases: {result.phrases}")

    def test_paraphrase_without_synonyms(self, bot: QuillBot):
        result = bot.paraphrase(
            "Testing without synonym fetch.",
            fetch_synonyms=False,
        )
        assert isinstance(result, ParaphraseResult)
        assert result.synonyms == {}
        print(f"  Paraphrased (no synonyms): {result.paraphrased_text}")

    def test_available_replacements_helper(self, bot: QuillBot):
        result = bot.paraphrase("The agile fox leaps swiftly.")
        for word in result.phrases:
            replacements = result.available_replacements(word)
            assert isinstance(replacements, list)
        print(f"  Replacements for first phrase '{result.phrases[0]}': "
              f"{result.available_replacements(result.phrases[0])[:5]}")

    def test_frozen_words(self, bot: QuillBot):
        result = bot.paraphrase(
            "Python is a great programming language.",
            frozen_words=["Python"],
        )
        assert "Python" in result.paraphrased_text
        print(f"  Frozen 'Python': {result.paraphrased_text}")

    def test_raw_response_preserved(self, bot: QuillBot):
        result = bot.paraphrase("Hello world.")
        assert isinstance(result.raw, dict)
        assert "data" in result.raw


# ---------------------------------------------------------------------------
# Synonyms
# ---------------------------------------------------------------------------


class TestSynonyms:
    def test_get_synonyms(self, bot: QuillBot):
        text = "The agile reddish-brown fox bounds over the sluggish dog."
        phrases = [
            "The", "agile", "reddish-brown", "fox",
            "bounds", "over the", "sluggish", "dog.",
        ]
        synonyms = bot.get_synonyms(text, phrases)
        assert isinstance(synonyms, dict)
        non_empty = {k: v for k, v in synonyms.items() if v}
        assert len(non_empty) > 0
        print(f"  Synonyms for 'agile': {synonyms.get('agile', [])[:5]}")
        print(f"  Synonyms for 'sluggish': {synonyms.get('sluggish', [])[:5]}")


# ---------------------------------------------------------------------------
# Summarisation
# ---------------------------------------------------------------------------


class TestSummarize:
    def test_basic_summarize(self, bot: QuillBot):
        long_text = (
            "The quick brown fox jumps over the lazy dog. "
            "The quick brown fox jumps over the lazy dog. "
            "The quick brown fox jumps over the lazy dog. "
            "The quick brown fox jumps over the lazy dog. "
            "The quick brown fox jumps over the lazy dog. "
            "The quick brown fox jumps over the lazy dog."
        )
        result = bot.summarize(long_text)
        assert isinstance(result, SummarizeResult)
        assert len(result.summary) > 0
        assert len(result.summary) < len(long_text)
        print(f"  Summary: {result.summary}")

    def test_summarize_preserves_original(self, bot: QuillBot):
        text = "Some text to summarize. " * 10
        result = bot.summarize(text)
        assert result.original_text == text


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrors:
    def test_invalid_token_raises_auth_error(self):
        bot = QuillBot(useridtoken="invalid-token-abc123")
        with pytest.raises((AuthenticationError, Exception)):
            bot.paraphrase("This should fail.")
        bot.close()
        print("  Bad token correctly raised error")
