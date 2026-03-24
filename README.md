# Agent 47 — My PC AI Agent

An AI agent that manages files, talks to GitHub, searches the web, and reads Gmail — all through natural language. It connects to multiple MCP servers simultaneously so it can chain local file operations, GitHub API calls, web search, and email in a single task. Built as a learning project to understand how agentic AI and the Model Context Protocol work from the ground up.

## What it does

You tell it what to do in plain English and it figures out the steps. Things like:

- "Delete all files in the temp folder"
- "Analyze the CSV in my workspace and show me the key trends"
- "Read my README, check git diff, rewrite it, and push to GitHub"
- "What is in this image?" ← it will write a vision tool if it doesn't have one
- "Search GitHub for issues in my repo" ← talks to GitHub directly
- "Search the web for X and summarise the results"
- "What are my most recent emails about?"

If it needs a capability it doesn't have yet, it writes the tool itself, registers it, and uses it — all in the same turn. Those tools are saved to disk and available on every future run.

## How it works

The agent uses Claude as the brain (planner and orchestrator). You give it an instruction, Claude decides which tools to call and in what order, and Python executes the actual operations. Claude never touches your file system or GitHub directly — it just plans, your code acts.

Tools are served over **MCP (Model Context Protocol)** — an open standard that separates your agent logic from your tool layer. The agent connects to **multiple MCP servers simultaneously**:

- **Local server** — file ops, read/write files, code execution, git tools, dynamic tool creation
- **GitHub MCP server** — read/write issues, PRs, files, branches, search code, and more
- **Brave Search MCP server** — web search, news, images, video, local search
- **Gmail MCP server** — read, search, summarise, and send emails

Servers are defined in `mcp.json` — add any MCP server by dropping an entry there, no code changes needed.

### The self-extension loop

```
User asks for something
    ↓
Agent checks available tools (from all servers)
    ↓
Tool missing? → calls create_tool → writes Python code → registers it live
    ↓
Calls the new tool immediately
    ↓
Tool saved to disk — available on every future run
```

### Multi-server architecture

```
                    ┌──────────────────────┐
                    │       Claude         │
                    │  (plans & decides)   │
                    └────────┬─────────────┘
                             │
                    ┌────────▼─────────────┐
                    │      Agent Loop      │
                    │  (prefix routing)    │
                    └──┬──────┬──────┬─────┘
                       │      │      │      │
            ┌──────────▼─┐ ┌──▼────┐ ┌─▼──────┐ ┌─▼──────┐
            │ Local MCP  │ │GitHub │ │ Brave  │ │ Gmail  │
            │ (stdio)    │ │ (HTTP)│ │(stdio) │ │(stdio) │
            │            │ │       │ │        │ │        │
            │ file ops   │ │repos, │ │web,    │ │read,   │
            │ git tools  │ │issues,│ │news,   │ │search, │
            │ execute_py │ │PRs,   │ │images  │ │send    │
            │ dynamic    │ │search │ │        │ │        │
            │ tools      │ │       │ │        │ │        │
            └────────────┘ └───────┘ └────────┘ └────────┘
```

## Setup

**1. Clone the repo and activate the virtual environment:**
```bash
cd "Agent 47"
python -m venv venv
source venv/bin/activate
```

**2. Install dependencies:**
```bash
pip install -r requirements.txt
```

**3. Add your API keys to `.env`:**
```
ANTHROPIC_API_KEY=sk-ant-...
GITHUB_TOKEN=ghp_...
BRAVE_API_KEY=BSA...
```

**4. Set your workspace folders in `config.py`:**
```python
SAFE_ROOTS = [
    Path("/Users/you/Agent 47").resolve(),
    Path("/Users/you/AgentWorkspace").resolve(),
]
```

**5. Configure external MCP servers in `mcp.json`:**
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

For Gmail, follow the OAuth setup in `get_gmail_token.py` to generate credentials, then add the gmail entry to `mcp.json`.

**6. Run it:**
```bash
python main.py
```

## Session commands

| Command | What it does |
|---|---|
| `tools` | List all available tools (built-in + agent-created) |
| `clear history` | Wipe conversation memory and start fresh |
| `quit` | Exit and print session cost summary |

## Project structure

```
Agent 47/
├── main.py               # Entry point
├── config.py             # Settings and system prompt
├── mcp.json              # MCP server config (gitignored)
├── agent/
│   ├── loop.py           # The agentic loop (multi-server MCP)
│   └── pretty.py         # Coloured terminal output
├── mcp_server/
│   ├── server.py         # Local MCP server
│   ├── tool_store.py     # Saves/loads dynamic tools to disk
│   └── dynamic_tools/    # Agent-created tools (auto-generated)
├── tools/
│   ├── handlers.py       # What each built-in tool actually does
│   └── __init__.py       # Tool registry
├── safety/
│   └── sandbox.py        # Keeps the agent inside allowed workspaces
└── memory/
    ├── history.py         # Conversation persistence
    └── usage.py           # Token and cost tracking
```

## Built-in tools

| Tool | What it does |
|---|---|
| `list_files` | List folder contents |
| `read_file` | Read a text file (capped at 8k chars) |
| `write_file` | Write or create a file |
| `delete_file` | Delete a file or folder |
| `delete_folder_contents` | Empty a folder without deleting it |
| `create_folder` | Create nested folders |
| `move_file` | Move a file or folder |
| `rename_file` | Rename a file or folder |
| `find_files` | Recursive glob search across all safe roots |
| `open_file` | Open with macOS default app |
| `git_status` | Run `git status` in a repo |
| `git_diff` | Full diff (staged or unstaged) |
| `git_diff_stat` | Compact diff summary — filenames and line counts only |
| `execute_python` | Run a Python snippet in a sandboxed subprocess |
| `create_tool` | Write and register a new tool at runtime |
| `list_dynamic_tools` | List all agent-created tools |
| `delete_tool` | Remove a dynamic tool from memory and disk |

Plus all tools from GitHub, Brave Search, and Gmail MCP servers.

## Cost tracking

Every session prints a summary on exit showing input tokens, output tokens, total cost, and which turns were most expensive. Current pricing is Claude Sonnet 4.6 — $3/M input, $15/M output.

The biggest cost driver is tool schemas: every API call sends the full schema list from all connected MCP servers. A session with GitHub + Brave + Gmail connected costs more per turn than one with only local tools — even if none of those tools are used.

## Notes

- The agent can only access folders defined in `SAFE_ROOTS` in `config.py`
- Conversation history is summarised automatically when it gets too long
- Agent-created tools are saved in `mcp_server/dynamic_tools/` — one `.py` + one `.json` per tool
- `mcp.json` is gitignored — keep API keys in `.env` and reference them with `${VAR_NAME}`
- Run `clear history` to reset memory between unrelated sessions

---

*Committed by Agent 47*