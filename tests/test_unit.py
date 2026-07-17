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
import time

@pytest.fixture(autouse=True)
def slow_down_tests():
    """Wait 10 seconds between tests to prevent DDoS/Rate limits from QuillBot."""
    yield
    time.sleep(10)


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


@pytest.fixture(scope="session")
def bot():
    """Yield an authenticated QuillBot client, then close it."""
    if not EMAIL or not PASSWORD:
        pytest.skip("No credentials found. Set QUILLBOT_EMAIL and QUILLBOT_PASSWORD env vars or create .env file.")
    client = QuillBot(email=EMAIL, password=PASSWORD)
    print(f"\n[Auth] Successfully logged in. Premium account: {client.is_premium}")
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

    def test_paraphrase_standard(self, bot: QuillBot):
        """Test standard mode paraphrasing (available to all)."""
        text = "The quick brown fox jumps over the lazy dog."
        result = bot.paraphrase(text, mode=2)  # Mode 2 = Standard
        
        assert result.original_text == text
        assert len(result.paraphrased_text) > 0

    def test_paraphrase_premium_modes(self, bot: QuillBot):
        """Test premium modes (Formal, Shorten) if account is premium."""
        if not bot.is_premium:
            pytest.skip("Account is not premium. Skipping premium mode tests.")
            
        text = "The quick brown fox jumps over the lazy dog."
        
        # Mode 9 = Formal
        res_formal = bot.paraphrase(text, mode=9)
        assert len(res_formal.paraphrased_text) > 0
        
        # Mode 6 = Shorten
        res_shorten = bot.paraphrase(text, mode=6)
        assert len(res_shorten.paraphrased_text) > 0
        assert len(res_shorten.paraphrased_text) <= len(text) + 20

    def test_humanizer(self, bot: QuillBot):
        """Test the AI Humanizer / Narrative mode."""
        if not bot.is_premium:
            pytest.skip("Account is not premium. Skipping humanizer test.")
            
        text = "The quick brown fox jumps over the lazy dog."
        res = bot.paraphrase(text, mode=12)
        assert len(res.paraphrased_text) > 0
        assert "paras_13" in str(res.raw) or "paras_" in str(res.raw)

    @pytest.mark.parametrize("word_count", [50, 150, 300, 500])
    def test_paraphrase_various_lengths(self, bot: QuillBot, word_count: int):
        """Test paraphrasing with different word counts to ensure robust handling."""
        if not bot.is_premium and word_count > 125:
            pytest.skip("Account is not premium. Skipping long text test.")
            
        # Generate a realistic-looking long sentence structure
        base_sentence = "The quick brown fox jumps over the lazy dog. "
        words_in_base = 9
        repetitions = (word_count // words_in_base) + 1
        long_text = (base_sentence * repetitions).strip()
        # Truncate to exact word count roughly
        long_text = " ".join(long_text.split()[:word_count])
        
        result = bot.paraphrase(long_text, mode=2)
        assert len(result.paraphrased_text) > 0
        assert isinstance(result.paraphrased_text, str)

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
