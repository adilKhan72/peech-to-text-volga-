"""RQ worker entrypoint.

Run with: python worker.py
Concurrency (how many transcriptions run at once) is controlled by how many of
these processes you run, not by anything in the API layer.
"""

from app.db.session import init_db
from app.jobs.queue import get_queue, get_redis

if __name__ == "__main__":
    from rq import Worker

    init_db()
    Worker([get_queue()], connection=get_redis()).work()
