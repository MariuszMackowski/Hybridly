"""Celery app: background COROS sync, also queued once when the worker starts."""

import logging

import redis
from celery import Celery
from celery.signals import worker_ready

import app.models_registry  # noqa: F401
from app.config import get_settings
from app.coros import oauth
from app.coros.client import McpCorosClient
from app.coros.models import CorosAccount
from app.coros.sync import run_sync
from app.db import SessionLocal
from app.time import local_today

log = logging.getLogger(__name__)
celery_app = Celery("hybridly", broker=get_settings().redis_url)
LOCK_KEY = "hybridly:coros-sync"
LOCK_TTL_S = 600


class SyncLock:
    """Redis lock so only one COROS sync runs at a time."""

    def __init__(self, client: redis.Redis):
        """Wrap a Redis connection."""
        self.redis = client

    def is_held(self) -> bool:
        """Whether a sync is currently running."""
        return bool(self.redis.exists(LOCK_KEY))

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
    if not lock.acquire():
        return None
    try:
        with SessionLocal() as db:
            account = db.get(CorosAccount, 1)
            if account is None or account.status != "connected":
                return None
            try:
                token = oauth.get_access_token(db)
            except oauth.NeedsReconnect as error:
                account.last_sync_status = {"errors": [str(error)]}
                db.commit()
                return None
            client = McpCorosClient(account.server_url, token)
            try:
                return vars(run_sync(db, client, local_today()))
            except Exception as error:  # noqa: BLE001 — record and surface in the UI
                log.exception("COROS sync failed")
                db.rollback()
                account = db.get(CorosAccount, 1)
                account.last_sync_status = {"errors": [f"Sync failed: {error}"]}
                db.commit()
                return None
    finally:
        lock.release()


def enqueue_sync() -> None:
    """Queue a background sync."""
    sync_coros.delay()


@worker_ready.connect
def _sync_on_start(**_) -> None:
    """Sync once whenever the stack (worker) starts."""
    enqueue_sync()
