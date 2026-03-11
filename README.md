# Agent 47 — My PC AI Agent

An AI agent that manages files on your computer using natural language — and can extend itself by writing its own tools on demand. Built as a learning project to understand how agentic AI and the Model Context Protocol (MCP) work.

## What it does

You tell it what to do in plain English and it figures out the steps. Things like:

- "Delete all files in the temp folder"
- "Open the largest image"
- "Move all PDFs to the archive folder"
- "Show me what's in the reports folder"
- "What is in this image?" ← it will write a vision tool if it doesn't have one

If it needs a capability it doesn't have yet, it writes the tool itself, registers it, and uses it — all in the same turn. Those tools are saved to disk and available on every future run.

## How it works

The agent uses Claude as the brain (planner and orchestrator). You give it an instruction, Claude decides which tools to call and in what order, and Python executes the actual operations. Claude never touches your file system directly — it just plans, your code acts.

Tools are served over **MCP (Model Context Protocol)** — an open standard that separates your agent logic from your tool layer. The MCP server runs as a subprocess and communicates with the agent over stdio. This means the same tool server could plug into Claude Desktop, Cursor, or any other MCP-compatible host.

### The self-extension loop

```
User asks for something
    ↓
Agent checks available tools
    ↓
Tool missing? → calls create_tool → writes Python code → registers it live
    ↓
Calls the new tool immediately
    ↓
Tool saved to disk — available on every future run
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

**3. Add your Anthropic API key:**

Create a `.env` file in the project root:
```
ANTHROPIC_API_KEY=sk-ant-...
```

**4. Set your workspace folder in `config.py`:**
```python
SAFE_ROOT = Path.home() / "YourFolderName"
```

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
├── main.py               # Entry point
├── config.py             # Settings and system prompt
├── agent/
│   ├── loop.py           # The agentic loop (MCP-powered)
│   └── pretty.py         # Coloured terminal output
├── mcp_server/
│   ├── server.py         # The MCP server — exposes all tools
│   ├── tool_store.py     # Saves/loads dynamic tools to disk
│   └── dynamic_tools/    # Agent-created tools live here (auto-generated)
├── tools/
│   ├── handlers.py       # What each built-in tool actually does
│   ├── definitions.py    # Tool schemas (legacy, kept for reference)
│   └── __init__.py       # Tool registry
├── safety/
│   └── sandbox.py        # Keeps the agent inside the workspace
└── memory/
    └── history.py        # Saves conversation between sessions
```

## Notes

- The agent can only access the folder you define in `config.py` — nothing outside it
- Conversation history is saved in `memory/history.json` so it remembers between sessions
- Agent-created tools are saved in `mcp_server/dynamic_tools/` — one `.py` + one `.json` per tool
- You can ask the agent to delete broken or duplicate tools and it will clean them up itself
- Run `clear history` inside the session to reset memory