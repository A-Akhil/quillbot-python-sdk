import os
import json
import difflib
import secrets
import re
import platformdirs
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from mcp.server.fastmcp import FastMCP
from quillbot import QuillBot
from quillbot.endpoints import ParaphraseMode, Language
import logging

# Set up file logging so you can monitor what happens behind the scenes
logging.basicConfig(
    filename='quillbot_mcp.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("quillbot_mcp")

# Initialize the FastMCP Server
mcp = FastMCP("QuillBot")

_bot: Optional[QuillBot] = None

def get_bot() -> QuillBot:
    """Lazily initialize the QuillBot client."""
    global _bot
    if _bot is None:
        logger.info("Initializing QuillBot client...")
        email = os.environ.get("QUILLBOT_EMAIL")
        password = os.environ.get("QUILLBOT_PASSWORD")
        if not email or not password:
            logger.error("QUILLBOT_EMAIL and QUILLBOT_PASSWORD environment variables are not set.")
            raise RuntimeError(
                "Please set QUILLBOT_EMAIL and QUILLBOT_PASSWORD environment variables."
            )
        _bot = QuillBot(email=email, password=password)
        logger.info("QuillBot client initialized successfully.")
    return _bot

# ---------------------------------------------------------------------------
# State Management
# ---------------------------------------------------------------------------

@dataclass
class DocumentSession:
    task_id: str
    original_text: str
    current_text: str
    mode: str
    language: str
    phrases: List[str]
    synonyms: Dict[str, List[str]]
    history: List[str] = field(default_factory=list)
    replaced_words_count: int = 0

CACHE_DIR = Path(platformdirs.user_cache_dir("quillbot_mcp"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)
logger.info(f"Cache directory initialized at: {CACHE_DIR}")

def _save_session(session: DocumentSession) -> None:
    path = CACHE_DIR / f"{session.task_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(asdict(session), f, ensure_ascii=False, indent=2)
    logger.debug(f"Saved session to disk: {session.task_id}")

def _get_session(task_id: str) -> DocumentSession:
    path = CACHE_DIR / f"{task_id}.json"
    if not path.exists():
        logger.error(f"Failed to fetch session. Task ID not found: {task_id}")
        raise ValueError(f"Task ID '{task_id}' not found.")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return DocumentSession(**data)

def _delete_session(task_id: str) -> bool:
    path = CACHE_DIR / f"{task_id}.json"
    if path.exists():
        path.unlink()
        logger.info(f"Deleted session: {task_id}")
        return True
    logger.warning(f"Attempted to delete non-existent session: {task_id}")
    return False

def _list_sessions() -> List[str]:
    return [p.stem for p in CACHE_DIR.glob("*.json")]

def _minify(data: Any) -> str:
    """Helper to return highly optimized, single-line JSON to the LLM."""
    return json.dumps(data, separators=(',', ':'))

# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def paraphrase_text(
    text: str,
    mode_name: str = "STANDARD",
    synonyms_level: int = 2,
    custom_mode_name: Optional[str] = None,
    frozen_words: Optional[List[str]] = None,
    input_lang: str = "ENGLISH"
) -> str:
    """
    Initialize a new document session by paraphrasing text. This is the entry point.
    Returns a JSON string containing task_id and the initial paraphrased text. Use this task_id for all subsequent operations.
    """
    logger.info(f"paraphrase_text called. Mode: {mode_name}, Length: {len(text)} chars.")
    bot = get_bot()
    
    try:
        mode_attr = mode_name.upper()
        if not hasattr(ParaphraseMode, mode_attr):
            logger.error(f"Invalid mode_name requested: {mode_name}")
            return _minify({"error": f"Invalid mode_name: {mode_name}"})
        mode_val = getattr(ParaphraseMode, mode_attr)

        lang_attr = input_lang.upper().replace("-", "_")
        lang_val = Language.ENGLISH
        if hasattr(Language, lang_attr):
            lang_val = getattr(Language, lang_attr)

        logger.info("Sending network request to QuillBot API...")
        result = bot.paraphrase(
            text,
            mode=mode_val,
            synonyms_level=synonyms_level,
            frozen_words=frozen_words,
            input_lang=lang_val
        )

        # Use a short, 8-character hex token for cleaner task IDs
        task_id = secrets.token_hex(4)
        session = DocumentSession(
            task_id=task_id,
            original_text=result.original_text,
            current_text=result.paraphrased_text,
            mode=mode_name,
            language=input_lang,
            phrases=result.phrases,
            synonyms=result.synonyms,
        )
        _save_session(session)

        logger.info(f"Successfully generated new task_id: {task_id}")
        return _minify({
            "task_id": task_id,
            "text": session.current_text
        })
    except Exception as e:
        logger.error(f"Error in paraphrase_text: {str(e)}", exc_info=True)
        return _minify({"error": str(e)})

@mcp.tool()
def paraphrase_and_diversify(
    text: str,
    mode_name: str = "STANDARD",
    iterations: int = 1,
    protected_terms: Optional[List[str]] = None
) -> str:
    """
    Macro tool that performs deep, recursive paraphrasing. 
    It loops the text through Quillbot 'iterations' times while strictly protecting 'protected_terms'.
    Returns the final text, the longest unchanged string (for potential manual synonym swapping), 
    and a word-level unified diff to visualize structural changes.
    """
    logger.info(f"paraphrase_and_diversify called. Mode: {mode_name}, Iterations: {iterations}")
    bot = get_bot()
    try:
        mode_attr = mode_name.upper()
        if not hasattr(ParaphraseMode, mode_attr):
            return _minify({"error": f"Invalid mode_name: {mode_name}"})
        mode_val = getattr(ParaphraseMode, mode_attr)
        
        current_text = text
        last_result = None
        
        # Deep recursive looping
        for i in range(max(1, iterations)):
            logger.info(f"Diversify Loop {i+1}/{iterations}...")
            last_result = bot.paraphrase(current_text, mode=mode_val, synonyms_level=2, frozen_words=protected_terms)
            current_text = last_result.paraphrased_text
            
        if not last_result:
            return _minify({"error": "Failed to paraphrase text."})
            
        from .diff_legend import process_legend
        
        # We need to process each sentence if it's multi-sentence, but text might be just one paragraph.
        # The Quillbot algorithm expects words split by space.
        para_words = [{"word": w} for w in current_text.split(" ")]
        
        # Apply the 3 legend algorithms
        para_words = process_legend(text, para_words)
        
        # Reconstruct the unified diff but now with legend flags!
        # Instead of just ndiff, we can use the flags directly.
        annotated_words = []
        for w in para_words:
            word_str = w["word"]
            flags = []
            if w.get("is_changed_word"):
                flags.append("changed")
            if w.get("is_structural_change"):
                flags.append("structural")
            if w.get("in_longest_substring"):
                flags.append("longest_unchanged")
            
            if flags:
                flag_str = ",".join(flags)
                annotated_words.append(f"[{word_str}]({flag_str})")
            else:
                annotated_words.append(word_str)
                
        unified_diff_str = " ".join(annotated_words)
        
        # Find longest unchanged words string for the return object
        longest_unchanged_list = [w["word"] for w in para_words if w.get("in_longest_substring")]
        unchanged_string = " ".join(longest_unchanged_list)
        
        logger.info(f"Diversify complete.")
        return _minify({
            "final_text": current_text,
            "longest_unchanged_words_found": unchanged_string,
            "legend_annotated_text": unified_diff_str,
            "word_stats": para_words
        })
    except Exception as e:
        logger.error(f"Error in paraphrase_and_diversify: {str(e)}", exc_info=True)
        return _minify({"error": str(e)})

@mcp.tool()
def summarize_text(text: str) -> str:
    """
    Condense long texts into brief, readable summaries. Does not create a document session.
    """
    logger.info(f"summarize_text called. Length: {len(text)} chars.")
    bot = get_bot()
    try:
        result = bot.summarize(text)
        logger.info("Summary generated successfully.")
        return _minify({"summary": result.summary})
    except Exception as e:
        logger.error(f"Error in summarize_text: {str(e)}", exc_info=True)
        return _minify({"error": str(e)})

@mcp.tool()
def list_replaceable_phrases(
    task_id: str,
    target_string: Optional[str] = None,
    max_suggestions: int = 3
) -> str:
    """
    Returns a JSON string listing phrases in the document that can be interactively replaced with synonyms.
    If target_string is provided, it only returns phrases that exist within that specific substring.
    Includes the inline text of the top 'max_suggestions' to prevent blind guessing.
    """
    logger.info(f"list_replaceable_phrases called for task_id: {task_id}")
    try:
        session = _get_session(task_id)
        results = []
        
        # Determine the target search scope
        search_text = session.current_text
        if target_string and target_string in search_text:
            search_text = target_string
            
        for idx, phrase in enumerate(session.phrases):
            # Only include the phrase if it exists in the search_text
            if phrase not in search_text:
                continue
                
            suggs = session.synonyms.get(phrase, [])
            if suggs:
                top_suggs = [{"suggestion_index": i, "text": sug} for i, sug in enumerate(suggs[:max_suggestions])]
                results.append({
                    "phrase_index": idx,
                    "current_phrase": phrase,
                    "suggestion_count": len(suggs),
                    "top_suggestions": top_suggs
                })
        logger.info(f"Found {len(results)} replaceable phrases for task_id: {task_id}")
        return _minify({"phrases": results})
    except Exception as e:
        logger.error(f"Error in list_replaceable_phrases: {str(e)}")
        return _minify({"error": str(e)})

@mcp.tool()
def get_suggestions(task_id: str, phrase_index: int) -> str:
    """
    Fetch the context-aware synonym suggestions available for a specific phrase index in the document session.
    """
    logger.info(f"get_suggestions called for task_id: {task_id}, index: {phrase_index}")
    try:
        session = _get_session(task_id)
        if phrase_index < 0 or phrase_index >= len(session.phrases):
            logger.warning(f"phrase_index {phrase_index} out of bounds.")
            return _minify({"error": "phrase_index out of bounds."})
        
        phrase = session.phrases[phrase_index]
        suggestions = session.synonyms.get(phrase, [])
        logger.info(f"Returning {len(suggestions)} suggestions for phrase: '{phrase}'")
        return _minify({
            "current_phrase": phrase,
            "suggestions": [
                {"suggestion_index": i, "text": sug} for i, sug in enumerate(suggestions)
            ]
        })
    except Exception as e:
        logger.error(f"Error in get_suggestions: {str(e)}")
        return _minify({"error": str(e)})

def _apply_replacement(session: DocumentSession, phrase_index: int, suggestion_index: int) -> str:
    """Internal helper to safely apply a replacement (does not save)."""
    if phrase_index < 0 or phrase_index >= len(session.phrases):
        raise ValueError("phrase_index out of bounds.")
    
    old_phrase = session.phrases[phrase_index]
    suggestions = session.synonyms.get(old_phrase, [])
    
    if suggestion_index < 0 or suggestion_index >= len(suggestions):
        raise ValueError("suggestion_index out of bounds.")
        
    new_phrase = suggestions[suggestion_index]
    logger.info(f"Replacing phrase '{old_phrase}' with '{new_phrase}' (index {phrase_index})")
    
    if old_phrase in session.current_text:
        pattern = r'(?<![a-zA-Z0-9])' + re.escape(old_phrase) + r'(?![a-zA-Z0-9])'
        if re.search(pattern, session.current_text):
            session.current_text = re.sub(pattern, new_phrase, session.current_text, count=1)
        else:
            session.current_text = session.current_text.replace(old_phrase, new_phrase, 1)
        
        session.replaced_words_count += 1
        session.phrases[phrase_index] = new_phrase
        session.synonyms[new_phrase] = session.synonyms.get(old_phrase, [])
    
    return session.current_text

@mcp.tool()
def replace_synonym(task_id: str, phrase_index: int, suggestion_index: int) -> str:
    """
    Replace a specific occurrence in the cached document with one of QuillBot's available suggestions. Returns the updated text in a JSON string.
    """
    logger.info(f"replace_synonym called for task_id: {task_id}, phrase: {phrase_index}, suggestion: {suggestion_index}")
    try:
        session = _get_session(task_id)
        session.history.append(session.current_text)
        new_text = _apply_replacement(session, phrase_index, suggestion_index)
        _save_session(session)
        logger.info("Replacement applied and session saved successfully.")
        return _minify({"text": new_text})
    except Exception as e:
        logger.error(f"Error in replace_synonym: {str(e)}")
        return _minify({"error": str(e)})

@mcp.tool()
def replace_many(task_id: str, replacements: List[Dict[str, int]]) -> str:
    """
    Apply multiple synonym replacements in a single batch operation. Returns the updated text in a JSON string.
    Expects a list of dicts: [{"phrase_index": 0, "suggestion_index": 1}, ...]
    """
    logger.info(f"replace_many called for task_id: {task_id} with {len(replacements)} replacements.")
    try:
        session = _get_session(task_id)
        session.history.append(session.current_text)
        
        for rep in replacements:
            p_idx = rep.get("phrase_index")
            s_idx = rep.get("suggestion_index")
            if p_idx is not None and s_idx is not None:
                _apply_replacement(session, p_idx, s_idx)
                
        _save_session(session)
        logger.info("Batch replacements applied successfully.")
        return _minify({"text": session.current_text})
    except Exception as e:
        logger.error(f"Error in replace_many: {str(e)}")
        return _minify({"error": str(e)})

@mcp.tool()
def refresh_phrase(task_id: str, phrase_index: int) -> str:
    """
    Make a network request to QuillBot to fetch or refresh context-aware synonym suggestions for a specific phrase. Returns JSON string of suggestions.
    """
    logger.info(f"refresh_phrase called for task_id: {task_id}, index: {phrase_index}")
    try:
        session = _get_session(task_id)
        if phrase_index < 0 or phrase_index >= len(session.phrases):
            return _minify({"error": "phrase_index out of bounds."})
            
        phrase = session.phrases[phrase_index]
        bot = get_bot()
        
        mode_val = getattr(ParaphraseMode, session.mode.upper(), ParaphraseMode.STANDARD)
        
        logger.info(f"Fetching fresh thesaurus data for phrase '{phrase}'...")
        new_syns = bot._fetch_thesaurus(session.current_text, [phrase], mode=mode_val)
        session.synonyms.update(new_syns)
        
        _save_session(session)
        logger.info("Thesaurus successfully refreshed.")
        return get_suggestions(task_id, phrase_index)
    except Exception as e:
        logger.error(f"Error in refresh_phrase: {str(e)}")
        return _minify({"error": str(e)})

@mcp.tool()
def get_document(task_id: str) -> str:
    """
    Retrieve the current full state of the document session, including the text, available phrases, active mode, and language.
    """
    logger.info(f"get_document called for task_id: {task_id}")
    try:
        session = _get_session(task_id)
        return _minify({
            "text": session.current_text,
            "mode": session.mode,
            "language": session.language,
            "available_phrase_count": len([p for p in session.phrases if session.synonyms.get(p)])
        })
    except Exception as e:
        logger.error(f"Error in get_document: {str(e)}")
        return _minify({"error": str(e)})

@mcp.tool()
def undo(task_id: str) -> str:
    """
    Undo the last synonym replacement operation, reverting the document to its previous state.
    """
    logger.info(f"undo called for task_id: {task_id}")
    try:
        session = _get_session(task_id)
        if not session.history:
            logger.warning("Undo attempted but history is empty.")
            return _minify({"error": "No history to undo."})
            
        session.current_text = session.history.pop()
        _save_session(session)
        logger.info("Undo successful.")
        return _minify({"text": session.current_text})
    except Exception as e:
        logger.error(f"Error in undo: {str(e)}")
        return _minify({"error": str(e)})

@mcp.tool()
def reset(task_id: str) -> str:
    """
    Completely reset the document session back to the original paraphrased text, discarding all interactive edits.
    """
    logger.info(f"reset called for task_id: {task_id}")
    try:
        session = _get_session(task_id)
        if not session.history:
            return _minify({"text": session.current_text})
            
        initial_text = session.history[0]
        session.current_text = initial_text
        session.history.clear()
        session.replaced_words_count = 0
        _save_session(session)
        logger.info("Session reset back to initial state.")
        return _minify({"text": session.current_text})
    except Exception as e:
        logger.error(f"Error in reset: {str(e)}")
        return _minify({"error": str(e)})

@mcp.tool()
def stats(task_id: str) -> str:
    """
    Retrieve analytical statistics about the document session. This includes QuillBot's specific text analysis metrics to help the LLM decide what to edit.
    """
    logger.info(f"stats called for task_id: {task_id}")
    try:
        session = _get_session(task_id)
        
        matcher = difflib.SequenceMatcher(None, session.original_text.split(), session.current_text.split())
        changed_words = []
        longest_unchanged = []
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'replace' or tag == 'insert':
                changed_words.extend(session.current_text.split()[j1:j2])
            elif tag == 'equal':
                match_words = session.original_text.split()[i1:i2]
                if len(match_words) > len(longest_unchanged):
                    longest_unchanged = match_words
                    
        structural_changes = len(session.original_text.split('.')) != len(session.current_text.split('.'))
        thesaurus_available = any(session.synonyms.values())
        
        logger.info("Stats calculated successfully.")
        return _minify({
            "changed_words": changed_words,
            "structural_changes": structural_changes,
            "longest_unchanged_words": " ".join(longest_unchanged),
            "thesaurus_available": thesaurus_available,
            "replaced_words_count": session.replaced_words_count,
            "mode": session.mode,
            "language": session.language,
            "word_count": len(session.current_text.split()),
            "character_count": len(session.current_text)
        })
    except Exception as e:
        logger.error(f"Error in stats: {str(e)}")
        return _minify({"error": str(e)})

@mcp.tool()
def export(task_id: str) -> str:
    """
    Export the final document session state, returning the current text, original text, and metadata.
    """
    logger.info(f"export called for task_id: {task_id}")
    try:
        session = _get_session(task_id)
        return _minify({
            "original_text": session.original_text,
            "final_text": session.current_text,
            "mode": session.mode,
            "language": session.language,
            "edits_made": session.replaced_words_count
        })
    except Exception as e:
        logger.error(f"Error in export: {str(e)}")
        return _minify({"error": str(e)})

@mcp.tool()
def delete_task(task_id: str) -> str:
    """
    Explicitly delete a document session from the cache to free up memory.
    """
    logger.info(f"delete_task called for task_id: {task_id}")
    return _minify({"success": _delete_session(task_id)})

@mcp.tool()
def list_tasks() -> str:
    """
    List all active document sessions (task IDs) currently residing in memory.
    """
    logger.info("list_tasks called.")
    return _minify({"active_tasks": _list_sessions()})

@mcp.tool()
def list_options() -> str:
    """
    Helper tool to list the available Modes and Languages for use with paraphrase_text.
    """
    logger.info("list_options called.")
    modes = list(ParaphraseMode.__members__.keys())
    languages = list(Language.__members__.keys())
    return _minify({
        "modes": modes,
        "languages": languages
    })

def main():
    """Entry point for the MCP server."""
    logger.info("Starting QuillBot MCP Server...")
    mcp.run()

if __name__ == "__main__":
    main()
