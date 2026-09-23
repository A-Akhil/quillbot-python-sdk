"""Offline checks that every MCP tool, argument and prompt is documented in `quillbot --help` and the tool schemas."""

import asyncio
from pathlib import Path

from quillbot import server

HELP = (Path(server.__file__).parent / "mcp_resources" / "cli_help.txt").read_text(encoding="utf-8")


def test_help_documents_every_tool_and_argument():
    for tool in asyncio.run(server.mcp.list_tools()):
        assert tool.name in HELP, f"tool {tool.name} missing from cli_help.txt"
        for arg in tool.inputSchema.get("properties", {}):
            assert f"{arg}:" in HELP, f"argument {tool.name}.{arg} missing from cli_help.txt"


def test_every_tool_argument_has_schema_description():
    for tool in asyncio.run(server.mcp.list_tools()):
        for arg, schema in tool.inputSchema.get("properties", {}).items():
            assert schema.get("description"), f"argument {tool.name}.{arg} has no description in the MCP schema"


def test_help_documents_every_prompt():
    for prompt in asyncio.run(server.mcp.list_prompts()):
        assert prompt.name in HELP, f"prompt {prompt.name} missing from cli_help.txt"
