# Agent 47 — My PC AI Agent

An AI agent that manages files on your computer using natural language. Built as a learning project to understand how agentic AI works.

## What it does

You tell it what to do in plain English and it figures out the steps. Things like:

- "Delete all files in the temp folder"
- "Open the largest image"
- "Move all PDFs to the archive folder"
- "Show me what's in the reports folder" , etce

## How it works

The agent uses Claude as the brain (planner and ochestrator). You give it an instruction, Claude decides which tools to call and in what order, and Python executes the actual file operations. Claude never touches your file system directly it just plans, your code acts.

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

## Project structure

```
Agent 47/
├── main.py          # Entry point
├── config.py        # Settings
├── agent/
│   └── loop.py      # The agentic loop
├── tools/
│   ├── handlers.py  # What each tool actually does
│   └── definitions.py # Tool descriptions Claude reads
├── safety/
│   └── sandbox.py   # Keeps the agent inside the workspace
└── memory/
    └── history.py   # Saves conversation between sessions
```

## Notes

- The agent can only access the folder you define in `config.py` — nothing outside it
- Conversation history is saved in `memory/history.json` so it remembers between sessions
- Run `clear history` inside the session to reset memory