from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass


class AdmissionRejected(RuntimeError):
    """Raised when the Agent concurrency capacity cannot accept a request."""


@dataclass(frozen=True)
class AdmissionLease:
    request_id: str
    wait_seconds: float


class AgentAdmission:
    """Process-local admission control for Agent requests.

    This is the Agent equivalent of a seckill system's rate/capacity gate:
    only a bounded number of model workflows may run at once.
    """

    def __init__(self, max_concurrent: int = 4, queue_timeout: float = 10.0) -> None:
        if max_concurrent < 1:
            raise ValueError("max_concurrent must be positive")
        if queue_timeout < 0:
            raise ValueError("queue_timeout must not be negative")
        self.max_concurrent = max_concurrent
        self.queue_timeout = queue_timeout
        self._slots = threading.BoundedSemaphore(max_concurrent)
        self._lock = threading.Lock()
        self._active = 0
        self._rejected = 0

    def acquire(self, request_id: str | None = None) -> AdmissionLease:
        request_id = request_id or uuid.uuid4().hex
        started = time.monotonic()
        acquired = self._slots.acquire(timeout=self.queue_timeout)
        waited = time.monotonic() - started
        if not acquired:
            with self._lock:
                self._rejected += 1
            raise AdmissionRejected("Agent 当前并发容量已满，请稍后重试")
        with self._lock:
            self._active += 1
        return AdmissionLease(request_id=request_id, wait_seconds=waited)

    def release(self) -> None:
        with self._lock:
            if self._active <= 0:
                raise RuntimeError("Agent admission slot released too many times")
            self._active -= 1
        self._slots.release()

    def stats(self) -> dict[str, int | float]:
        with self._lock:
            active = self._active
            rejected = self._rejected
        return {
            "max_concurrent": self.max_concurrent,
            "active": active,
            "available": self.max_concurrent - active,
            "rejected": rejected,
            "queue_timeout_seconds": self.queue_timeout,
        }

    @classmethod
    def from_environment(cls) -> "AgentAdmission":
        import os

        max_concurrent = int(os.getenv("AGENT_MAX_CONCURRENT", "4"))
        queue_timeout = float(os.getenv("AGENT_QUEUE_TIMEOUT", "10"))
        return cls(max_concurrent=max_concurrent, queue_timeout=queue_timeout)
