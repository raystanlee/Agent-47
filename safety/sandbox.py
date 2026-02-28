
# safety/sandbox.py
# ─────────────────────────────────────────────────────────
# CONCEPT: Sandboxing an agent.
#
# An AI agent will do exactly what you tell it. That means if
# you give it file system access, it could (if not constrained)
# delete your entire home folder. The sandbox is a hard wall.
#
# How it works:
#   resolve() turns any path into its true absolute form.
#   e.g. "../../etc/passwd" resolves to "/etc/passwd"
#   Then we check: does this resolved path START with our safe root?
#   If not → blocked, no matter how the agent tried to get there.
# ─────────────────────────────────────────────────────────

from pathlib import Path
from config import SAFE_ROOT


def safe_path(relative: str) -> Path:
    """
    Takes a relative path string from Claude (e.g. "reports/q1")
    and returns a fully resolved absolute Path — but ONLY if it
    stays inside SAFE_ROOT. Raises an exception otherwise.
    """
    # Join with the safe root, then resolve to absolute real path
    resolved = (SAFE_ROOT / relative).resolve()

    try:
        # This line raises ValueError if resolved is NOT under SAFE_ROOT
        resolved.relative_to(SAFE_ROOT.resolve())
    except ValueError:
        raise PermissionError(
            f"🚫 Blocked: '{relative}' resolves outside the safe workspace.\n"
            f"   Resolved to: {resolved}\n"
            f"   Safe root:   {SAFE_ROOT}"
        )

    return resolved


def ensure_workspace_exists():
    """Create the workspace folder if it doesn't exist yet."""
    SAFE_ROOT.mkdir(parents=True, exist_ok=True)
    print(f"📂 Workspace ready: {SAFE_ROOT}")