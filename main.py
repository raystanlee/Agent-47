# main.py
# ─────────────────────────────────────────────────────────
# Entry point. Run: python main.py
#
# Runs CLI and Telegram bot concurrently in one process.
# Both interfaces share the same conversation history,
# tracker, and asyncio lock so they never overlap.
# ─────────────────────────────────────────────────────────

import asyncio
import logging
import os

from dotenv import load_dotenv

from config import SAFE_ROOTS, API_KEY
from safety.sandbox import ensure_workspace_exists
from memory.history import load_history, clear_history, trim_history
from memory.usage import UsageTracker
from agent.loop import run_async
from agent.pretty import print_user, print_separator
from mcp_server.tool_store import list_saved_tool_names

load_dotenv()

TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_USER_ID = int(os.environ.get("TELEGRAM_USER_ID", "0"))

# ── Shared session state ──────────────────────────────────
# Both CLI and Telegram read/write these.
# The lock ensures they never run the agent at the same time.
messages: list[dict] = []
tracker  = UsageTracker()
lock     = asyncio.Lock()


def print_tools():
    static = [
        "list_files", "read_file", "write_file",
        "delete_file", "delete_folder_contents",
        "create_folder", "move_file", "rename_file",
        "find_files", "open_file",
        "git_status", "git_diff", "git_diff_stat",
        "execute_python",
    ]
    dynamic = list_saved_tool_names()

    print("\n📦 Static tools (built-in):")
    for name in static:
        print(f"   • {name}")

    if dynamic:
        print(f"\n⚡ Dynamic tools (agent-created): {len(dynamic)}")
        for name in sorted(dynamic):
            print(f"   • {name}")
    else:
        print("\n⚡ Dynamic tools: none yet")

    print("\n🔧 Meta-tools:")
    for name in ["create_tool", "list_dynamic_tools", "delete_tool"]:
        print(f"   • {name}")
    print()


# ── Telegram handlers ─────────────────────────────────────

def _authorized(update) -> bool:
    return update.effective_user.id == TELEGRAM_USER_ID


async def tg_start(update, context):
    if not _authorized(update):
        return
    await update.message.reply_text(
        "👋 Agent 47 online.\n\n"
        "Commands:\n"
        "/clear — wipe conversation history\n"
        "/cost  — show session token usage and cost\n"
        "/tools — list available tools"
    )


async def tg_clear(update, context):
    if not _authorized(update):
        return
    global messages
    clear_history()
    messages = []
    await update.message.reply_text("🗑️ History cleared.")


async def tg_cost(update, context):
    if not _authorized(update):
        return
    summary = (
        f"📊 Session so far:\n"
        f"  API calls:   {tracker.total_api_calls}\n"
        f"  Input:       {tracker.total_input_tokens:,} tokens\n"
        f"  Output:      {tracker.total_output_tokens:,} tokens\n"
        f"  Est. cost:   ${tracker.total_cost:.4f}"
    )
    await update.message.reply_text(summary)


async def tg_tools(update, context):
    if not _authorized(update):
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


async def tg_handle_message(update, context):
    if not _authorized(update):
        return

    global messages

    user_text = update.message.text.strip()
    if not user_text:
        return

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )

    # Record time before running so we can detect freshly saved images
    import time
    run_start = time.time()

    async with lock:
        messages.append({"role": "user", "content": user_text})
        try:
            messages = await run_async(messages, tracker)
        except Exception as e:
            await update.message.reply_text(f"❌ Agent error: {e}")
            return

    # Send captured image if one was saved during this run
    import os
    img_path = "/tmp/last_capture.jpg"
    if os.path.exists(img_path) and os.path.getmtime(img_path) >= run_start:
        with open(img_path, "rb") as f:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=f
            )

    # Extract last assistant text response
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

    # Telegram 4096 char limit — split if needed
    for i in range(0, len(reply), 4096):
        await update.message.reply_text(reply[i:i + 4096])


# ── CLI loop ──────────────────────────────────────────────

async def cli_loop():
    global messages
    loop = asyncio.get_event_loop()

    while True:
        try:
            user_input = await loop.run_in_executor(
                None, lambda: input("\nYou: ").strip()
            )
        except (EOFError, KeyboardInterrupt):
            print("\n👋 Goodbye!")
            tracker.print_summary()
            return

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "q"):
            print("👋 Goodbye!")
            tracker.print_summary()
            return

        if user_input.lower() == "clear history":
            clear_history()
            messages = []
            continue

        if user_input.lower() == "tools":
            print_tools()
            continue

        print_user(user_input)
        print_separator()

        async with lock:
            messages.append({"role": "user", "content": user_input})
            messages = await run_async(messages, tracker)

        print_separator()


# ── Entry point ───────────────────────────────────────────

async def main_async():
    global messages

    if not API_KEY:
        print("❌ Missing ANTHROPIC_API_KEY. Run: export ANTHROPIC_API_KEY='sk-ant-...'")
        return

    ensure_workspace_exists()
    print(f"📂 Workspace: {SAFE_ROOTS}")

    msgs = load_history()
    if msgs:
        messages = trim_history(msgs)
        print(f"📖 Resuming session ({len(messages)} messages in history)\n")

    print("💡 Commands: 'quit' to exit | 'clear history' to reset | 'tools' to list tools\n")
    print_separator()

    if TELEGRAM_TOKEN and TELEGRAM_USER_ID:
        from telegram.ext import (
            ApplicationBuilder, CommandHandler, MessageHandler, filters
        )
        logging.basicConfig(level=logging.WARNING)
        logging.getLogger("mcp").setLevel(logging.ERROR)
        logging.getLogger("mcp.server").setLevel(logging.ERROR)

        tg_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        tg_app.add_handler(CommandHandler("start", tg_start))
        tg_app.add_handler(CommandHandler("clear", tg_clear))
        tg_app.add_handler(CommandHandler("cost",  tg_cost))
        tg_app.add_handler(CommandHandler("tools", tg_tools))
        tg_app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, tg_handle_message
        ))

        print(f"🤖 Telegram bot active (user ID: {TELEGRAM_USER_ID})\n")

        async with tg_app:
            await tg_app.start()
            await tg_app.updater.start_polling()
            try:
                await cli_loop()
            except (KeyboardInterrupt, asyncio.CancelledError):
                pass
            finally:
                await tg_app.updater.stop()
                await tg_app.stop()
    else:
        print("⚠️  No TELEGRAM_TOKEN/TELEGRAM_USER_ID set — running CLI only\n")
        await cli_loop()


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
