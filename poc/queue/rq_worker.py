"""RQ candidate worker with short PoC maintenance intervals."""

from __future__ import annotations

import os

from redis import Redis
from rq import Queue, Worker
from rq.serializers import JSONSerializer


connection = Redis.from_url(os.environ["REDIS_URL"])
queue = Queue("aca", connection=connection, serializer=JSONSerializer)
worker = Worker(
    [queue],
    connection=connection,
    serializer=JSONSerializer,
    worker_ttl=2,
    maintenance_interval=1,
)
worker.work(logging_level="WARNING")
