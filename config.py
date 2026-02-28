
# config.py
# ─────────────────────────────────────────────────────────
# Central place for all settings.
# Good practice: never scatter config values across files.
# ─────────────────────────────────────────────────────────

import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

# ── Model ──────────────────────────────────────────────
MODEL = "claude-opus-4-6"
MAX_TOKENS = 1024          # Max tokens Claude can reply with per turn

# ── The folder the agent is allowed to touch ────────────
# Change this to any folder on your Mac.
# The agent CANNOT access anything outside this folder.
SAFE_ROOT = Path.home() / "AgentWorkspace"

# ── API Key ─────────────────────────────────────────────
# Loaded from your environment — never hardcode secrets in code.
# Run: export ANTHROPIC_API_KEY="sk-ant-..."
API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# ── Memory ──────────────────────────────────────────────
# The agent saves conversation history here so it remembers between sessions.
HISTORY_FILE = Path("memory/history.json")

# ── System Prompt ────────────────────────────────────────
# This is the "personality" and rules given to Claude at the start.
# Think of it as the agent's job description.
SYSTEM_PROMPT = f"""You are a file management assistant for a Mac.
You can only access the workspace folder: {SAFE_ROOT}

Rules:
- Always list a folder before deleting its contents unless the user is explicit.
- Tell the user what you did after each action clearly.
- If an operation would be destructive, confirm what you are about to do first.
- Be concise and clear. No unnecessary filler.
"""