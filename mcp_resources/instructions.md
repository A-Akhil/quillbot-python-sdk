# QuillBot MCP: Advanced Document Editing Skill & Agentic Framework

## 0. Quick Start Workflow
> **IMPORTANT**: If this is your first time using this server, read the file `START_HERE_AGENT_WORKFLOW.json` located in the MCP server directory. It provides a complete, step-by-step example of how to initialize a document, read the stats, find synonyms, and apply edits.

---

## 1. Core Purpose and Capabilities
This MCP server integrates QuillBot's advanced AI paraphrasing, humanizing, and summarizing engines directly into your agentic context. Your primary objective when utilizing this server is to assist the user in rewriting, refining, or summarizing text while maintaining absolute, granular control over tone, fluency, and structural variety.

Unlike a standard stateless LLM prompt where text is generated and forgotten, this server features a **highly stateful and persistent paraphrasing engine**. Every document you paraphrase is cached to the local disk and assigned a unique 8-character hex `task_id`. This architecture empowers you to interactively edit specific words, retrieve analytical diff statistics, undo mistakes chronologically, and iteratively perfect a document over an extended period without making expensive or redundant network requests. You are effectively acting as a highly sophisticated, deterministic copyeditor.

---

## 2. Stateless Summarization
**Tool:** `summarize_text`

If the user simply wants to condense a long piece of text into a brief summary, **do not** use `paraphrase_text`. Use `summarize_text`. 
- **Action:** Pass the raw `text` to this tool.
- **Constraint:** This tool is entirely **stateless**. It does not generate a `task_id`, and it does not allow for interactive synonym replacement. Do not attempt to call interactive tools on a summarized output.

**Example Usage:**
```json
// Tool Call
summarize_text(text="Artificial intelligence is the simulation of human intelligence processes by machines, especially computer systems. These processes include learning, reasoning, and self-correction.")

// Tool Response
{"summary":"AI is the simulation of human intelligence by machines, including learning, reasoning, and self-correction."}
```

---

## 3. High-Level Macro Automation (Deep Rewriting)
**Tool:** `paraphrase_and_diversify`

If the user explicitly requests you to heavily rewrite a text to bypass AI detectors or maximize diversity, you should use this macro tool instead of doing it manually step-by-step.
- **Action:** Pass the `text`, `mode_name`, `iterations` (default 1), and a list of `protected_terms` (e.g., `["YOLOv8", "\cite"]`).
- **How it works:** It paraphrases the text recursively `n` times to shatter the original structure, while passing the `protected_terms` securely to Quillbot's backend so they are never altered.
- **Constraint:** This tool automatically caches the result and returns a `task_id`. It also returns the `longest_unchanged_options`. You can immediately pipe this `task_id` and the options into the `replace_many` tool to programmatically apply synonyms in one shot.

**Example Usage (Piping into replace_many):**
```json
// 1. Tool Call: Macro Rewrite
paraphrase_and_diversify(text="The quick brown fox jumps.", mode_name="HUMANIZER", iterations=2, protected_terms=["fox"])

// 1. Tool Response
{
  "task_id": "c1bd9760",
  "final_text": "The swift auburn fox leaps.",
  "longest_unchanged_words_found": "fox leaps",
  "longest_unchanged_options": [
    {
      "phrase_index": 3,
      "current_phrase": "leaps",
      "top_suggestions": [{"suggestion_index": 0, "text": "plunges"}]
    }
  ]
}

// 2. Immediate Follow-up Tool Call: Apply the suggestion directly!
replace_many(task_id="c1bd9760", replacements=[{"phrase_index": 3, "suggestion_index": 0}])
```

---

## 4. Initialization and Paraphrasing Modes
**Tool:** `paraphrase_text`

If the user wants to rewrite text while maintaining your ability to perform surgical edits, initiate a session via `paraphrase_text`.

**Critical Parameters:**
- `mode_name` (string): The stylistic mode.
  - `STANDARD`: Balances altering the text with maintaining the original semantic meaning. Use this as the default fallback.
  - `FLUENCY`: Focuses strictly on fixing grammatical errors and enhancing natural readability. Ideal for cleaning up messy, translated, or human-drafted text.
  - `FORMAL`: Sophisticated, professional, and objective. Mandatory for business communications, official emails, or academic text.
  - `ACADEMIC`: Highly scholarly, prioritizing complex vocabulary, strict tone, and academic phrasing conventions.
  - `HUMANIZER`: Specifically rewrites text to bypass AI detectors and sound as naturally human-like as possible.
  - `SIMPLE`: Makes text highly accessible, stripping away jargon to make it easy to read for general audiences.
  - `CREATIVE`: Introduces entirely new phrasing, idioms, and structural concepts. WARNING: Use with caution as it can fundamentally alter the original meaning.
  - `EXPAND`: Artificially increases word count by adding descriptive adjectives and fleshing out clauses.
  - `SHORTEN`: Aggressively trims filler words and condenses clauses to reduce overall length.
- `input_lang` (string): The language of the text (e.g., `ENGLISH`, `SPANISH`, `FRENCH`). Must match the input text natively.
- `synonyms_level` (int, 1-3): Defaults to 2. Level 1 changes few words; Level 3 is highly aggressive.
- `frozen_words` (list of strings): Use this proactively to protect specific nouns or entities (e.g. `["Google", "Antigravity SDK"]`).
- `include_stats` (bool): Defaults to `true`. Outputs `longest_unchanged_words_found` and `longest_unchanged_options` to give immediate insight.

**Example Usage:**
```json
// Tool Call
paraphrase_text(text="The quick brown fox jumps over the lazy dog.", mode_name="FORMAL", synonyms_level=2, frozen_words=["fox"], include_stats=true)

// Tool Response
{"task_id":"433b1eae","text":"The swift brown fox leaps over the lethargic dog.", "longest_unchanged_words_found":"brown fox over the dog.", "longest_unchanged_options": [...]}
```
**CRITICAL:** You must retain the `task_id` (`"433b1eae"`) in your internal reasoning; all subsequent tools strictly require it.

---

## 5. Interactive Synonym Workflow (Deep Dive)
Once a document is initialized via `paraphrase_text`, your role shifts to a meticulous editor. You must scan the text and swap specific words.

1. **Map the Document State:**
   **Tool:** `list_replaceable_phrases`
   - **Action:** Call this to see which phrases can be edited.
   - **Targeting (Important):** Use the `target_string` filter to limit results to a specific sentence (e.g., the `longest_unchanged_words_found` from `stats`) so you don't get overwhelmed by a 500-word document.
   **Example Response:**
   ```json
   {"phrases":[{"phrase_index":0,"current_phrase":"swift","suggestion_count":4,"top_suggestions":[{"suggestion_index":0,"text":"rapid"},{"suggestion_index":1,"text":"agile"}]}]}
   ```

2. **Explore Context-Aware Alternatives (Fallback):**
   **Tool:** `get_suggestions`
   - **Action:** If the `top_suggestions` in the list above aren't enough, you can request the full array of synonyms for a specific phrase index.

3. **Execute the Edit:**
   **Tool:** `replace_synonym`
   - **Action:** Apply the chosen synonym.
   **Example Usage:**
   ```json
   // Tool Call
   replace_synonym(task_id="433b1eae", phrase_index=0, suggestion_index=1)
   
   // Tool Response
   {"text":"The agile brown fox leaps over the lethargic dog."}
   ```

4. **Batch Processing for Efficiency:**
   **Tool:** `replace_many`
   - **Action:** If changing 5 words, do it in one atomic transaction to save token bandwidth.
   **Example Usage:**
   ```json
   // Tool Call
   replace_many(task_id="433b1eae", replacements=[{"phrase_index":0,"suggestion_index":1},{"phrase_index":3,"suggestion_index":0}])
   ```

---

## 6. Analytical Evaluation & Quality Control
Before presenting final text to the user, evaluate if the text meets the user's criteria.

**Tool:** `stats`
- **Agentic Action (Plagiarism):** If `longest_unchanged_words_found` is longer than 8 words, the paraphrase is too similar to the original input. You must actively remediate this by calling `list_replaceable_phrases(target_string="...")` on that exact string and applying synonyms to break it up.
- **Agentic Action (Structural):** If the user requested a "deep rewrite" but `structural_changes` is `false`, you failed. Switch to `CREATIVE` or `HUMANIZER` mode and try again, or use the `paraphrase_and_diversify` macro.

**Example Usage & Response:**
```json
// Tool Call
stats(task_id="433b1eae")

// Tool Response
{"changed_words":["swift","leaps","lethargic"],"structural_changes":false,"longest_unchanged_words_found":"brown fox over the dog.", "longest_unchanged_options": [...], "replaced_words_count":2,"mode":"FORMAL","language":"ENGLISH","word_count":9}
```

---

## 7. State Recovery, History, and Network Logic

- **Re-Orienting Context (`get_document`):** 
  If your context window truncates and you lose track of the text, **never** hallucinate. Explicitly call `get_document(task_id)` to fetch the exact, true state of the text currently residing in the cache.
  ```json
  {"text":"The agile brown fox leaps...","mode":"FORMAL","language":"ENGLISH","available_phrase_count":5}
  ```
- **Chronological Reversion (`undo`):** 
  If you apply a bad synonym that ruins the grammatical flow, do not attempt to manually fix it. Call `undo(task_id)` to revert the document to the exact character state before your last edit.
- **Nuclear Reset (`reset`):** 
  Call `reset(task_id)` to wipe all manual edits and restore the text to the pristine state of the initial paraphrase.
- **Network Forcing (`refresh_phrase`):** 
  If cached suggestions do not fit the semantic requirements, call `refresh_phrase(task_id, phrase_index)`. This forces a secure HTTPS network request to QuillBot's deep backend to fetch brand new alternatives.

---

## 8. Lifecycle Management and Discovery

- **Enum Discovery (`list_options`):**
  If unsure about the precise casing of a language (e.g., `ENGLISH_UK` vs `ENGLISH_GB`) or mode, call `list_options()`. Do not hallucinate strings.
  ```json
  {"modes":["FLUENCY","STANDARD","CREATIVE","HUMANIZER"],"languages":["ENGLISH","FRENCH","SPANISH"]}
  ```
- **Exporting (`export`):** 
  When the user is completely satisfied, call `export(task_id)` and present the payload cleanly to the user.
- **Garbage Collection (`delete_task`):** 
  To prevent disk bloat, you **must** proactively call `delete_task(task_id)` once a workflow is finalized.
- **Auditing (`list_tasks`):**
  If you lose track of your `task_id` entirely, call `list_tasks()` to retrieve all active task IDs on the disk.
