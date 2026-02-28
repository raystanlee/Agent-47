# tools/__init__.py
# ─────────────────────────────────────────────────────────
# CONCEPT: Tool registry.
#
# This maps tool names (strings Claude sends) to actual
# Python functions. When Claude says "call list_files",
# the agent loop looks up "list_files" here and runs it.
# ─────────────────────────────────────────────────────────

from tools.handlers import (
    list_files, delete_file, delete_folder_contents,
    create_folder, move_file, rename_file, find_files, open_file
)
from tools.definitions import TOOL_DEFINITIONS

TOOL_REGISTRY = {
    "list_files":            list_files,
    "delete_file":           delete_file,
    "delete_folder_contents": delete_folder_contents,
    "create_folder":         create_folder,
    "move_file":             move_file,
    "rename_file":           rename_file,
    "find_files":            find_files,
    "open_file":             open_file, # New tool added to registry
}