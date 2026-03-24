# telegram_bot.py
# ─────────────────────────────────────────────────────────
# CONCEPT: Telegram as an interface layer for Agent 47.
#
# This file is the bridge between Telegram and your agent.
# It does three things:
#   1. Receives messages from your phone via Telegram
#   2. Passes them to the agent loop (same loop as main.py)
#   3. Sends the agent's response back to your phone
#
# Security: only your TELEGRAM_USER_ID can talk to the bot.
# Everyone else gets ignored silently.
#
# Run this instead of main.py when you want phone access:
#   python telegram_bot.py
# ─────────────────────────────────────────────────────────

import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)

from memory.history import load_history, save_history, clear_history, trim_history
from memory.usage import UsageTracker
from agent.loop import run_async

load_dotenv()

TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_USER_ID = int(os.environ.get("TELEGRAM_USER_ID", "0"))

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.WARNING   # suppress verbose telegram logs
)

# ── Shared state ───────────────────────────────────────────
# One history + tracker per bot session.
# These persist across messages until you restart the bot.
messages: list[dict] = []
tracker  = UsageTracker()


def _load_initial_history():
    """Load and trim history on startup, same as main.py."""
    global messages
    msgs = load_history()
    if msgs:
        messages = trim_history(msgs)
    else:
        messages = []


# ── Handlers ───────────────────────────────────────────────

def _is_authorized(update: Update) -> bool:
    """Only allow messages from your Telegram user ID."""
    return update.effective_user.id == TELEGRAM_USER_ID


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        return
    await update.message.reply_text(
        "👋 Agent 47 online.\n\n"
        "Commands:\n"
        "/clear — wipe conversation history\n"
        "/cost  — show session token usage and cost\n"
        "/tools — list available tools"
    )


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        return
    global messages
    clear_history()
    messages = []
    await update.message.reply_text("🗑️ History cleared.")


async def cost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        return
    summary = (
        f"📊 Session so far:\n"
        f"  API calls:   {tracker.total_api_calls}\n"
        f"  Input:       {tracker.total_input_tokens:,} tokens\n"
        f"  Output:      {tracker.total_output_tokens:,} tokens\n"
        f"  Est. cost:   ${tracker.total_cost:.4f}"
    )
    await update.message.reply_text(summary)


async def tools(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        return
    static = [
        "list_files", "read_file", "write_file", "delete_file",
        "find_files", "open_file", "git_status", "git_diff",
        "git_diff_stat", "execute_python", "create_tool",
        "list_dynamic_tools", "delete_tool"
    ]
    text = "🔧 Built-in tools:\n" + "\n".join(f"  • {t}" for t in static)
    text += "\n\nPlus GitHub, Brave, Gmail tools when needed."
    await update.message.reply_text(text)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Main message handler — the heart of the Telegram interface.

    CONCEPT: Why send a typing indicator?
      The agent loop can take 5-30 seconds depending on how many
      tool calls are needed. Without feedback, it looks broken.
      Telegram's "typing..." indicator shows the agent is working.
    """
    if not _is_authorized(update):
        return

    global messages

    user_text = update.message.text.strip()
    if not user_text:
        return

    # Show typing indicator while agent works
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )

    # Add user message and run the agent loop
    messages.append({"role": "user", "content": user_text})

    try:
        messages = await run_async(messages, tracker)
    except Exception as e:
        await update.message.reply_text(f"❌ Agent error: {e}")
        return

    # Extract the last assistant text response
    last = messages[-1] if messages else None
    reply = ""

    if last and last.get("role") == "assistant":
        content = last.get("content", "")
        if isinstance(content, str):
            reply = content
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    reply += block.get("text", "")

    if not reply:
        reply = "(Agent completed the task with no text response)"

    # Telegram has a 4096 char limit per message — split if needed
    if len(reply) <= 4096:
        await update.message.reply_text(reply)
    else:
        for i in range(0, len(reply), 4096):
            await update.message.reply_text(reply[i:i+4096])


# ── Entry point ────────────────────────────────────────────

def main():
    if not TELEGRAM_TOKEN:
        print("❌ Missing TELEGRAM_TOKEN in .env")
        return
    if not TELEGRAM_USER_ID:
        print("❌ Missing TELEGRAM_USER_ID in .env")
        return

    _load_initial_history()

    print("🤖 Agent 47 Telegram bot starting...")
    print(f"   Authorized user ID: {TELEGRAM_USER_ID}")
    print("   Send a message from Telegram to start.\n")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(CommandHandler("cost",  cost))
    app.add_handler(CommandHandler("tools", tools))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()


if __name__ == "__main__":
    main()