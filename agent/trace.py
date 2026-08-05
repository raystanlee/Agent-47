# agent/trace.py
# ─────────────────────────────────────────────────────────
# CONCEPT: In-process live trace stream.
#
# The agent loop already narrates itself to the terminal via
# agent/pretty.py. This module adds a *second* listener: each
# step is also emitted as a structured event onto an in-memory
# bus, streamed to a browser over SSE and drawn as a live
# timeline. Terminal output is unchanged — this is purely additive.
#
# It runs as a background task on the agent's existing asyncio
# loop (no extra process), so it covers both CLI and Telegram
# turns, which share the same run_async().
#
# WHY SSE and not websockets: the flow is one-way (agent → UI)
# and SSE auto-reconnects in the browser for free. WHY a ring
# buffer: a tab opened mid-run should show recent context, not
# a blank screen until the next event.
# ─────────────────────────────────────────────────────────

import asyncio
import itertools
import json
import time
from collections import deque
from pathlib import Path

from starlette.applications import Starlette
from starlette.responses import FileResponse
from starlette.routing import Route
from sse_starlette.sse import EventSourceResponse

_UI_FILE = Path(__file__).parent / "trace_ui.html"

# One asyncio.Queue per connected browser.
_subscribers: set[asyncio.Queue] = set()

# Full session history (bounded) so a reloaded tab rebuilds the WHOLE session,
# not just the current turn. ~5000 events ≈ hundreds of turns; oldest drop past
# the cap. Resets when the process restarts — matching the UsageTracker's lifetime.
BUFFER_MAX = 5000
_buffer: deque = deque(maxlen=BUFFER_MAX)

_seq = itertools.count(1)
_turn = itertools.count(1)


def emit(kind: str, **data) -> None:
    """Push a structured event to every connected browser.

    Safe to call from anywhere inside the agent's event loop. Delivery
    is non-blocking on purpose: a slow or stuck browser is dropped for
    that event rather than ever stalling the agent.
    """
    event = {"seq": next(_seq), "t": time.time(), "kind": kind, **data}
    _buffer.append(event)
    for q in list(_subscribers):
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            pass  # this browser can't keep up; skip it, never block the agent


def reset() -> None:
    """Signal a hard clear of the UI timeline (manual/debug use)."""
    emit("reset")


def start_turn() -> None:
    """Mark the start of a new turn so the UI opens a new section in the log.

    Unlike reset(), this does NOT wipe earlier turns — the session log stays
    stacked and scrollable, and each turn gets its own divider and cost.
    """
    emit("turn", n=next(_turn))


def trim_result(result, limit: int = 2000) -> str:
    """Shrink a tool result for the wire: hide base64 image blobs, cap length.

    Mirrors the suppression print_tool_result already does for the terminal,
    so a captured frame doesn't flood the trace with megabytes of base64.
    """
    if not isinstance(result, str):
        result = str(result)
    try:
        parsed = json.loads(result)
        if isinstance(parsed, dict) and "image" in parsed:
            parsed = {
                k: (f"<base64 {len(v)} chars>" if k == "image" and isinstance(v, str) else v)
                for k, v in parsed.items()
            }
            result = json.dumps(parsed)
    except (json.JSONDecodeError, TypeError):
        pass
    if len(result) > limit:
        result = result[:limit] + f"… (+{len(result) - limit} more chars)"
    return result


async def _events(request):
    q: asyncio.Queue = asyncio.Queue(maxsize=BUFFER_MAX + 1000)
    for event in list(_buffer):  # replay full session history first
        q.put_nowait(event)
    _subscribers.add(q)

    async def gen():
        try:
            while True:
                event = await q.get()
                yield {"data": json.dumps(event, default=str)}
        finally:
            _subscribers.discard(q)

    return EventSourceResponse(gen())


async def _index(request):
    return FileResponse(_UI_FILE)


_app = Starlette(routes=[
    Route("/", _index),
    Route("/events", _events),
])


def launch_trace_server(port: int = 8770) -> asyncio.Task:
    """Start the trace UI as a background task on the current event loop.

    Returns the task. Startup failures (e.g. port already in use) are
    reported but never crash the agent — the trace UI is a convenience,
    not a critical path. Must be called from within a running loop.
    """
    async def _serve():
        import uvicorn
        config = uvicorn.Config(_app, host="127.0.0.1", port=port, log_level="warning")
        server = uvicorn.Server(config)
        # Don't let uvicorn hijack SIGINT/SIGTERM — main.py owns Ctrl-C.
        server.install_signal_handlers = lambda: None
        try:
            await server.serve()
        except Exception as e:  # noqa: BLE001 - convenience feature, degrade gracefully
            print(f"⚠️  Trace UI failed to start on :{port} ({e})")

    return asyncio.create_task(_serve())
