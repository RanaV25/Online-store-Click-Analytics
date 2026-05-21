"""Redis queue helpers for prediction jobs."""
import json
import uuid
from datetime import datetime

import redis

from config import Config


def get_redis_client(redis_url=None):
    return redis.Redis.from_url(redis_url or Config.REDIS_URL, decode_responses=True)


def enqueue_prediction_job(payload, redis_url=None, queue_name=None):
    job = {
        "job_id": str(uuid.uuid4()),
        "payload": payload,
        "queued_at": datetime.utcnow().isoformat(),
    }
    client = get_redis_client(redis_url)
    client.rpush(queue_name or Config.REDIS_PREDICTION_QUEUE, json.dumps(job))
    return job


def pop_prediction_job(redis_url=None, queue_name=None, timeout=1):
    client = get_redis_client(redis_url)
    item = client.blpop([queue_name or Config.REDIS_PREDICTION_QUEUE], timeout=timeout)
    if not item:
        return None
    _, body = item
    return json.loads(body)


def queue_length(redis_url=None, queue_name=None):
    client = get_redis_client(redis_url)
    return client.llen(queue_name or Config.REDIS_PREDICTION_QUEUE)
