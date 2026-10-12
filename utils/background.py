"""Background work: a Celery task in the worker, or a thread of this process when there is no Celery."""
import logging
import threading
from functools import wraps

from django.conf import settings
from django.core.cache import cache
from django.db import connection

logger = logging.getLogger(__name__)


def run_in_background(task, *args):
    """Hands a Celery task over to the worker. With `CELERY_ENABLED=0` (no worker: local run, a server
    where the services are not set up yet) or when the broker is unreachable, the task runs in a
    thread of this process — a failure there is only logged, the caller is never affected."""
    if settings.CELERY_ENABLED:
        try:
            task.delay(*args)
            return
        except Exception as e:
            logger.error("Celery broker is unreachable, running %s in a thread: %s", task.name, e)
    threading.Thread(target=_run_in_thread, args=(task, args), daemon=True).start()


def _run_in_thread(task, args):
    try:
        # calling a task object runs its function right here
        task(*args)
    except Exception as e:
        logger.error("Background task failed: task=%s args=%s error=%s", task.name, args, e)
    finally:
        connection.close()


def exclusive(timeout):
    """A periodic task that is still running is not started a second time. The lock lives in the cache:
    released when the task ends, or after `timeout` seconds if its process died."""
    def decorator(func):
        key = f"task-lock:{func.__module__}.{func.__name__}"

        @wraps(func)
        def wrapper(*args, **kwargs):
            if not cache.add(key, 1, timeout):
                logger.info("Task is still running, skipped: %s", key)
                return None
            try:
                return func(*args, **kwargs)
            finally:
                cache.delete(key)
        return wrapper
    return decorator
