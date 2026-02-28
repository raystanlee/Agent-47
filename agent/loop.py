# agent/loop.py
# ─────────────────────────────────────────────────────────
# CONCEPT: The Agentic Loop — this is the core of everything.
#
# A normal LLM call is one-shot: you send a message, get a reply.
# An AGENT is different. It loops:
#
#   ┌──────────────────────────────────────────┐
#   │  1. Send messages to Claude              │
#   │  2. Claude replies with text OR tool use │
#   │  3. If tool use → run the tool           │
#   │  4. Send tool result back to Claude      │
#   │  5. Claude replies again                 │
#   │  6. Repeat until Claude says "end_turn"  │
#   └──────────────────────────────────────────┘
#
# This loop is what makes Claude an AGENT rather than a chatbot.
# It can take multiple steps, check results, and self-correct.
# ─────────────────────────────────────────────────────────

# agent/loop.py

import anthropic
from agent.pretty import print_claude, print_tool_call, print_tool_result
from tools import TOOL_REGISTRY, TOOL_DEFINITIONS
from memory.history import save_history
from config import MODEL, MAX_TOKENS, SYSTEM_PROMPT, API_KEY

client = anthropic.Anthropic(api_key=API_KEY)


def serialize(content):
    """
    Convert SDK response objects into plain dicts for JSON storage.
    This is critical — if we store raw SDK objects, they break when
    reloaded from history.json on the next session.
    """
    if isinstance(content, list):
        return [serialize(block) for block in content]
    if hasattr(content, "model_dump"):
        return content.model_dump()
    return content


def run(messages: list[dict]) -> list[dict]:
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        tools=TOOL_DEFINITIONS,
        messages=messages,
    )

    while response.stop_reason == "tool_use":

        # Print any text Claude wrote before calling tools
        for block in response.content:
            if hasattr(block, "text") and block.text:
                print_claude(block.text)

        # Serialize before appending — plain dicts only
        messages.append({
            "role": "assistant",
            "content": serialize(response.content)
        })

        # Execute each tool Claude requested
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            print_tool_call(block.name, block.input)

            handler = TOOL_REGISTRY.get(block.name)
            if handler:
                try:
                    result = handler(**block.input)
                except PermissionError as e:
                    result = str(e)
                except Exception as e:
                    result = f"Error: {e}"
            else:
                result = f"Unknown tool: {block.name}"

            print_tool_result(result)

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result,
            })

        messages.append({"role": "user", "content": tool_results})

        # Call Claude again with updated history
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )

    # Claude is done
    for block in response.content:
        if hasattr(block, "text") and block.text:
            print_claude(block.text)

    # Serialize final message before saving
    messages.append({
        "role": "assistant",
        "content": serialize(response.content)
    })

    save_history(messages)
    return messages