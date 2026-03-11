# agent/loop.py
# ─────────────────────────────────────────────────────────
# CONCEPT: The agentic loop — now MCP-powered.
#
# What changed from the old version:
#   BEFORE: loop called tool functions directly (TOOL_REGISTRY)
#   AFTER:  loop talks to MCP server via a client session
#
# What stayed the same:
#   - The loop structure (send → get response → handle tools → repeat)
#   - How we talk to Claude
#   - How we save history
#   - Pretty printing
#
# New concepts here:
#   - async/await  (required by MCP client)
#   - ClientSession (the MCP client object)
#   - StdioServerParameters (tells the client how to launch the server)
# ─────────────────────────────────────────────────────────

import asyncio
import anthropic

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

from agent.pretty import print_claude, print_tool_call, print_tool_result
from memory.history import save_history
from config import MODEL, MAX_TOKENS, SYSTEM_PROMPT, API_KEY

client = anthropic.Anthropic(api_key=API_KEY)


def run(messages: list[dict]) -> list[dict]:
    """
    Public entry point — called from main.py exactly as before.

    main.py is synchronous (normal Python). But our MCP client
    needs async. So we use asyncio.run() to bridge them.

    asyncio.run() says: "spin up an async event loop, run this
    coroutine inside it, wait for it to finish, then return."
    """
    return asyncio.run(_run_async(messages))


async def _run_async(messages: list[dict]) -> list[dict]:
    """
    The real loop — async so it can await MCP calls.

    CONCEPT: StdioServerParameters
      This tells the MCP client HOW to launch the server.
      - command: the executable to run ("python")
      - args: arguments passed to it (["-m", "mcp_server.server"])

      So when the client connects, it literally runs:
        python -m mcp_server.server
      as a subprocess, then pipes stdio to/from it.

      You never have to start the server manually — the client
      starts it automatically when your agent runs.

    CONCEPT: ClientSession
      This is your handle to the MCP server.
      Through it you can:
        - session.list_tools()    → ask what tools exist
        - session.call_tool()     → call a specific tool
      The session manages the stdio pipe connection for you.
    """

    # Tell the MCP client how to launch our server
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "mcp_server.server"]
    )

    # stdio_client() launches the server subprocess and opens the pipe
    # ClientSession wraps the connection with a nice API
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:

            # Always initialize first — this is the MCP handshake.
            # The client says "hello", the server replies with its
            # capabilities. Without this, nothing works.
            await session.initialize()

            # Ask the server: "what tools do you have?"
            # This returns all static + dynamic + create_tool schemas.
            # We convert them into the format Claude's API expects.
            tools_response = await session.list_tools()
            tools = [
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.inputSchema  # Claude uses input_schema
                }
                for t in tools_response.tools
            ]

            # ── Main agentic loop ─────────────────────────
            # Same structure as before — just tool execution changed.
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                tools=tools,          # tools now come from MCP, not definitions.py
                messages=messages,
            )

            while response.stop_reason == "tool_use":

                # Print any text Claude wrote before calling tools
                for block in response.content:
                    if hasattr(block, "text") and block.text:
                        print_claude(block.text)

                # Serialize and store Claude's response in history
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

                    # CONCEPT: session.call_tool()
                    #   Instead of looking up a function in TOOL_REGISTRY,
                    #   we ask the MCP server to run the tool for us.
                    #   The server handles routing to static or dynamic handlers.
                    #
                    #   This is the key difference. The agent loop no longer
                    #   knows anything about how tools work internally.
                    #   It just says "run this" and gets a result back.
                    try:
                        mcp_result = await session.call_tool(block.name, block.input)
                        # MCP returns a list of content blocks — we join them
                        result = "\n".join(
                            c.text for c in mcp_result.content
                            if hasattr(c, "text")
                        )
                    except Exception as e:
                        result = f"MCP error calling '{block.name}': {e}"

                    print_tool_result(result)

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

                messages.append({"role": "user", "content": tool_results})

                # Call Claude again with the updated history + tool results
                response = client.messages.create(
                    model=MODEL,
                    max_tokens=MAX_TOKENS,
                    system=SYSTEM_PROMPT,
                    tools=tools,
                    messages=messages,
                )

            # Claude finished — print final response
            for block in response.content:
                if hasattr(block, "text") and block.text:
                    print_claude(block.text)

            messages.append({
                "role": "assistant",
                "content": serialize(response.content)
            })

            save_history(messages)
            return messages


def serialize(content):
    """
    Convert SDK response objects into plain dicts for JSON storage.
    Unchanged from the original — needed so history.json stays clean.
    """
    if isinstance(content, list):
        return [serialize(block) for block in content]
    if hasattr(content, "model_dump"):
        return content.model_dump()
    return content