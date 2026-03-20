# main.py
# ─────────────────────────────────────────────────────────
# Entry point. Run: python main.py
# ─────────────────────────────────────────────────────────

from config import SAFE_ROOTS, API_KEY
from safety.sandbox import ensure_workspace_exists
from memory.history import load_history, clear_history
from agent.loop import run
from agent.pretty import print_user, print_separator
from mcp_server.tool_store import list_saved_tool_names


def print_tools():
    """
    Print all available tools directly from disk + hardcoded static list.

    CONCEPT: Why not ask the MCP server?
      The MCP server is only alive during agent.loop.run().
      Between turns it's not running — it's launched and torn down
      each time run() is called.

      So for a quick CLI 'tools' command, we read directly from
      tool_store (disk) for dynamic tools, and hardcode the static
      list here. Fast, no subprocess needed.
    """
    static = [
        "list_files", "delete_file", "delete_folder_contents",
        "create_folder", "move_file", "rename_file",
        "find_files", "open_file"
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

    # Also show meta-tools so the user knows they exist
    print("\n🔧 Meta-tools:")
    for name in ["create_tool", "list_dynamic_tools", "delete_tool"]:
        print(f"   • {name}")
    print()


def main():
    if not API_KEY:
        print("❌ Missing ANTHROPIC_API_KEY. Run: export ANTHROPIC_API_KEY='sk-ant-...'")
        return

    ensure_workspace_exists()
    print(f"📂 Workspace: {SAFE_ROOTS}")
    print("💡 Commands: 'quit' to exit | 'clear history' to reset | 'tools' to list tools\n")
    print_separator()

    messages = load_history()
    if messages:
        print(f"📖 Resuming session ({len(messages)} messages in history)\n")

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 Goodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "q"):
            print("👋 Goodbye!")
            break

        if user_input.lower() == "clear history":
            clear_history()
            messages = []
            continue

        # New: show tool list without involving Claude at all
        if user_input.lower() == "tools":
            print_tools()
            continue

        print_user(user_input)
        print_separator()

        messages.append({"role": "user", "content": user_input})
        messages = run(messages)
        print_separator()


if __name__ == "__main__":
    main()