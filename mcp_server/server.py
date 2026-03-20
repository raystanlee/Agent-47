# mcp_server/server.py
# ─────────────────────────────────────────────────────────
# The MCP server.
# Includes two meta-tools:
#   list_dynamic_tools  → show all runtime-created tools
#   delete_tool         → remove a dynamic tool from memory + disk
# ─────────────────────────────────────────────────────────

import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

from tools.handlers import (
    list_files, delete_file, delete_folder_contents,
    create_folder, move_file, rename_file, find_files, open_file,
    git_status, git_diff, git_diff_stat,
)
from mcp_server.tool_store import (
    save_tool, load_all_tools,
    delete_tool_from_disk, list_saved_tool_names
)

# ── Registries ────────────────────────────────────────────
STATIC_HANDLERS = {
    "list_files":             list_files,
    "delete_file":            delete_file,
    "delete_folder_contents": delete_folder_contents,
    "create_folder":          create_folder,
    "move_file":              move_file,
    "rename_file":            rename_file,
    "find_files":             find_files,
    "open_file":              open_file,
    "git_diff_stat": git_diff_stat,
}

# Populated at startup from disk, and grows as create_tool is called
DYNAMIC_HANDLERS: dict = {}
DYNAMIC_SCHEMAS:  list = []


def load_dynamic_tools():
    """Load all previously saved dynamic tools into memory at startup."""
    tools = load_all_tools()
    for t in tools:
        name = t["meta"]["name"]
        DYNAMIC_HANDLERS[name] = t["func"]
        DYNAMIC_SCHEMAS.append(t["meta"])


server = Server("agent-47")


# ── Tool Discovery ─────────────────────────────────────────
@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """Return all available tools: static + meta-tools + dynamic."""

    static = [
        types.Tool(
            name="list_files",
            description="List all files and subfolders inside a given folder.",
            inputSchema={
                "type": "object",
                "properties": {
                    "folder": {"type": "string", "description": "Relative path from workspace root. Use '' for root."}
                },
                "required": ["folder"]
            }
        ),
        types.Tool(
            name="delete_file",
            description="Delete a single file or an entire folder (including all its contents).",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Relative path to the file or folder to delete."}
                },
                "required": ["file_path"]
            }
        ),
        types.Tool(
            name="delete_folder_contents",
            description="Delete everything INSIDE a folder but keep the folder itself.",
            inputSchema={
                "type": "object",
                "properties": {
                    "folder": {"type": "string", "description": "Relative path to the folder to empty."}
                },
                "required": ["folder"]
            }
        ),
        types.Tool(
            name="create_folder",
            description="Create a new folder. Can create nested folders in one call.",
            inputSchema={
                "type": "object",
                "properties": {
                    "folder_path": {"type": "string", "description": "Relative path of the folder to create."}
                },
                "required": ["folder_path"]
            }
        ),
        types.Tool(
            name="move_file",
            description="Move a file or folder to a new location within the workspace.",
            inputSchema={
                "type": "object",
                "properties": {
                    "source":      {"type": "string", "description": "Relative path of the item to move."},
                    "destination": {"type": "string", "description": "Relative path of the destination."}
                },
                "required": ["source", "destination"]
            }
        ),
        types.Tool(
            name="rename_file",
            description="Rename a file or folder.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path":     {"type": "string", "description": "Relative path to the file or folder."},
                    "new_name": {"type": "string", "description": "The new name (not the full path)."}
                },
                "required": ["path", "new_name"]
            }
        ),
        types.Tool(
            name="find_files",
            description="Search recursively for files matching a glob pattern.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Glob pattern to match (e.g. '*.pdf')."},
                    "folder":  {"type": "string", "description": "Subfolder to search in. Default is workspace root.", "default": ""}
                },
                "required": ["pattern"]
            }
        ),
        types.Tool(
            name="open_file",
            description="Open a file using the system's default application.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Relative path to the file to open."}
                },
                "required": ["file_path"]
            }
        ),

        types.Tool(
            name="read_file",
            description="Read and return the full text contents of a file.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Absolute or relative path to the file."}
                },
                "required": ["file_path"]
            }
        ),
        types.Tool(
            name="write_file",
            description="Write content to a file. Creates the file if it doesn't exist, overwrites if it does.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Absolute or relative path to the file."},
                    "content":   {"type": "string", "description": "Full content to write to the file."}
                },
                "required": ["file_path", "content"]
            }
        ),
        types.Tool(
            name="git_status",
            description="Run git status in a repository folder to see changed, staged, and untracked files.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string", "description": "Absolute or relative path to the git repo root."}
                },
                "required": ["repo_path"]
            }
        ),
        types.Tool(
            name="git_diff",
            description="Show git diff for a repository. Use staged=true to see staged changes, false for unstaged.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string", "description": "Absolute or relative path to the git repo root."},
                    "staged":    {"type": "boolean", "description": "If true, shows staged diff. Default false.", "default": False}
                },
                "required": ["repo_path"]
            }
        ),
        types.Tool(
            name="git_diff_stat",
            description="Run git diff --stat to get a compact summary of what changed — filenames and line counts only. Use this before git_diff to decide which files actually need a full diff.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string", "description": "Absolute or relative path to the git repo root."}
                },
                "required": ["repo_path"]
            }
        ),

        # ── Meta-tools ────────────────────────────────────
        types.Tool(
            name="create_tool",
            description=(
                "Create a brand-new tool and register it immediately. "
                "Use this when asked to do something and no suitable tool exists. "
                "The tool will be saved to disk and available in future sessions."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Snake_case name for the tool, e.g. 'read_file'."
                    },
                    "description": {
                        "type": "string",
                        "description": "What this tool does. Be specific."
                    },
                    "python_code": {
                        "type": "string",
                        "description": (
                            "A complete Python function with the same name as 'name'. "
                            "Must be self-contained: import anything it needs inside the function. "
                            "Use safe_path from safety.sandbox for any file access. "
                            "Always return a string."
                        )
                    },
                    "input_schema": {
                        "type": "object",
                        "description": "JSON Schema object describing the function's parameters."
                    }
                },
                "required": ["name", "description", "python_code", "input_schema"]
            }
        ),

        types.Tool(
            name="list_dynamic_tools",
            description=(
                "List all tools that have been dynamically created at runtime. "
                "Use this to check what tools already exist before creating a new one, "
                "or to review tools that can be deleted."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),

        types.Tool(
            name="delete_tool",
            description=(
                "Permanently delete a dynamic tool from memory and disk. "
                "Use this to remove tools that failed, are duplicates, or are no longer needed. "
                "Cannot delete static (built-in) tools."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Exact name of the dynamic tool to delete."
                    }
                },
                "required": ["name"]
            }
        ),
    ]

    # Append dynamic tool schemas so Claude knows they exist
    dynamic = [
        types.Tool(
            name=t["name"],
            description=t["description"],
            inputSchema=t["inputSchema"]
        )
        for t in DYNAMIC_SCHEMAS
    ]

    return static + dynamic


# ── Tool Execution ─────────────────────────────────────────
@server.call_tool()
async def call_tool(tool_name: str, arguments: dict) -> list[types.TextContent]:

    # ── create_tool ───────────────────────────────────────
    if tool_name == "create_tool":
        name         = arguments["name"]
        description  = arguments["description"]
        python_code  = arguments["python_code"]
        input_schema = arguments["input_schema"]

        if name in STATIC_HANDLERS:
            return [types.TextContent(type="text",
                text=f"Cannot create '{name}' — a built-in tool with that name already exists.")]

        saved = save_tool(name, description, python_code, input_schema)
        if not saved:
            return [types.TextContent(type="text", text=f"Failed to save '{name}' to disk.")]

        namespace = {}
        try:
            exec(python_code, namespace)
            func = namespace.get(name)
            if func is None:
                return [types.TextContent(type="text",
                    text=f"Code saved but no function named '{name}' found in it.")]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Code error: {e}")]

        DYNAMIC_HANDLERS[name] = func
        DYNAMIC_SCHEMAS.append({
            "name": name,
            "description": description,
            "inputSchema": input_schema
        })

        return [types.TextContent(type="text",
            text=f"Tool '{name}' created and registered. You can call it right now.")]

    # ── list_dynamic_tools ────────────────────────────────
    if tool_name == "list_dynamic_tools":
        names = list_saved_tool_names()
        if not names:
            return [types.TextContent(type="text", text="No dynamic tools exist yet.")]
        lines = "\n".join(f"  • {n}" for n in sorted(names))
        return [types.TextContent(type="text", text=f"Dynamic tools ({len(names)}):\n{lines}")]

    # ── delete_tool ───────────────────────────────────────
    if tool_name == "delete_tool":
        name = arguments["name"]

        if name in STATIC_HANDLERS:
            return [types.TextContent(type="text",
                text=f"'{name}' is a built-in tool and cannot be deleted.")]

        success, msg = delete_tool_from_disk(name)
        if not success:
            return [types.TextContent(type="text", text=msg)]

        DYNAMIC_HANDLERS.pop(name, None)
        # Mutate in place instead of reassigning — avoids the global/scoping issue
        DYNAMIC_SCHEMAS[:] = [t for t in DYNAMIC_SCHEMAS if t["name"] != name]

        return [types.TextContent(type="text",
            text=f"Tool '{name}' deleted from memory and disk.")]

    # ── Static tools ───────────────────────────────────────
    handler = STATIC_HANDLERS.get(tool_name)
    if handler:
        try:
            result = handler(**arguments)
        except PermissionError as e:
            result = f"Permission denied: {e}"
        except Exception as e:
            result = f"Error: {e}"
        return [types.TextContent(type="text", text=str(result))]

    # ── Dynamic tools ──────────────────────────────────────
    handler = DYNAMIC_HANDLERS.get(tool_name)
    if handler:
        try:
            result = handler(**arguments)
        except Exception as e:
            result = f"Error running '{tool_name}': {e}"
        return [types.TextContent(type="text", text=str(result))]

    # ── Unknown ────────────────────────────────────────────
    return [types.TextContent(type="text", text=f"Unknown tool: {tool_name}")]


# ── Entry Point ────────────────────────────────────────────
async def main():
    load_dynamic_tools()
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())