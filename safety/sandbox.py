
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
# safety/sandbox.py
# ─────────────────────────────────────────────────────────
# Now supports multiple safe roots.
# A path is allowed if it falls under ANY of the SAFE_ROOTS.
# ─────────────────────────────────────────────────────────

from pathlib import Path
from config import SAFE_ROOTS


def safe_path(relative: str) -> Path:
    """
    Resolve a path string and verify it sits under one of the
    allowed roots. Raises PermissionError if not.

    Accepts either:
      - A relative path like "README.md" (resolved against each root)
      - An absolute path like "/Users/ray/Agent 47/README.md"
    """
    candidate = Path(relative).expanduser()

    # If absolute, check it directly against all roots
    if candidate.is_absolute():
        resolved = candidate.resolve()
        for root in SAFE_ROOTS:
            try:
                resolved.relative_to(root)
                return resolved
            except ValueError:
                continue
        raise PermissionError(
            f"🚫 Blocked: '{relative}' is outside all allowed roots.\n"
            f"   Allowed: {[str(r) for r in SAFE_ROOTS]}"
        )

    # If relative, try resolving under each root
    for root in SAFE_ROOTS:
        resolved = (root / relative).resolve()
        try:
            resolved.relative_to(root)
            return resolved
        except ValueError:
            continue

    raise PermissionError(
        f"🚫 Blocked: '{relative}' could not be resolved under any allowed root.\n"
        f"   Allowed: {[str(r) for r in SAFE_ROOTS]}"
    )


def ensure_workspace_exists():
    """Create all workspace roots if they don't exist."""
    for root in SAFE_ROOTS:
        root.mkdir(parents=True, exist_ok=True)
    print(f"📂 Workspaces ready: {[str(r) for r in SAFE_ROOTS]}")