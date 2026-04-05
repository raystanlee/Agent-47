
# agent/pretty.py
# Coloured terminal output so you can see what's happening clearly.

import json

RESET  = "\033[0m"
BOLD   = "\033[1m"
BLUE   = "\033[34m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
CYAN   = "\033[36m"
GREY   = "\033[90m"


def print_claude(text: str):
    print(f"\n{BLUE}{BOLD}Claude:{RESET} {text}")


def print_tool_call(name: str, inputs: dict):
    args = json.dumps(inputs, indent=2)
    print(f"\n  {YELLOW}🔧 Tool call:{RESET} {BOLD}{name}{RESET}")
    print(f"  {GREY}{args}{RESET}")


def print_tool_result(result: str):
    # Suppress large base64 image data from being printed
    try:
        parsed = json.loads(result)
        if isinstance(parsed, dict) and "image" in parsed:
            display = {k: (f"<base64 {len(v)} chars>" if k == "image" else v)
                       for k, v in parsed.items()}
            result = json.dumps(display)
    except (json.JSONDecodeError, TypeError):
        pass
    print(f"  {GREEN}✅ Result:{RESET} {result}")


def print_user(text: str):
    print(f"\n{CYAN}{BOLD}You:{RESET} {text}")


def print_separator():
    print(f"\n{GREY}{'─' * 50}{RESET}")