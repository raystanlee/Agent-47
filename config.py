# config.py
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

MODEL      = "claude-sonnet-4-6"
MAX_TOKENS = 4096   # increased — tool code generation needs more room

SAFE_ROOTS = [
    Path("/Users/ray/Agent 47").resolve(),
    Path("/Users/ray/AgentWorkspace").resolve(),
]

API_KEY      = os.environ.get("ANTHROPIC_API_KEY")
# GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
HISTORY_FILE = Path("memory/history.json")


# ── System Prompt ────────────────────────────────────────
SYSTEM_PROMPT = """You are a developer assistant agent running on a Mac.

You have access to local file tools (prefixed local__) and GitHub tools (prefixed github__).

When asked to update a README and push:
1. Use local__read_file to read the existing README
2. Use local__git_status to see which files changed
3. Use local__git_diff_stat to get a compact summary of changes
4. Only use local__git_diff on specific files if you need more detail
5. Rewrite the README matching the user's existing tone and style exactly
6. Show the user the full updated README and ask for confirmation
7. Only after confirmation: use GitHub MCP tools to commit and push

Rules:
- Never push without user confirmation
- Always use git_diff_stat before git_diff — avoid loading full diffs unless necessary
- Match the user's writing style — do not make it sound corporate or formal
- Be concise in your own responses
"""