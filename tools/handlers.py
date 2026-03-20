# tools/handlers.py

import shutil
import subprocess
from pathlib import Path
from safety.sandbox import safe_path


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
    """Run git diff --stat to get a summary of changed files and line counts."""
    p = safe_path(repo_path)
    if not p.exists():
        return f"Path '{repo_path}' does not exist."
    result = subprocess.run(
        ["git", "diff", "--stat"],
        cwd=str(p),
        capture_output=True,
        text=True
    )
    output = result.stdout or result.stderr
    return output if output.strip() else "No differences found."

def read_file(file_path: str) -> str:
    """Read and return the contents of a text file."""
    p = safe_path(file_path)
    if not p.exists():
        return f"'{file_path}' does not exist."
    if not p.is_file():
        return f"'{file_path}' is a folder, not a file."
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return f"'{file_path}' is a binary file and cannot be read as text."


def write_file(file_path: str, content: str) -> str:
    """Write content to a file, creating it if it doesn't exist."""
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
    base = safe_path(folder) if folder else safe_path(".")
    matches = [str(f) for f in base.rglob(pattern)]
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
    """Run git status in a repo folder."""
    p = safe_path(repo_path)
    if not p.exists():
        return f"Path '{repo_path}' does not exist."
    result = subprocess.run(
        ["git", "status"],
        cwd=str(p),
        capture_output=True,
        text=True
    )
    return result.stdout or result.stderr


def git_diff(repo_path: str, staged: bool = False) -> str:
    """
    Run git diff in a repo folder.
    staged=True shows changes staged for commit (git diff --staged).
    staged=False shows unstaged working directory changes.
    """
    p = safe_path(repo_path)
    if not p.exists():
        return f"Path '{repo_path}' does not exist."
    cmd = ["git", "diff"]
    if staged:
        cmd.append("--staged")
    result = subprocess.run(
        cmd,
        cwd=str(p),
        capture_output=True,
        text=True
    )
    output = result.stdout or result.stderr
    return output if output.strip() else "No differences found."