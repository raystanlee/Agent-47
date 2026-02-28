# tools/handlers.py
# ─────────────────────────────────────────────────────────
# CONCEPT: Tool handlers.
#
# Each function here is a "tool" the agent can call.
# Claude doesn't run these — YOUR code runs them.
# Claude simply decides WHICH tool to call and with WHAT args.
# Your agent loop then executes the matching function and
# sends the result back to Claude.
#
# This is the key insight of tool use:
#   LLM decides → Python executes → result goes back to LLM
# ─────────────────────────────────────────────────────────

import shutil
import subprocess
from pathlib import Path
from safety.sandbox import safe_path



def open_file(file_path: str) -> str:
    """Open a file using macOS default app (like double-clicking in Finder)."""
    p = safe_path(file_path)
    if not p.exists():
        return f"'{file_path}' does not exist."
    subprocess.run(["open", str(p)])
    return f"Opened '{file_path}' in its default application."

def list_files(folder: str) -> str:
    """List everything inside a folder."""
    p = safe_path(folder)
    if not p.exists():
        return f"Folder '{folder}' does not exist."
    if not p.is_dir():
        return f"'{folder}' is a file, not a folder."

    items = sorted(p.iterdir(), key=lambda x: (x.is_file(), x.name))
    if not items:
        return f"'{folder}' is empty."

    lines = []
    for item in items:
        icon = "📁" if item.is_dir() else "📄"
        size = f"  ({item.stat().st_size:,} bytes)" if item.is_file() else ""
        lines.append(f"{icon} {item.name}{size}")

    return f"Contents of '{folder}':\n" + "\n".join(lines)


def delete_file(file_path: str) -> str:
    """Delete a single file or an entire folder."""
    p = safe_path(file_path)
    if not p.exists():
        return f"Nothing found at '{file_path}'."
    if p.is_dir():
        shutil.rmtree(p)
        return f"Deleted folder '{file_path}' and all its contents."
    p.unlink()
    return f"Deleted file '{file_path}'."


def delete_folder_contents(folder: str) -> str:
    """Delete everything INSIDE a folder, but keep the folder itself."""
    p = safe_path(folder)
    if not p.exists():
        return f"Folder '{folder}' does not exist."
    if not p.is_dir():
        return f"'{folder}' is a file, not a folder."

    deleted = []
    for item in p.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()
        deleted.append(item.name)

    if not deleted:
        return f"'{folder}' was already empty."
    return f"Cleared '{folder}'. Deleted: {', '.join(deleted)}"


def create_folder(folder_path: str) -> str:
    """Create a new folder (including any missing parent folders)."""
    p = safe_path(folder_path)
    if p.exists():
        return f"'{folder_path}' already exists."
    p.mkdir(parents=True)
    return f"Created folder '{folder_path}'."


def move_file(source: str, destination: str) -> str:
    """Move a file or folder from source to destination."""
    src = safe_path(source)
    dst = safe_path(destination)
    if not src.exists():
        return f"Source '{source}' does not exist."
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    return f"Moved '{source}' → '{destination}'."


def rename_file(path: str, new_name: str) -> str:
    """Rename a file or folder."""
    p = safe_path(path)
    if not p.exists():
        return f"'{path}' does not exist."
    new_p = p.parent / new_name
    p.rename(new_p)
    return f"Renamed '{p.name}' → '{new_name}'."


def find_files(pattern: str, folder: str = "") -> str:
    """Search recursively for files matching a glob pattern like '*.pdf'."""
    base = safe_path(folder)
    matches = [
        str(f.relative_to(base.parent if folder == "" else base.parent.parent))
        for f in base.rglob(pattern)
    ]
    if not matches:
        return f"No files matching '{pattern}' found in '{folder or 'workspace'}'."
    return f"Found {len(matches)} match(es):\n" + "\n".join(matches)