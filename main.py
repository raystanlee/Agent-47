# main.py
# ─────────────────────────────────────────────────────────
# Entry point. Run this file to start the agent.
#   python main.py
# ─────────────────────────────────────────────────────────

from config import SAFE_ROOT, API_KEY
from safety.sandbox import ensure_workspace_exists
from memory.history import load_history, clear_history
from agent.loop import run
from agent.pretty import print_user, print_separator


def main():
    # Basic checks before we start
    if not API_KEY:
        print("❌ Missing ANTHROPIC_API_KEY. Run: export ANTHROPIC_API_KEY='sk-ant-...'")
        return

    ensure_workspace_exists()
    print(f"📂 Workspace: {SAFE_ROOT}")
    print("💡 Commands: 'quit' to exit | 'clear history' to reset memory\n")
    print_separator()

    # Load existing conversation history from disk
    # This is what gives the agent memory across sessions
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

        print_user(user_input)
        print_separator()

        # Add the user's message to history
        messages.append({"role": "user", "content": user_input})

        # Run the agentic loop — this is where the magic happens
        messages = run(messages)

        print_separator()


if __name__ == "__main__":
    main()