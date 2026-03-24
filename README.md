# Agent 47 — My Personal AI Agent

A personal AI agent that runs on your Mac, connects to your phone via Telegram, manages files, talks to GitHub, searches the web, reads Gmail, executes code, and extends itself by writing new tools on demand. Built from scratch to understand how agentic AI and the Model Context Protocol work at a fundamental level.

> 🎬 *Demo GIF coming soon*

## What it does

You tell it what to do in plain English — from your terminal or your phone — and it figures out the steps:

- "Analyze the CSV in my workspace and show me the key trends"
- "Read my README, check git diff, rewrite it, and push to GitHub"
- "What is in this image?" ← writes a vision tool on the spot if needed
- "Search GitHub for open issues in my repo"
- "Search the web for the latest AI research and summarise it"
- "What are my most recent emails about?"
- "Delete all files in the temp folder"

If it needs a capability it doesn't have yet, it writes the tool itself, registers it, and uses it — all in the same turn. Those tools are saved to disk and available on every future run.

## Interfaces

| Interface | How to run | Use case |
|---|---|---|
| Terminal | `python main.py` | Development, debugging |
| Telegram | `python telegram_bot.py` | Phone access, anywhere |

Both share the same history, tools, and cost tracking.

## Architecture

```
You (terminal or phone)
        │
        ▼
┌───────────────────┐
│   Interface Layer  │
│ main.py / Telegram │
└────────┬──────────┘
         │
         ▼
┌───────────────────────────────────────┐
│           Agent Loop (loop.py)         │
│                                        │
│  1. Haiku classifier → which servers?  │
│  2. Fetch only relevant tool schemas   │
│  3. Claude plans → tools execute       │
│  4. Track tokens + cost per turn       │
└──┬──────────┬──────────┬──────────┬───┘
   │          │          │          │
   ▼          ▼          ▼          ▼
Local MCP  GitHub MCP  Brave MCP  Gmail MCP
(stdio)    (HTTP)      (stdio)    (stdio)
file ops   repos       web search read/send
git tools  issues      news       emails
execute_py PRs         images
dynamic    search
tools
```

### Intent-based tool routing

Every turn, a cheap Haiku classifier decides which MCP servers are actually needed before the main Sonnet call. A simple "hi" only loads local tools (~20 schemas) instead of all servers (~85 schemas) — cutting input token cost by ~70% on focused tasks.

```
User message → Haiku classifier → ["github"] → load only github + local tools
                                                → main Sonnet call (cheaper)
```

### The self-extension loop

```
User asks for something
    ↓
Agent checks available tools
    ↓
Tool missing? → create_tool → writes Python → registers live
    ↓
Calls the new tool immediately
    ↓
Saved to disk — available forever
```

## Setup

**1. Clone and activate venv:**
```bash
cd "Agent 47"
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**2. Add API keys to `.env`:**
```
ANTHROPIC_API_KEY=sk-ant-...
GITHUB_TOKEN=ghp_...
BRAVE_API_KEY=BSA...
TELEGRAM_TOKEN=...
TELEGRAM_USER_ID=...
```

**3. Set workspace folders in `config.py`:**
```python
SAFE_ROOTS = [
    Path("/Users/you/Agent 47").resolve(),
    Path("/Users/you/AgentWorkspace").resolve(),
]
```

**4. Configure MCP servers in `mcp.json`:**
```json
{
  "mcpServers": {
    "github": {
      "type": "http",
      "url": "https://api.githubcopilot.com/mcp/",
      "headers": { "Authorization": "Bearer ${GITHUB_TOKEN}" }
    },
    "brave": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@brave/brave-search-mcp-server"],
      "env": { "BRAVE_API_KEY": "${BRAVE_API_KEY}" }
    }
  }
}
```

For Gmail, run `get_gmail_token.py` once for OAuth setup, then add the gmail entry to `mcp.json`. Add any MCP server by dropping an entry — no code changes needed.

**5. Run:**
```bash
python main.py          # terminal
python telegram_bot.py  # phone via Telegram
```

## Commands

**Terminal:**
| Command | What it does |
|---|---|
| `tools` | List all available tools |
| `clear history` | Reset conversation memory |
| `quit` | Exit and print cost summary |

**Telegram:**
| Command | What it does |
|---|---|
| `/start` | Show help |
| `/clear` | Reset conversation memory |
| `/cost` | Show session token usage and cost |
| `/tools` | List available tools |

## Project structure

```
Agent 47/
├── main.py               # Terminal entry point
├── telegram_bot.py       # Telegram bot entry point
├── config.py             # Settings and system prompt
├── mcp.json              # MCP server config (gitignored)
├── agent/
│   ├── loop.py           # Agentic loop + classifier + routing
│   └── pretty.py         # Coloured terminal output
├── mcp_server/
│   ├── server.py         # Local MCP server
│   ├── tool_store.py     # Dynamic tool persistence
│   └── dynamic_tools/    # Agent-created tools (auto-generated)
├── tools/
│   ├── handlers.py       # Built-in tool implementations
│   └── __init__.py       # Tool registry
├── safety/
│   └── sandbox.py        # Path sandboxing across all safe roots
└── memory/
    ├── history.py         # Conversation persistence + auto-summarisation
    └── usage.py           # Token and cost tracking
```

## Built-in tools

| Tool | What it does |
|---|---|
| `list_files` | List folder contents |
| `read_file` | Read a text file (capped at 8k chars) |
| `write_file` | Write or create a file |
| `delete_file` | Delete a file or folder |
| `delete_folder_contents` | Empty a folder |
| `create_folder` | Create nested folders |
| `move_file` | Move a file or folder |
| `rename_file` | Rename a file or folder |
| `find_files` | Recursive glob search across all safe roots |
| `open_file` | Open with macOS default app |
| `git_status` | Run `git status` in a repo |
| `git_diff` | Full diff (staged or unstaged) |
| `git_diff_stat` | Compact diff summary |
| `execute_python` | Run Python in a sandboxed subprocess |
| `create_tool` | Write and register a new tool at runtime |
| `list_dynamic_tools` | List agent-created tools |
| `delete_tool` | Remove a dynamic tool |

Plus all tools from GitHub, Brave Search, and Gmail MCP servers.

## Cost tracking

Every session prints a breakdown on exit — API calls, input/output tokens, estimated cost, and most expensive turns. Pricing: Claude Sonnet 4.6 at $3/M input, $15/M output. The Haiku classifier runs at ~$0.001/M input — nearly free.

The biggest cost driver is tool schemas sent as input on every turn. The classifier cuts this by only loading schemas for servers actually needed.

## Notes

- Agent can only access folders defined in `SAFE_ROOTS` — nothing outside them
- History is summarised automatically when it gets too long to prevent rate limits
- `mcp.json` is gitignored — keep secrets in `.env`, reference with `${VAR_NAME}`
- Dynamic tools survive restarts — saved as `.py` + `.json` pairs in `dynamic_tools/`

## Roadmap

- [x] Local file management via MCP
- [x] Multi-server MCP (GitHub, Brave, Gmail)
- [x] Dynamic tool creation at runtime
- [x] Intent-based tool routing (Haiku classifier)
- [x] Telegram bot — phone access
- [x] Token + cost tracking
- [ ] Scheduled / proactive tasks
- [ ] Voice interface
- [ ] Hardware integration (NVIDIA Orin Nano + sensors)

---

*Committed by Agent 47*