import datetime as dt
import json
import os
import re
import sys
import threading
from pathlib import Path
from typing import Any


_audit_error_count = 0
_audit_error_lock = threading.Lock()
_BEIJING_TIMEZONE = dt.timezone(dt.timedelta(hours=8), name="Asia/Shanghai")
_SENSITIVE_KEY_PATTERN = re.compile(
    r"(?i)(api[_-]?key|password|token|secret)"
)


def _log_path() -> Path:
    workspace = Path(os.getenv("AGENT_WORKSPACE", Path.cwd())).expanduser().resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace / ".agent_audit.jsonl"


def _fallback_log_path() -> Path | None:
    configured_path = os.getenv("AGENT_AUDIT_FALLBACK_PATH")
    if not configured_path or not configured_path.strip():
        return None
    return Path(configured_path).expanduser().resolve()


def _record_error(error: OSError) -> int:
    global _audit_error_count
    with _audit_error_lock:
        _audit_error_count += 1
        error_count = _audit_error_count
    print(
        f"[AuditLog] WARNING: audit log write failed "
        f"(total {error_count}): "
        f"{type(error).__name__}",
        file=sys.stderr,
    )
    return error_count


def get_audit_error_count() -> int:
    with _audit_error_lock:
        return _audit_error_count


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: (
                "[REDACTED]"
                if isinstance(key, str) and _SENSITIVE_KEY_PATTERN.search(key)
                else _redact(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, str):
        value = re.sub(
            r"(?i)(api[_-]?key|password|token|secret)\s*[:=]\s*\S+",
            r"\1=[REDACTED]",
            value,
        )
        return value[:4000]
    return value


def record(event: str, **details: Any) -> None:
    entry = {
        "timestamp": dt.datetime.now(_BEIJING_TIMEZONE).isoformat(),
        "event": event,
        "details": _redact(details),
    }
    serialized_entry = json.dumps(entry, ensure_ascii=False) + "\n"
    try:
        with _log_path().open("a", encoding="utf-8") as stream:
            stream.write(serialized_entry)
        return
    except OSError as error:
        # Audit logging must not make the agent task fail.
        _record_error(error)

    fallback_path = _fallback_log_path()
    if fallback_path is None:
        return

    try:
        fallback_path.parent.mkdir(parents=True, exist_ok=True)
        with fallback_path.open("a", encoding="utf-8") as stream:
            stream.write(serialized_entry)
    except OSError as error:
        _record_error(error)
