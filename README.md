# Agent 47 — My PC AI Agent

An AI agent that manages files on your computer and talks to GitHub — all through natural language. It connects to multiple MCP servers at the same time, so it can chain local file operations with GitHub API calls in a single task. Built as a learning project to understand how agentic AI and the Model Context Protocol work.

## What it does

You tell it what to do in plain English and it figures out the steps. Things like:

- "Delete all files in the temp folder"
- "Open the largest image"
- "Move all PDFs to the archive folder"
- "Show me what's in the reports folder"
- "Read my README, check git diff, rewrite it, and push to GitHub"
- "What is in this image?" ← it will write a vision tool if it doesn't have one
- "Search GitHub for issues in my repo" ← talks to GitHub directly
- "Search the web for X" ← uses Brave Search

If it needs a capability it doesn't have yet, it writes the tool itself, registers it, and uses it — all in the same turn. Those tools are saved to disk and available on every future run.

## How it works

The agent uses Claude as the brain (planner and orchestrator). You give it an instruction, Claude decides which tools to call and in what order, and Python executes the actual operations. Claude never touches your file system or GitHub directly — it just plans, your code acts.

Tools are served over **MCP (Model Context Protocol)** — an open standard that separates your agent logic from your tool layer. The agent connects to **multiple MCP servers simultaneously**:

- **Local server** — file ops, dynamic tool creation, git status/diff, image analysis
- **GitHub MCP server** — read/write issues, PRs, files, branches, search code, and more
- **Brave Search MCP server** — web search, news, images, video, local search

This means you can ask it to do things across your local machine and the internet in the same turn.

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
                    │     Agent Loop        │
                    │  (prefix routing)     │
                    └───┬─────────┬────────┘
                        │         │
             ┌──────────▼──┐  ┌───▼──────────┐  ┌──────────────────┐
             │ Local MCP   │  │ GitHub MCP    │  │ Brave Search MCP │
             │ (stdio)     │  │ (HTTP)        │  │ (stdio/npx)      │
             │             │  │               │  │                  │
             │ file ops    │  │ repos, issues,│  │ web, news,       │
             │ git tools   │  │ PRs, search.. │  │ images, video    │
             │ dynamic     │  │               │  │                  │
             │ tools       │  │               │  │                  │
             └─────────────┘  └───────────────┘  └──────────────────┘
```

Servers are defined in `mcp.json` — add a new server by adding an entry there, no code changes needed.

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

**3. Add your API keys:**

Create a `.env` file in the project root:
```
ANTHROPIC_API_KEY=sk-ant-...
GITHUB_TOKEN=ghp_...
BRAVE_API_KEY=BSA...
```

GitHub and Brave tools are only available if you provide the relevant keys. The GitHub token needs the scopes required by GitHub's MCP server (repo access, etc.).

**4. Set your workspace folders in `config.py`:**
```python
SAFE_ROOTS = [
    Path("/Users/you/Agent 47").resolve(),
    Path("/Users/you/AgentWorkspace").resolve(),
]
```

The agent can access any of these roots. Paths outside all of them are blocked.

**5. Run it:**
```bash
python main.py
```

## Session commands

| Command | What it does |
|---|---|
| `tools` | List all available tools (built-in + agent-created) |
| `clear history` | Wipe conversation memory and start fresh |
| `quit` | Exit |

## Project structure

```
Agent 47/
├── main.py               # Entry point — connects to all MCP servers
├── config.py             # Settings and system prompt
├── mcp.json              # MCP server config (add servers here)
├── agent/
│   ├── loop.py           # The agentic loop (multi-server MCP)
│   └── pretty.py         # Coloured terminal output
├── mcp_server/
│   ├── server.py         # Local MCP server — exposes file + git + vision tools
│   ├── tool_store.py     # Saves/loads dynamic tools to disk
│   └── dynamic_tools/    # Agent-created tools live here (auto-generated)
├── tools/
│   ├── handlers.py       # What each built-in tool actually does
│   ├── definitions.py    # Tool schemas (legacy, kept for reference)
│   └── __init__.py       # Tool registry
├── safety/
│   └── sandbox.py        # Keeps the agent inside the allowed workspaces
└── memory/
    └── history.json      # Saves conversation between sessions
```

## Built-in tools

| Tool | What it does |
|---|---|
| `list_files` | List folder contents |
| `read_file` | Read a text file |
| `write_file` | Write/create a file |
| `delete_file` | Delete a file or folder |
| `delete_folder_contents` | Empty a folder without deleting it |
| `create_folder` | Create nested folders |
| `move_file` | Move a file or folder |
| `rename_file` | Rename a file or folder |
| `find_files` | Recursive glob search |
| `open_file` | Open with macOS default app |
| `git_status` | Run `git status` in a repo |
| `git_diff` | Run `git diff` (staged or unstaged) |
| `create_tool` | Write and register a new tool at runtime |
| `list_dynamic_tools` | List all agent-created tools |
| `delete_tool` | Remove a dynamic tool from memory + disk |

Plus everything from the GitHub and Brave Search MCP servers.

## Notes

- The agent can only access the folders you define in `config.py` — nothing outside them
- Conversation history is saved in `memory/history.json` so it remembers between sessions
- Agent-created tools are saved in `mcp_server/dynamic_tools/` — one `.py` + one `.json` per tool
- You can ask the agent to delete broken or duplicate tools and it will clean them up itself
- Run `clear history` inside the session to reset memory
- Servers are loaded from `mcp.json` at startup — add new MCP servers there without touching any code

---

*Committed by Agent 47*
