# agent/loop.py
# ─────────────────────────────────────────────────────────
# CONCEPT: Config-driven MCP connections.
#
# Instead of hardcoding server URLs in code, we read mcp.json
# at startup. Any HTTP MCP server can be added by editing the
# JSON — no code changes needed.
#
# Architecture:
#   - Local stdio server  → always connected (your file tools)
#   - Remote HTTP servers → loaded dynamically from mcp.json
#
# Adding a new server is just adding an entry to mcp.json.
# ─────────────────────────────────────────────────────────

import asyncio
import json
import os
import re
from pathlib import Path

import anthropic
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.streamable_http import streamablehttp_client

from agent.pretty import print_claude, print_tool_call, print_tool_result
from memory.history import save_history
from memory.usage import UsageTracker
from config import MODEL, MAX_TOKENS, SYSTEM_PROMPT, API_KEY

client = anthropic.Anthropic(api_key=API_KEY)

MCP_CONFIG_PATH = Path("mcp.json")


def load_mcp_config() -> dict:
    if not MCP_CONFIG_PATH.exists():
        print("⚠️  No mcp.json found — only local tools will be available.")
        return {"mcpServers": {}}

    raw = MCP_CONFIG_PATH.read_text()

    def substitute(match):
        var_name = match.group(1)
        value = os.environ.get(var_name)
        if not value:
            print(f"⚠️  mcp.json references ${{{var_name}}} but it's not set in .env")
            return ""
        return value

    substituted = re.sub(r"\$\{(\w+)\}", substitute, raw)
    return json.loads(substituted)


def run(messages: list[dict], tracker: UsageTracker = None) -> list[dict]:
    return asyncio.run(_run_async(messages, tracker or UsageTracker()))


async def _collect_tools(session: ClientSession, prefix: str) -> tuple[list[dict], dict]:
    response = await session.list_tools()
    tools_for_claude = []
    owner_map = {}

    for t in response.tools:
        prefixed = f"{prefix}__{t.name}"
        tools_for_claude.append({
            "name":         prefixed,
            "description":  t.description,
            "input_schema": t.inputSchema,
        })
        owner_map[prefixed] = (session, t.name)

    return tools_for_claude, owner_map


async def _connect_remote_servers(config: dict, stack):
    servers = config.get("mcpServers", {})
    sessions = []

    for name, cfg in servers.items():
        server_type = cfg.get("type")

        try:
            if server_type == "http":
                url     = cfg["url"]
                headers = cfg.get("headers", {})
                read, write, _ = await stack.enter_async_context(
                    streamablehttp_client(url, headers=headers)
                )

            elif server_type == "stdio":
                env = {
                    k: os.path.expandvars(v)
                    for k, v in cfg.get("env", {}).items()
                }
                env = {
                    k: re.sub(r"\$\{(\w+)\}", lambda m: os.environ.get(m.group(1), ""), v)
                    for k, v in env.items()
                }
                params = StdioServerParameters(
                    command=cfg["command"],
                    args=cfg.get("args", []),
                    env={**os.environ, **env}
                )
                read, write = await stack.enter_async_context(
                    stdio_client(params)
                )

            else:
                print(f"  ⚠️  Unknown type '{server_type}' for '{name}' — skipping")
                continue

            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            sessions.append((name, session))
            print(f"  🌐 Connected: {name} ({server_type})")

        except Exception as e:
            print(f"  ⚠️  Skipping '{name}': {e}")

    return sessions


async def _run_async(messages: list[dict], tracker: UsageTracker) -> list[dict]:

    config = load_mcp_config()

    server_params = StdioServerParameters(
        command="python",
        args=["-m", "mcp_server.server"]
    )

    async with stdio_client(server_params) as (local_read, local_write):
        async with ClientSession(local_read, local_write) as local_session:
            await local_session.initialize()

            from contextlib import AsyncExitStack

            async with AsyncExitStack() as stack:
                remote_sessions = await _connect_remote_servers(config, stack)

                async def refresh_tools():
                    all_tools = []
                    owner_map = {}

                    t, m = await _collect_tools(local_session, prefix="local")
                    all_tools.extend(t)
                    owner_map.update(m)

                    for name, session in remote_sessions:
                        t, m = await _collect_tools(session, prefix=name)
                        all_tools.extend(t)
                        owner_map.update(m)

                    return all_tools, owner_map

                # ── Agentic loop ───────────────────────────
                all_tools, tool_owner = await refresh_tools()

                try:
                    response = client.messages.create(
                        model=MODEL,
                        max_tokens=MAX_TOKENS,
                        system=SYSTEM_PROMPT,
                        tools=all_tools,
                        messages=messages,
                    )
                except Exception as e:
                    print(f"\n❌ API error: {e}")
                    return messages

                # Record usage for this API call
                tracker.record(
                    response.usage.input_tokens,
                    response.usage.output_tokens,
                    label=f"turn_{tracker.total_api_calls}"
                )

                while response.stop_reason == "tool_use":

                    for block in response.content:
                        if hasattr(block, "text") and block.text:
                            print_claude(block.text)

                    messages.append({
                        "role": "assistant",
                        "content": serialize(response.content)
                    })

                    tool_results = []
                    for block in response.content:
                        if block.type != "tool_use":
                            continue

                        print_tool_call(block.name, block.input)

                        owner = tool_owner.get(block.name)
                        if owner is None:
                            result = f"Unknown tool: {block.name}"
                        else:
                            session, real_name = owner
                            try:
                                mcp_result = await session.call_tool(
                                    real_name, block.input
                                )
                                result = "\n".join(
                                    c.text for c in mcp_result.content
                                    if hasattr(c, "text")
                                )
                            except Exception as e:
                                result = f"Error calling '{block.name}': {e}"

                        print_tool_result(result)

                        tool_results.append({
                            "type":        "tool_result",
                            "tool_use_id": block.id,
                            "content":     result,
                        })

                    messages.append({"role": "user", "content": tool_results})

                    all_tools, tool_owner = await refresh_tools()

                    try:
                        response = client.messages.create(
                            model=MODEL,
                            max_tokens=MAX_TOKENS,
                            system=SYSTEM_PROMPT,
                            tools=all_tools,
                            messages=messages,
                        )
                    except Exception as e:
                        print(f"\n❌ API error mid-task: {e}")
                        messages = messages[:-2]
                        save_history(messages)
                        return messages

                    # Record usage for this tool-loop API call
                    tracker.record(
                        response.usage.input_tokens,
                        response.usage.output_tokens,
                        label=f"turn_{tracker.total_api_calls}"
                    )

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
    if isinstance(content, list):
        return [serialize(block) for block in content]
    if hasattr(content, "model_dump"):
        return content.model_dump()
    return content