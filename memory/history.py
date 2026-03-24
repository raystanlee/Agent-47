
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
#
# CONCEPT 2: Adding Context management.
#
# Claude has no memory between API calls — we send the full
# conversation history every time. The problem: history grows
# forever, eventually exceeding token limits and causing
# rate limit errors.
#
# The fix: when history gets too long, summarise the old
# part into a single message and keep only recent turns.
#
# Structure after trimming:
#   [system summary message]  ← compressed old history
#   [last N message pairs]    ← recent turns kept verbatim
#
# This way the agent always has context of what happened
# without sending thousands of tokens every turn.
# ─────────────────────────────────────────────────────────


import json
import anthropic
from pathlib import Path
from config import HISTORY_FILE, API_KEY

# How many recent message pairs to keep verbatim after summarising
RECENT_TURNS_TO_KEEP = 6

# Summarise when history exceeds this many messages
# (each turn = 2 messages: user + assistant)
MAX_MESSAGES_BEFORE_SUMMARY = 20


def load_history() -> list[dict]:
    """Load conversation history from disk."""
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
    """Save conversation history to disk."""
    path = Path(HISTORY_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(messages, f, indent=2, default=str)


def clear_history():
    """Wipe saved history."""
    path = Path(HISTORY_FILE)
    if path.exists():
        path.unlink()
    print("🗑️  Conversation history cleared.")


def _estimate_tokens(messages: list[dict]) -> int:
    """
    Rough token estimate — 1 token ≈ 4 characters.
    Good enough to decide when to summarise.
    """
    total = sum(len(str(m)) for m in messages)
    return total // 4


def _summarise_old_messages(messages: list[dict]) -> str:
    """
    Ask Claude to summarise old conversation turns into a
    compact paragraph. This becomes the 'memory' of what
    happened before the recent turns.
    """
    client = anthropic.Anthropic(api_key=API_KEY)

    # Format the old messages into readable text for summarisation
    text_lines = []
    for m in messages:
        role = m.get("role", "unknown")
        content = m.get("content", "")
        if isinstance(content, list):
            # Extract just the text from tool use blocks
            parts = [
                b.get("text", "") if isinstance(b, dict) else str(b)
                for b in content
                if isinstance(b, dict) and b.get("type") == "text"
            ]
            content = " ".join(parts)
        if content:
            text_lines.append(f"{role.upper()}: {content[:500]}")

    conversation_text = "\n".join(text_lines)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": (
                "Summarise this conversation history in 3-5 sentences. "
                "Focus on what tasks were completed, what files or tools were used, "
                "and any important decisions made. Be concise.\n\n"
                f"{conversation_text}"
            )
        }]
    )

    return response.content[0].text


def _is_clean_message(msg: dict) -> bool:
    """
    Returns True if a message contains only plain text — no tool_use
    or tool_result blocks. Only clean messages are safe to keep after
    trimming, since tool_use/tool_result must always come in matched
    pairs in adjacent messages.
    """
    content = msg.get("content", "")
    if isinstance(content, str):
        return True
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict):
                if block.get("type") in ("tool_use", "tool_result"):
                    return False
    return True


def trim_history(messages: list[dict]) -> list[dict]:
    """
    If history is too long, summarise the old part and keep
    only recent CLEAN turns (no tool_use/tool_result blocks).

    This prevents the 'unexpected tool_use_id' error that happens
    when tool_result blocks are kept without their matching tool_use.
    """
    if len(messages) <= MAX_MESSAGES_BEFORE_SUMMARY:
        return messages

    print(f"📝 History too long ({len(messages)} messages) — summarising...")

    # Keep only clean recent messages — filter out any tool blocks
    clean_recent = [m for m in messages if _is_clean_message(m)]
    recent_messages = clean_recent[-(RECENT_TURNS_TO_KEEP * 2):]
    old_messages = messages[:-(RECENT_TURNS_TO_KEEP * 2)]

    try:
        summary = _summarise_old_messages(old_messages)
        print(f"✅ Summarised {len(old_messages)} old messages into 1.")
    except Exception as e:
        print(f"⚠️  Could not summarise history: {e}. Trimming without summary.")
        return recent_messages

    summary_message = {
        "role": "user",
        "content": (
            f"[Previous conversation summary: {summary}]\n\n"
            "Continue from here."
        )
    }
    ack_message = {
        "role": "assistant",
        "content": "Understood. Continuing from the previous context."
    }

    trimmed = [summary_message, ack_message] + recent_messages
    save_history(trimmed)
    return trimmed