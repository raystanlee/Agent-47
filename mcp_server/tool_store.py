# mcp_server/tool_store.py
# ─────────────────────────────────────────────────────────
# Persistence layer for dynamic tools.
# Handles saving, loading, listing, and deleting tools on disk.
# ─────────────────────────────────────────────────────────

import json
from pathlib import Path

DYNAMIC_TOOLS_DIR = Path(__file__).parent / "dynamic_tools"


def ensure_store_exists():
    """Create the dynamic_tools folder and __init__.py if missing."""
    DYNAMIC_TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    init = DYNAMIC_TOOLS_DIR / "__init__.py"
    if not init.exists():
        init.write_text("# Auto-generated\n")


def save_tool(name: str, description: str, python_code: str, input_schema: dict) -> bool:
    """
    Save a dynamic tool to disk as two files:
      - {name}.py   → the Python function code
      - {name}.json → the MCP schema (name, description, inputSchema)
    Returns True on success, False on failure.
    """
    ensure_store_exists()
    try:
        (DYNAMIC_TOOLS_DIR / f"{name}.py").write_text(python_code)
        meta = {"name": name, "description": description, "inputSchema": input_schema}
        (DYNAMIC_TOOLS_DIR / f"{name}.json").write_text(json.dumps(meta, indent=2))
        return True
    except Exception as e:
        print(f"[tool_store] Failed to save '{name}': {e}")
        return False


def delete_tool_from_disk(name: str) -> tuple[bool, str]:
    """
    Delete a dynamic tool's files from disk.

    Returns a tuple:
      (True, success message)   if deleted
      (False, reason message)   if not found or failed

    CONCEPT: Why a tuple instead of just bool?
      The caller (server.py) needs to tell Claude what happened.
      A bool alone doesn't give enough information to form a
      useful message. Returning (success, message) keeps the
      logic here and lets the caller just pass the message through.
    """
    ensure_store_exists()

    py_file   = DYNAMIC_TOOLS_DIR / f"{name}.py"
    json_file = DYNAMIC_TOOLS_DIR / f"{name}.json"

    # Check if either file exists at all
    if not py_file.exists() and not json_file.exists():
        return False, f"No dynamic tool named '{name}' found on disk."

    # Delete whatever exists (handle partial saves gracefully)
    deleted = []
    try:
        if py_file.exists():
            py_file.unlink()
            deleted.append(f"{name}.py")
        if json_file.exists():
            json_file.unlink()
            deleted.append(f"{name}.json")
        return True, f"Deleted from disk: {', '.join(deleted)}"
    except Exception as e:
        return False, f"Failed to delete '{name}' from disk: {e}"


def load_all_tools() -> list[dict]:
    """
    Load all saved dynamic tools from disk.
    Called once at server startup.

    For each .json file found, looks for a matching .py file,
    exec()s it, and returns a list of dicts with:
      - "meta": the MCP schema dict
      - "func": the live callable function
    """
    ensure_store_exists()
    tools = []

    for meta_file in DYNAMIC_TOOLS_DIR.glob("*.json"):
        name    = meta_file.stem
        py_file = DYNAMIC_TOOLS_DIR / f"{name}.py"

        if not py_file.exists():
            print(f"[tool_store] Warning: {name}.json has no matching .py — skipping")
            continue

        try:
            meta      = json.loads(meta_file.read_text())
            code      = py_file.read_text()
            namespace = {}
            exec(code, namespace)
            func = namespace.get(name)

            if func is None:
                print(f"[tool_store] Warning: {name}.py has no function named '{name}' — skipping")
                continue

            tools.append({"meta": meta, "func": func})
            print(f"[tool_store] Loaded: {name}")

        except Exception as e:
            print(f"[tool_store] Failed to load '{name}': {e}")

    return tools


def list_saved_tool_names() -> list[str]:
    """Return names of all tools currently saved to disk."""
    ensure_store_exists()
    return [f.stem for f in DYNAMIC_TOOLS_DIR.glob("*.json")]