"""
Embedding Queue Worker
-----------------------
A daemon thread that continuously pops tasks from the Redis rebuild queue
(see redis_cache.enqueue_embedding_rebuild) and processes them using the
synchronization_service.

The worker is started once during application lifespan via `start_worker()`.
It runs as a daemon thread so it exits automatically when the main process
stops — no explicit shutdown coordination needed.

Queue payload schema:
    {"type": "technician" | "job", "id": "<uuid string>"}

Back-off strategy:
    On failure the item is re-enqueued with an exponential back-off counter
    embedded in the payload, up to MAX_RETRIES times.
"""
from __future__ import annotations

import json
import threading
import time
from typing import Any, Dict

from app.utils.logger import logger

MAX_RETRIES = 3
RETRY_BASE_DELAY_SECONDS = 5  # grows as 5, 10, 20 …


def _process_task(task: Dict[str, Any]) -> None:
    """Run the appropriate sync function for a single queue task."""
    entity_type = task.get("type")
    entity_id = task.get("id")
    retries = int(task.get("retries", 0))

    if not entity_type or not entity_id:
        logger.warning(f"Embedding queue: malformed task: {task}")
        return

    # Import here to avoid circular imports at module load time
    from app.core.database import get_session
    from app.services.vector import synchronization_service, redis_cache

    try:
        session_gen = get_session()
        session = next(session_gen)

        try:
            if entity_type == "technician":
                ok = synchronization_service.sync_technician_embedding(session, entity_id)
            elif entity_type == "job":
                ok = synchronization_service.sync_job_embedding(session, entity_id)
            else:
                logger.warning(f"Unknown entity_type in queue: {entity_type}")
                return

            if not ok and retries < MAX_RETRIES:
                _re_enqueue(entity_type, entity_id, retries, redis_cache)
        finally:
            try:
                next(session_gen)  # close the generator / session
            except StopIteration:
                pass

    except Exception as exc:
        logger.error(f"Embedding queue worker error: {exc}")
        if retries < MAX_RETRIES:
            from app.services.vector import redis_cache
            _re_enqueue(entity_type, entity_id, retries, redis_cache)


def _re_enqueue(entity_type: str, entity_id: str, retries: int, redis_cache) -> None:
    """Re-queue a failed task with incremented retry counter and delay."""
    delay = RETRY_BASE_DELAY_SECONDS * (2 ** retries)
    time.sleep(delay)
    payload = json.dumps({"type": entity_type, "id": entity_id, "retries": retries + 1})
    r = redis_cache.get_redis()
    if r:
        from app.core.config import settings
        r.rpush(settings.EMBEDDING_QUEUE_KEY, payload)
        logger.info(
            f"Re-enqueued {entity_type}:{entity_id} (retry {retries+1}/{MAX_RETRIES})"
        )


def _worker_loop() -> None:
    """
    Poll the Redis queue every 5 seconds using non-blocking LPOP.
    This avoids holding idle TCP connections that exceed Redis Cloud's
    connection timeout and eliminates the "Timeout reading from ..." warnings.
    """
    logger.info("Embedding queue worker thread started (poll mode).")
    from app.services.vector import redis_cache

    POLL_INTERVAL = 5  # seconds between queue polls when queue is empty

    while True:
        try:
            task = redis_cache.dequeue_embedding_rebuild()
            if task:
                logger.info(f"Queue worker processing: {task}")
                _process_task(task)
            else:
                # Queue is empty — sleep before next poll
                time.sleep(POLL_INTERVAL)
        except Exception as exc:
            # Never let the worker die — log and keep going
            logger.error(f"Embedding queue loop error (continuing): {exc}")
            time.sleep(2)


_worker_thread: threading.Thread | None = None
_worker_started = False
_worker_lock = threading.Lock()


def start_worker() -> None:
    """
    Start the background queue worker daemon thread.
    Safe to call multiple times — will only start one thread.
    """
    global _worker_thread, _worker_started
    with _worker_lock:
        if _worker_started:
            return
        _worker_thread = threading.Thread(
            target=_worker_loop,
            name="EmbeddingQueueWorker",
            daemon=True,
        )
        _worker_thread.start()
        _worker_started = True
        logger.info("Embedding queue worker daemon started.")


def is_worker_running() -> bool:
    return _worker_thread is not None and _worker_thread.is_alive()
