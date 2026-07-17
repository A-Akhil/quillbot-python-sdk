import os
from mcp.server.fastmcp import FastMCP
from quillbot import QuillBot

# Create an MCP server instance
mcp = FastMCP("QuillBot")

_bot = None

def get_bot() -> QuillBot:
    """Lazily initialize the QuillBot client."""
    global _bot
    if _bot is None:
        email = os.environ.get("QUILLBOT_EMAIL")
        password = os.environ.get("QUILLBOT_PASSWORD")
        if not email or not password:
            raise RuntimeError(
                "Please set QUILLBOT_EMAIL and QUILLBOT_PASSWORD environment variables."
            )
        _bot = QuillBot(email, password)
    return _bot

@mcp.tool()
def paraphrase(text: str, mode: int = 0, strength: int = 2) -> str:
    """
    Paraphrase text using QuillBot.

    Args:
        text: The text to paraphrase.
        mode: The paraphrasing mode (0=Standard, 1=Fluency, 6=Shorten, 9=Formal). Default is 0.
        strength: The aggressiveness of the paraphrasing (0-10). Default is 2.
    """
    bot = get_bot()
    try:
        # Note: Free accounts may only have access to mode=0 (Standard) and mode=1 (Fluency).
        result = bot.paraphrase(text, mode=mode, strength=strength)
        return result.paraphrased_text
    except Exception as e:
        return f"Error paraphrasing text: {e}"

@mcp.tool()
def summarize(text: str) -> str:
    """
    Summarize text using QuillBot.

    Args:
        text: The long text or paragraph to summarize.
    """
    bot = get_bot()
    try:
        result = bot.summarize(text)
        return result.summary_text
    except Exception as e:
        return f"Error summarizing text: {e}"

def main():
    """Entry point for the MCP server."""
    mcp.run()

if __name__ == "__main__":
    main()
