"""Scanner worker — picks nmap jobs off the Redis queue and executes them."""

import os

from redis import Redis
from rq import Worker, Queue

redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
conn = Redis.from_url(redis_url)

if __name__ == "__main__":
    queues = [Queue("scans", connection=conn)]
    worker = Worker(queues, connection=conn)
    worker.work()
