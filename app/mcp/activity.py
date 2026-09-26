from collections import deque
from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4


_MAX_EVENTS = 100

_events = deque(maxlen=_MAX_EVENTS)
_lock = Lock()


def record_mcp_activity(
    tool: str,
    status: str,
    repository_id: str | None = None,
    message: str | None = None,
    duration_ms: int | None = None,
) -> None:
    event = {
        "id": uuid4().hex,
        "tool": tool,
        "status": status,
        "repository_id": repository_id,
        "message": message,
        "duration_ms": duration_ms,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    with _lock:
        _events.appendleft(event)


def get_mcp_activity() -> list[dict]:
    with _lock:
        return list(_events)