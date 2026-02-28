# tools/definitions.py
# ─────────────────────────────────────────────────────────
# CONCEPT: Tool schemas.
#
# Claude is a language model — it can't see your Python code.
# Instead, you describe your tools in JSON Schema format.
# Claude reads these descriptions and decides which tool to call
# and what arguments to pass.
#
# Think of this as an API contract between you and Claude.
# The better your descriptions, the smarter Claude's decisions.
# ─────────────────────────────────────────────────────────

TOOL_DEFINITIONS = [
    {
        "name": "list_files",
        "description": (
            "List all files and subfolders inside a given folder. "
            "Use this to explore the workspace before making changes."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "folder": {
                    "type": "string",
                    "description": "Relative path from workspace root. Use '' for the root itself."
                }
            },
            "required": ["folder"]
        }
    },
    {
        "name": "delete_file",
        "description": "Delete a single file or an entire folder (including all its contents).",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Relative path to the file or folder to delete."
                }
            },
            "required": ["file_path"]
        }
    },
    {
        "name": "delete_folder_contents",
        "description": (
            "Delete everything INSIDE a folder (all files and subfolders), "
            "but keep the folder itself. Use this when the user says 'clear' or "
            "'empty' a folder."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "folder": {
                    "type": "string",
                    "description": "Relative path to the folder to empty."
                }
            },
            "required": ["folder"]
        }
    },
    {
        "name": "create_folder",
        "description": "Create a new folder. Can create nested folders in one call.",
        "input_schema": {
            "type": "object",
            "properties": {
                "folder_path": {
                    "type": "string",
                    "description": "Relative path of the folder to create (e.g. 'archive/2024')."
                }
            },
            "required": ["folder_path"]
        }
    },
    {
        "name": "move_file",
        "description": "Move a file or folder to a new location within the workspace.",
        "input_schema": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "Relative path of the item to move."
                },
                "destination": {
                    "type": "string",
                    "description": "Relative path of the destination."
                }
            },
            "required": ["source", "destination"]
        }
    },
    {
        "name": "rename_file",
        "description": "Rename a file or folder.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to the file or folder."
                },
                "new_name": {
                    "type": "string",
                    "description": "The new name (just the name, not the full path)."
                }
            },
            "required": ["path", "new_name"]
        }
    },
    {
        "name": "find_files",
        "description": "Search recursively for files matching a glob pattern (e.g. '*.pdf', 'report_*').",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern to match (e.g. '*.png', 'invoice*')."
                },
                "folder": {
                    "type": "string",
                    "description": "Subfolder to search in. Default is workspace root.",
                    "default": ""
                }
            },
            "required": ["pattern"]
        }
    },
    {
        "name": "open_file",
        "description": "Open a file using the system's default application.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Relative path to the file to open."
                }
            },
            "required": ["file_path"]
        }
    }
    
]