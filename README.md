# QuillBot Python SDK

A lightweight, purely HTTP-based Python SDK for interacting with the QuillBot API.
This SDK allows you to easily integrate QuillBot's paraphrasing and summarizing capabilities into your applications, LLM agents, or command-line tools.

## Features

- **Paraphrasing**: Rewrite text using QuillBot's sophisticated paraphrasing engine.
- **Bulk Thesaurus**: Automatically fetch synonym suggestions for every word/phrase in the paraphrased text in a single request.
- **Summarization**: Condense long texts into brief, readable summaries.
- **Frozen Words**: Prevent specific words or phrases from being altered during paraphrasing.
- **Pure HTTP**: No browser automation (Selenium/Playwright) required. Fast and lightweight.

## Installation

This SDK requires Python 3.10+.

Clone the repository and install the dependencies (we recommend using a virtual environment):

```bash
# Example for installing with pip
pip install -r requirements.txt
```

If you are using `pytest` for running tests, install it using:
```bash
pip install pytest httpx --break-system-packages
```
*(Note: `--break-system-packages` may be required on some modern Linux distributions if you are not using a virtual environment.)*

## Authentication

To use the SDK, you need a valid QuillBot `useridtoken`. 
You can obtain this token by logging into QuillBot in your web browser, opening Developer Tools, and inspecting the cookies or request headers for `useridtoken`.

Create a `.env` file in the root directory and add your token:

```env
QUILLBOT_USERIDTOKEN=your_actual_token_here
```

## Quick Start

### Paraphrasing

```python
from quillbot import QuillBot
import os

# Initialize the client with your token
token = os.getenv("QUILLBOT_USERIDTOKEN")
bot = QuillBot(token)

# Basic Paraphrasing
text = "The quick brown fox jumps over the lazy dog."
result = bot.paraphrase(text, strength=9)

print(f"Original: {result.original_text}")
print(f"Paraphrased: {result.text}")
print(f"Phrases found: {result.phrases}")

# Accessing Synonym Suggestions (Interactive Editing)
if result.synonyms:
    first_word = result.phrases[0]
    suggestions = result.available_replacements(first_word)
    print(f"Suggestions for '{first_word}': {suggestions}")

# Paraphrasing with Frozen Words
frozen_result = bot.paraphrase(
    "Python is a great programming language.",
    frozen_words=["Python"]
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
print("Summary:", summary)
```

## Core Architecture

The SDK is intentionally designed to be thin and close to the QuillBot API. 
QuillBot already provides the heavily optimized NLP features (synonym suggestions, phrase grouping, grammar context). The SDK exposes these capabilities rather than reinventing a local document engine.

- The application (your script) is responsible for decision-making (e.g., deciding which word to replace with which synonym).
- The SDK purely provides the data (rewritten text and synonym maps).

## Running Tests

The test suite runs live integration tests against the actual QuillBot servers (as configured). Mocks are not used to ensure we accurately reflect the live API.

1. Ensure your `.env` contains a valid `QUILLBOT_USERIDTOKEN`.
2. Run the tests:

```bash
pytest tests/test_unit.py -v -s
```

## Disclaimer

This is an unofficial SDK. Use responsibly and ensure you comply with QuillBot's Terms of Service.
