"""Reliable Redis Streams worker with cloud analysis execution."""
from __future__ import annotations
import asyncio, json, logging, os, shutil, socket, tempfile, time
from functools import lru_cache
from pathlib import Path
from typing import Callable
from sqlalchemy import select, or_
from sqlalchemy.orm import Session
from backend.cloud.factory import build_object_storage
from backend.cloud.settings import validate_production_configuration
from backend.cloud.redis_queue import RedisStreamJobQueue
from backend.workers.lease import start_job_heartbeat
from backend.database.models import Analysis, MediaAsset, ExportedVideo
from backend.database.session import build_engine, build_session_factory
from backend.services.analysis_persistence import persist_analysis_result
from backend.services.retention import run_retention_sweep
logger = logging.getLogger("clipstudio.worker")
Handler = Callable[[dict[str, object]], None]



@lru_cache(maxsize=1)
def _session_factory():
    return build_session_factory(build_engine())

def _set_analysis_state(payload, status, error_message=None):
    analysis_id, owner_id = payload.get("analysis_id"), payload.get("owner_id")
    if not analysis_id or not owner_id: return
    db: Session = _session_factory()()
    try:
        analysis = db.scalar(select(Analysis).where(Analysis.id == str(analysis_id), Analysis.owner_id == str(owner_id)))
        if analysis is None:
            logger.warning("Analysis lifecycle update skipped: record not found")
            return
        analysis.status = status
        if status == "processing": analysis.progress_percent = max(float(analysis.progress_percent or 0), 5)
        elif status == "completed": analysis.progress_percent = 100
        if error_message is not None: analysis.error_message = str(error_message)[:2000]
        elif status in {"queued", "processing", "completed"}: analysis.error_message = None
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally: db.close()

def _persist_analysis_result(payload):
    if not all(k in payload for k in ("analysis_id", "owner_id", "result")) or not isinstance(payload["result"], dict):
        raise ValueError("analysis.persist_result payload is incomplete")
    db: Session = _session_factory()()
    try: persist_analysis_result(db, analysis_id=str(payload["analysis_id"]), owner_id=str(payload["owner_id"]), result=payload["result"])
    finally: db.close()

async def _consume_analysis_stream(request, queue, job_id):
    from backend.routers.analyze import analyze_video
    response = await analyze_video(request, None)
    buffer, final_result = "", None
    async for chunk in response.body_iterator:
        buffer += chunk.decode("utf-8", errors="replace") if isinstance(chunk, bytes) else str(chunk)
        while "\n\n" in buffer:
            block, buffer = buffer.split("\n\n", 1)
            data_lines = [line[5:].strip() for line in block.splitlines() if line.startswith("data:")]
            if not data_lines: continue
            try: event = json.loads("\n".join(data_lines))
            except json.JSONDecodeError: continue
            if "overall_progress" in event:
                pct = max(0, min(99, int(float(event.get("overall_progress") or 0))))
                queue.update_progress(job_id, "processing", pct, str(event.get("stage") or event.get("detail") or "Analyzing video"))
            if event.get("error"): raise RuntimeError(str(event["error"])[:1000])
            if event.get("done") and isinstance(event.get("result"), dict): final_result = event["result"]
    if final_result is None: raise RuntimeError("Analysis stream ended without a completed result")
    return final_result

def _run_analysis(payload, queue):
    from backend.schemas.analyze import AnalyzeRequest
    required = ("analysis_id", "owner_id", "media_asset_id", "_queue_job_id")
    if any(k not in payload for k in required): raise ValueError("analysis.run payload is incomplete")
    analysis_id, owner_id, job_id = str(payload["analysis_id"]), str(payload["owner_id"]), str(payload["_queue_job_id"])
    db: Session = _session_factory()()
    try:
        analysis = db.scalar(select(Analysis).where(Analysis.id == analysis_id, Analysis.owner_id == owner_id))
        media = db.scalar(select(MediaAsset).where(MediaAsset.id == str(payload["media_asset_id"]), MediaAsset.owner_id == owner_id, MediaAsset.status == "uploaded"))
        if analysis is None or media is None or analysis.media_asset_id != media.id: raise LookupError("Analysis or owned media asset was not found")
        if not media.storage_key: raise ValueError("Media asset has no cloud storage object key")
        settings, filename, storage_key = dict(analysis.request_json or {}), media.original_filename, media.storage_key
    finally: db.close()
    storage, temp_path = build_object_storage(), None
    try:
        with tempfile.NamedTemporaryFile(prefix="clipstudio-analysis-", suffix=Path(filename).suffix or ".mp4", delete=False) as temp:
            temp_path = temp.name
            with storage.open(storage_key) as source: shutil.copyfileobj(source, temp)
        request = AnalyzeRequest(url=temp_path, duration=settings.get("duration", "auto"),
            api_provider=settings.get("provider", "gemini"), model=settings.get("model") or "gemini-2.5-flash",
            custom_prompt=settings.get("custom_prompt"), range_start=settings.get("range_start"),
            range_end=settings.get("range_end"), target_clip_count=settings.get("target_clip_count", "auto"),
            transcript_language=settings.get("transcript_language", "id"))
        result = asyncio.run(_consume_analysis_stream(request, queue, job_id))
        _persist_analysis_result({"analysis_id": analysis_id, "owner_id": owner_id, "result": result})
    finally:
        if temp_path and os.path.exists(temp_path): os.unlink(temp_path)

def run_worker(handlers: dict[str, Handler] | None = None) -> None:
    validate_production_configuration()
    queue = RedisStreamJobQueue.from_env()
    consumer = os.environ.get("WORKER_NAME") or socket.gethostname()
    registered = {"analysis.persist_result": _persist_analysis_result, "analysis.run": lambda payload: _run_analysis(payload, queue)}
    if handlers: registered.update(handlers)
    max_attempts = max(1, int(os.environ.get("WORKER_MAX_ATTEMPTS", "3")))
    reclaim_idle_ms = max(10_000, int(os.environ.get("WORKER_RECLAIM_IDLE_MS", "60000")))
    logger.info("Worker %s started; registered handlers: %s", consumer, sorted(registered))
    if not os.environ.get("DATABASE_URL"):
        logger.warning("DATABASE_URL is not configured. Worker will stay idle and will not consume jobs until it is added in Railway Variables.")
    retention_interval = max(60, int(os.environ.get("RETENTION_SWEEP_INTERVAL_SECONDS", "900")))
    next_retention_sweep = 0.0
    while True:
        if not os.environ.get("DATABASE_URL"):
            time.sleep(10)
            continue
        if time.monotonic() >= next_retention_sweep:
            try:
                retention_db = _session_factory()()
                try:
                    summary = run_retention_sweep(retention_db, build_object_storage())
                    logger.info("Retention sweep: %s", summary)
                finally:
                    retention_db.close()
            except Exception:
                logger.exception("Retention sweep failed; it will retry next interval")
            finally:
                next_retention_sweep = time.monotonic() + retention_interval
        jobs = queue.claim_stale(consumer, min_idle_ms=reclaim_idle_ms, count=1)
        if not jobs: jobs = queue.read(consumer=consumer, count=1, block_ms=5000)
        for job in jobs:
            entry_id, job_id = str(job["stream_entry_id"]), str(job["job_id"])
            payload = dict(job.get("payload") or {})
            payload["_queue_job_id"] = job_id
            try:
                handler = registered.get(str(job["job_type"]))
                if handler is None:
                    reason = f"Unsupported job type: {job['job_type']}"
                    queue.dead_letter(job, reason); _set_analysis_state(payload, "failed", reason); continue
                if queue.is_cancelled(job_id):
                    _set_analysis_state(payload, "cancelled", "Job was cancelled")
                    queue.update_progress(job_id, "cancelled", 100); queue.acknowledge(entry_id); continue
                _set_analysis_state(payload, "processing"); queue.update_progress(job_id, "processing", 5)
                heartbeat_interval = max(2.0, reclaim_idle_ms / 3000.0)
                heartbeat_stop, heartbeat_thread = start_job_heartbeat(
                    queue, consumer, entry_id, heartbeat_interval
                )
                try:
                    handler(payload)
                finally:
                    heartbeat_stop.set()
                    heartbeat_thread.join(timeout=2.0)
                queue.update_progress(job_id, "completed", 100); _set_analysis_state(payload, "completed"); queue.acknowledge(entry_id)
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
                logger.exception("Job %s failed on attempt %s", job_id, int(job.get("attempt", 0)) + 1)
                try:
                    retry = queue.retry_or_dead_letter(job, error, max_attempts)
                    if retry:
                        _set_analysis_state(payload, "queued", error); time.sleep(min(2 ** (int(job.get("attempt", 0)) + 1), 30))
                    else: _set_analysis_state(payload, "failed", error)
                except Exception: logger.exception("Could not persist retry state for job %s; leaving it pending", job_id)

if __name__ == "__main__":
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    run_worker()
