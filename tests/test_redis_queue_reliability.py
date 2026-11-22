from backend.cloud.redis_queue import RedisStreamJobQueue

class FakeRedis:
    def __init__(self):
        self.streams, self.hashes, self.acked, self.dead, self.kv = {}, {}, [], [], set()
        self.claimed = None
    def xgroup_create(self, *args, **kwargs): return None
    def xadd(self, stream, fields):
        self.streams.setdefault(stream, []).append(("1-0", dict(fields)))
        if stream.endswith(":dead"): self.dead.append(dict(fields))
        return "1-0"
    def hset(self, key, mapping): self.hashes[key] = dict(mapping)
    def expire(self, *args): return True
    def hgetall(self, key): return self.hashes.get(key, {})
    def xack(self, stream, group, entry): self.acked.append(entry); return 1
    def xclaim(self, stream, group, consumer, min_idle_time, message_ids, justid=False):
        self.claimed = (stream, group, consumer, min_idle_time, message_ids, justid)
        return message_ids
    def set(self, key, value, ex=None): self.kv.add(key); return True
    def exists(self, key): return key in self.kv

def test_enqueue_writes_attempt_and_progress():
    client = FakeRedis()
    queue = RedisStreamJobQueue(client)
    receipt = queue.enqueue("analysis", {"media_asset_id": "asset-1"})
    fields = client.streams["clipstudio:jobs"][0][1]
    assert fields["attempt"] == "0"
    assert receipt.status == "queued"
    assert queue.get_progress(receipt.job_id)["status"] == "queued"

def test_retry_requeues_and_acknowledges_original():
    client = FakeRedis()
    queue = RedisStreamJobQueue(client)
    job = {"job_id": "job-1", "job_type": "analysis", "payload": {"x": 1},
           "attempt": 0, "stream_entry_id": "old-1", "created_at": "2026-01-01T00:00:00+00:00"}
    assert queue.retry_or_dead_letter(job, "temporary failure", max_attempts=3)
    assert client.streams["clipstudio:jobs"][-1][1]["attempt"] == "1"
    assert client.acked == ["old-1"]
    assert queue.get_progress("job-1")["status"] == "retrying"

def test_max_attempts_moves_job_to_dead_letter():
    client = FakeRedis()
    queue = RedisStreamJobQueue(client)
    job = {"job_id": "job-2", "job_type": "analysis", "payload": {"x": 1},
           "attempt": 2, "stream_entry_id": "old-2"}
    assert queue.retry_or_dead_letter(job, "permanent failure", max_attempts=3) is False
    assert len(client.dead) == 1
    assert client.acked == ["old-2"]
    assert queue.get_progress("job-2")["status"] == "failed"


def test_heartbeat_refreshes_pending_entry_for_same_consumer():
    client = FakeRedis()
    queue = RedisStreamJobQueue(client)

    assert queue.heartbeat("worker-a", "1710000000000-0") is True
    assert client.claimed == (
        "clipstudio:jobs",
        "clipstudio-workers",
        "worker-a",
        0,
        ["1710000000000-0"],
        True,
    )
