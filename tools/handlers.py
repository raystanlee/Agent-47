# tools/handlers.py

import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from safety.sandbox import safe_path
from config import SAFE_ROOTS


def list_files(folder: str) -> str:
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


def git_diff_stat(repo_path: str) -> str:
    p = safe_path(repo_path)
    if not p.exists():
        return f"Path '{repo_path}' does not exist."
    result = subprocess.run(
        ["git", "diff", "--stat"],
        cwd=str(p), capture_output=True, text=True
    )
    output = result.stdout or result.stderr
    return output if output.strip() else "No differences found."


def read_file(file_path: str, max_chars: int = 8000) -> str:
    p = safe_path(file_path)
    if not p.exists():
        return f"'{file_path}' does not exist."
    if not p.is_file():
        return f"'{file_path}' is a folder, not a file."
    try:
        content = p.read_text(encoding="utf-8")
        if len(content) > max_chars:
            return (
                content[:max_chars] +
                f"\n\n[File truncated — {len(content):,} chars total, showing first {max_chars:,}. "
                f"Use execute_python with pandas to analyze large files.]"
            )
        return content
    except UnicodeDecodeError:
        return f"'{file_path}' is a binary file and cannot be read as text."


def write_file(file_path: str, content: str) -> str:
    p = safe_path(file_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"Written to '{file_path}' ({len(content):,} chars)."


def delete_file(file_path: str) -> str:
    p = safe_path(file_path)
    if not p.exists():
        return f"Nothing found at '{file_path}'."
    if p.is_dir():
        shutil.rmtree(p)
        return f"Deleted folder '{file_path}' and all its contents."
    p.unlink()
    return f"Deleted file '{file_path}'."


def delete_folder_contents(folder: str) -> str:
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
    p = safe_path(folder_path)
    if p.exists():
        return f"'{folder_path}' already exists."
    p.mkdir(parents=True)
    return f"Created folder '{folder_path}'."


def move_file(source: str, destination: str) -> str:
    src = safe_path(source)
    dst = safe_path(destination)
    if not src.exists():
        return f"Source '{source}' does not exist."
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    return f"Moved '{source}' → '{destination}'."


def rename_file(path: str, new_name: str) -> str:
    p = safe_path(path)
    if not p.exists():
        return f"'{path}' does not exist."
    new_p = p.parent / new_name
    p.rename(new_p)
    return f"Renamed '{p.name}' → '{new_name}'."


def find_files(pattern: str, folder: str = "") -> str:
    if folder:
        base = safe_path(folder)
        matches = [str(f) for f in base.rglob(pattern)]
    else:
        # Search ALL safe roots when no folder specified
        matches = []
        for root in SAFE_ROOTS:
            matches.extend([str(f) for f in root.rglob(pattern)])
    
    if not matches:
        return f"No files matching '{pattern}' found."
    return f"Found {len(matches)} match(es):\n" + "\n".join(matches)


def open_file(file_path: str) -> str:
    p = safe_path(file_path)
    if not p.exists():
        return f"'{file_path}' does not exist."
    subprocess.run(["open", str(p)])
    return f"Opened '{file_path}' in its default application."


def git_status(repo_path: str) -> str:
    p = safe_path(repo_path)
    if not p.exists():
        return f"Path '{repo_path}' does not exist."
    result = subprocess.run(
        ["git", "status"],
        cwd=str(p), capture_output=True, text=True
    )
    return result.stdout or result.stderr


def git_diff(repo_path: str, staged: bool = False) -> str:
    p = safe_path(repo_path)
    if not p.exists():
        return f"Path '{repo_path}' does not exist."
    cmd = ["git", "diff"]
    if staged:
        cmd.append("--staged")
    result = subprocess.run(
        cmd, cwd=str(p), capture_output=True, text=True
    )
    output = result.stdout or result.stderr
    return output if output.strip() else "No differences found."


# ── Code Execution ─────────────────────────────────────────────────────────────
# CONCEPT: Why run code in a subprocess instead of exec()?
#
#   exec() runs code in the same Python process as Agent 47.
#   If something goes wrong — infinite loop, memory explosion,
#   bad import — it can crash the entire agent.
#
#   subprocess.run() launches a completely separate Python process.
#   The agent stays alive no matter what the code does.
#   The timeout kills it if it runs too long.
#   stdout/stderr come back as plain strings the agent can read.

# Patterns blocked for safety — checked before execution
BLOCKED_PATTERNS = [
    "os.system",
    "os.popen",
    "os.execv",
    "subprocess",
    "import requests",
    "import urllib",
    "import httpx",
    "import socket",
    "__import__",
    "eval(",
    "compile(",
    " open(",        # force use of safe_path instead
    "shutil.rmtree",
    "os.remove",
    "os.unlink",
]


def execute_python(code: str, working_dir: str = "") -> str:
    """
    Execute a Python code snippet and return its stdout + stderr.

    CONCEPT: How the safety model works
      1. Block dangerous patterns before running anything
      2. Run in a subprocess with a hard timeout
      3. Inject SAFE_ROOTS so the code knows where it can read from
      4. Capture all output and return it as a string to Claude

    Claude reads the output and decides what to do next —
    run more code, interpret results, or report back to you.
    """

    # ── Step 1: Safety check ───────────────────────────────
    for pattern in BLOCKED_PATTERNS:
        if pattern in code:
            return (
                f"❌ Blocked: code contains '{pattern}' which is not allowed.\n"
                f"Use safe_path() for file access. Network calls are not permitted."
            )

    # ── Step 2: Determine working directory ───────────────
    # Default to first SAFE_ROOT if none specified
    if working_dir:
        try:
            cwd = safe_path(working_dir)
        except PermissionError as e:
            return str(e)
    else:
        cwd = SAFE_ROOTS[0]

    # ── Step 3: Inject context into the code ──────────────
    # Prepend SAFE_ROOTS so the code can reference allowed paths
    # without hardcoding them. Claude's generated code can use
    # SAFE_ROOTS[0] to find the workspace automatically.
    safe_roots_repr = repr([str(r) for r in SAFE_ROOTS])
    preamble = textwrap.dedent(f"""
        from pathlib import Path
        SAFE_ROOTS = [Path(p) for p in {safe_roots_repr}]
        WORKSPACE  = SAFE_ROOTS[0]
    """)
    full_code = preamble + "\n" + code

    # ── Step 4: Run in subprocess with timeout ─────────────
    try:
        result = subprocess.run(
            [sys.executable, "-c", full_code],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=15,          # kill after 15 seconds
        )

        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += f"\n[stderr]\n{result.stderr}"

        # Truncate very long outputs so they don't flood Claude's context
        if len(output) > 4000:
            output = output[:4000] + "\n\n[output truncated — too long]"

        return output.strip() if output.strip() else "(no output)"

    except subprocess.TimeoutExpired:
        return "❌ Execution timed out after 15 seconds."
    except Exception as e:
        return f"❌ Execution error: {e}"