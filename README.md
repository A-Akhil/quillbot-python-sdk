# QuillBot Python SDK



A lightweight, purely HTTP-based Python SDK for interacting with the QuillBot API. 

This SDK allows you to easily integrate QuillBot's paraphrasing, translation, and summarizing capabilities into your applications, LLM agents, or command-line tools. It automatically handles token refreshing, payload formatting, and concurrent chunking of very large texts, fully mimicking the live web application.

## Features

- **Paraphrasing**: Rewrite text using QuillBot's sophisticated paraphrasing engine. Supports all premium modes including the new **AI Humanizer**.
- **Large Text Support**: Send texts of any size (even thousands of words)! The SDK will automatically chunk the text by sentences and process them concurrently, merging the results back together seamlessly.
- **Synonym Levels**: Adjust the `synonyms_level` (0-3) to control the vocabulary replacement strength, identical to the website's Synonyms slider.
- **Translation**: Translate text into over 30 languages using the integrated translation engine.
- **Bulk Thesaurus**: Automatically fetch synonym suggestions for every word/phrase in the paraphrased text in a single request.
- **Summarization**: Condense long texts into brief, readable summaries.
- **Frozen Words**: Prevent specific words or phrases from being altered during paraphrasing.
- **Pure HTTP**: No browser automation (Selenium/Playwright) required. Extremely fast and lightweight.

## Installation

This SDK requires Python 3.10+.

The package is available on PyPI. You can view the project at [https://pypi.org/project/quillbot/](https://pypi.org/project/quillbot/).

To install the latest version, simply run:

```bash
pip install quillbot
```

## Authentication

We highly recommend using email and password authentication. The SDK will automatically fetch, manage, and refresh the necessary JWT tokens in the background, keeping your session alive.

```python
import os
from quillbot import QuillBot

email = os.getenv("QUILLBOT_EMAIL")
password = os.getenv("QUILLBOT_PASSWORD")

# Initialize the client (auto-authenticates and manages tokens)
bot = QuillBot(email=email, password=password)

print(f"Logged in successfully! Premium active: {bot.is_premium}")
```

You can optionally pass a static token directly if you prefer:
```python
bot = QuillBot(useridtoken="your_static_jwt_token")
```

## Quick Start

### Paraphrasing and AI Humanizer

You can paraphrase text across multiple modes, such as `ParaphraseMode.STANDARD`, `ParaphraseMode.FLUENCY`, `ParaphraseMode.FORMAL`, or the new `ParaphraseMode.HUMANIZER`.

```python
from quillbot.endpoints import ParaphraseMode

text = "The quick brown fox jumps over the lazy dog."

# Standard Paraphrasing with Synonyms Level 2
result = bot.paraphrase(text, mode=ParaphraseMode.STANDARD, synonyms_level=2)
print(f"Paraphrased: {result.text}")

# AI Humanizer
humanized_result = bot.paraphrase(text, mode=ParaphraseMode.HUMANIZER)
print(f"Humanized: {humanized_result.text}")

# Custom Modes
custom_result = bot.paraphrase(text, mode=ParaphraseMode.CUSTOM, custom_mode_name="Shakespearean")
print(f"Custom Output: {custom_result.text}")

# View the individual phrases that were rewritten
print(f"Phrases found: {result.phrases}")
```

### Translation

You can supply the `input_lang` parameter to translate your output into one of the many supported languages.

```python
from quillbot.endpoints import Language, ParaphraseMode

english_text = "Hello world! This SDK is amazing."

# Translate to French
result = bot.paraphrase(
    english_text, 
    mode=ParaphraseMode.STANDARD, 
    input_lang=Language.FRENCH
)

print(f"French Translation: {result.text}")
```

### Interactive Editing (Synonym Suggestions)

By default, the SDK automatically fetches thesaurus data for the rewritten text. You can retrieve alternative synonyms for specific words or phrases.

```python
if result.synonyms:
    first_word = result.phrases[0]
    suggestions = result.available_replacements(first_word)
    print(f"Suggestions for '{first_word}': {suggestions}")
```

### Frozen Words

You can protect certain words or phrases from being altered.

```python
frozen_result = bot.paraphrase(
    "Python is a great programming language.",
    frozen_words=["Python", "programming"]
)
```

### Summarization

```python
long_text = (
    "Artificial intelligence (AI) is intelligence demonstrated by machines, "
    "as opposed to the natural intelligence displayed by animals including humans. "
    "Leading AI textbooks define the field as the study of intelligent agents: "
    "any system that perceives its environment and takes actions that maximize "
    "its chance of achieving its goals."
)

summary = bot.summarize(long_text)
print("Summary:", summary.summary)
```

## Running Tests

The test suite runs live integration tests against the actual QuillBot servers (as configured). Mocks are not used to ensure we accurately reflect the live API.

1. Ensure your `.env` contains a valid `QUILLBOT_EMAIL` and `QUILLBOT_PASSWORD`.
2. Run the tests:

```bash
pytest tests/test_unit.py -v -s
```

## License

This project is licensed under the GNU General Public License v3.0 (GPLv3). See the [LICENSE](LICENSE) file for details.

## Disclaimer

This is an unofficial SDK. Use responsibly and ensure you comply with QuillBot's Terms of Service.

<div align="center">

## Please support the development by donating.

[![BuyMeACoffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-ffdd00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/aakhil)

</div>