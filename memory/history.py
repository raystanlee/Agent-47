
# memory/history.py
# ─────────────────────────────────────────────────────────
# CONCEPT: Agent memory.
#
# Claude has NO memory between API calls by default.
# Every message you send must include the full conversation
# history — Claude re-reads it all each time.
#
# This file saves that history to disk so your agent
# remembers past sessions. It's the simplest form of
# long-term memory: just a JSON file of messages.
#
# More advanced systems use vector databases (like Chroma
# or Pinecone) to store and search millions of past memories.
# But for learning, JSON is perfect.
# ─────────────────────────────────────────────────────────

import json
from pathlib import Path
from config import HISTORY_FILE


def load_history() -> list[dict]:
    """Load conversation history from disk. Returns empty list if none exists."""
    path = Path(HISTORY_FILE)
    if not path.exists():
        return []
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        print("⚠️  Could not load history. Starting fresh.")
        return []


def save_history(messages: list[dict]):
    """Save the current conversation to disk."""
    path = Path(HISTORY_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(messages, f, indent=2, default=str)


def clear_history():
    """Wipe the saved history."""
    path = Path(HISTORY_FILE)
    if path.exists():
        path.unlink()
    print("🗑️  Conversation history cleared.")