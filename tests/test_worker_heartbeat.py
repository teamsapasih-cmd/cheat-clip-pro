import time

from backend.workers.redis_worker import _start_job_heartbeat


class FakeQueue:
    def __init__(self):
        self.calls = []

    def heartbeat(self, consumer, entry_id):
        self.calls.append((consumer, entry_id))
        return True


def test_worker_heartbeat_runs_until_handler_finishes():
    queue = FakeQueue()
    stop, thread = _start_job_heartbeat(queue, "worker-a", "entry-1", 0.01)

    time.sleep(0.06)
    stop.set()
    thread.join(timeout=1)

    assert not thread.is_alive()
    assert len(queue.calls) >= 2
    assert all(call == ("worker-a", "entry-1") for call in queue.calls)
