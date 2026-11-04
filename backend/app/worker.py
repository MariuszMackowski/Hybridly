"""Celery app: background COROS sync, also queued once when the worker starts."""

import redis
from celery import Celery
from celery.signals import worker_ready

import app.models_registry  # noqa: F401
from app.config import get_settings
from app.coros.client import McpCorosClient
from app.coros.sync import sync_account
from app.db import SessionLocal
from app.time import local_today

celery_app = Celery("hybridly", broker=get_settings().redis_url)
LOCK_KEY = "hybridly:coros-sync"
LOCK_TTL_S = 600
QUEUED_KEY = "hybridly:coros-sync-queued"
QUEUED_TTL_S = 120


class SyncLock:
    """Redis lock so only one COROS sync runs at a time."""

    def __init__(self, client: redis.Redis):
        """Wrap a Redis connection."""
        self.redis = client

    def is_held(self) -> bool:
        """Whether a sync is queued or running."""
        return bool(self.redis.exists(LOCK_KEY, QUEUED_KEY))

    def mark_queued(self) -> None:
        """Flag a queued sync so the UI shows progress before the worker starts."""
        self.redis.set(QUEUED_KEY, "1", ex=QUEUED_TTL_S)

    def clear_queued(self) -> None:
        """The worker picked the job up."""
        self.redis.delete(QUEUED_KEY)

    def acquire(self) -> bool:
        """Take the lock; False when another sync holds it."""
        return bool(self.redis.set(LOCK_KEY, "1", nx=True, ex=LOCK_TTL_S))

    def release(self) -> None:
        """Release the lock."""
        self.redis.delete(LOCK_KEY)


def sync_lock() -> SyncLock:
    """Lock bound to the configured Redis."""
    return SyncLock(redis.Redis.from_url(get_settings().redis_url))


@celery_app.task(name="sync_coros")
def sync_coros() -> dict | None:
    """Run one COROS sync unless one is already running."""
    lock = sync_lock()
    lock.clear_queued()
    if not lock.acquire():
        return None
    try:
        with SessionLocal() as db:
            return sync_account(db, McpCorosClient, local_today())
    finally:
        lock.release()


def enqueue_sync() -> None:
    """Queue a background sync (reported as syncing until the worker picks it up)."""
    sync_lock().mark_queued()
    sync_coros.delay()


@worker_ready.connect
def _sync_on_start(**_) -> None:
    """Sync once whenever the stack (worker) starts."""
    enqueue_sync()
