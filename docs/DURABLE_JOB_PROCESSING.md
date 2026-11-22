# Durable background job processing

The Redis Streams foundation includes:

- Explicit job handler registration; no dynamic imports from message payloads.
- Attempt counters and bounded retries (WORKER_MAX_ATTEMPTS, default 3).
- Dead-letter stream (clipstudio:jobs:dead) for unsupported or exhausted jobs.
- Pending-message recovery with XAUTOCLAIM after WORKER_RECLAIM_IDLE_MS (default 60 seconds).
- Per-job progress metadata in Redis hashes, retained for seven days.
- Cooperative cancellation markers.

## Worker environment
- REDIS_URL: required.
- WORKER_NAME: optional unique consumer name; defaults to hostname.
- WORKER_MAX_ATTEMPTS: optional retry limit, default 3.
- WORKER_RECLAIM_IDLE_MS: optional pending-job idle threshold, default 60000.

Run as a separate cloud process: python -m backend.workers.redis_worker

The worker deliberately has no production analysis handler yet. The existing analysis endpoint is a streaming request pipeline tied to request-scoped inputs and currently sends its result directly to the browser. A durable analysis handler must be extracted into a reusable service and tested against stored media before switching the endpoint to enqueue mode. This prevents placeholder jobs from being acknowledged and avoids changing existing editor/render behavior prematurely.

Progress is available through the queue adapter. An authenticated HTTP status endpoint and database synchronization are the next integration step. Redis and the worker must be configured in hosting before jobs can execute.
