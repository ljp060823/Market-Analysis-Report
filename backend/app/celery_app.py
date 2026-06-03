from celery import Celery
import asyncio
import redis
import json
from datetime import datetime, timedelta
from langchain_core.messages import BaseMessage
from app.graph.builder import build_graph
from app.metrics import update_celery_queue_length, record_cache_hit, record_cache_miss
from app.db import settings

celery_app = Celery("agent", broker=settings.REDIS_URI, backend=settings.REDIS_URI)
redis_client = redis.from_url(settings.REDIS_URI)

def _make_serializable(obj):
    if isinstance(obj, BaseMessage):
        return {"role": getattr(obj, "type", "assistant"), "content": obj.content}
    if isinstance(obj, dict):
        return {k: _make_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_make_serializable(v) for v in obj]
    return obj

@celery_app.task(bind=True, max_retries=3)
def run_full_pipeline(self, query: str, user_id: str, thread_id: str):
    update_celery_queue_length()
    cache_key = f"report:{hash(query)}:{user_id}"
    if cached := redis_client.get(cache_key):
        record_cache_hit()
        return json.loads(cached)
    record_cache_miss()

    async def _run():
        graph = await build_graph()
        config = {"configurable": {"thread_id": thread_id}}
        return await graph.ainvoke({"messages": [("human", query)], "user_id": user_id}, config)

    result = asyncio.run(_run())
    serializable = _make_serializable(result)
    redis_client.setex(cache_key, 7200, json.dumps(serializable))
    return serializable

@celery_app.task
def clean_old_cache():
    now = datetime.now()
    for key in list(redis_client.scan_iter("report:*")):
        ttl = redis_client.ttl(key)
        if ttl < 0 or datetime.fromtimestamp(now.timestamp() - ttl) < now - timedelta(hours=24):
            redis_client.delete(key)

@celery_app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(3600, clean_old_cache.s(), name='clean cache every hour')