import asyncio

from backend.workers.redis_worker import _consume_analysis_stream


class FakeQueue:
    def __init__(self):
        self.progress_updates = []

    def update_progress(self, job_id, status, progress, detail):
        self.progress_updates.append((job_id, status, progress, detail))


class FakeStreamingResponse:
    async def _body(self):
        yield b'data: {"overall_progress": 40, "stage": "Processing"}\n\n'
        yield b'data: {"done": true, "result": {"summary": "ok", "clips": []}}\n\n'

    @property
    def body_iterator(self):
        return self._body()


def test_worker_invokes_analysis_pipeline_without_http_request(monkeypatch):
    import backend.routers.analyze as analyze_router

    async def fake_analyze_video(payload, http_request):
        assert payload is marker
        assert http_request is None
        return FakeStreamingResponse()

    marker = object()
    queue = FakeQueue()
    monkeypatch.setattr(analyze_router, "analyze_video", fake_analyze_video)

    result = asyncio.run(_consume_analysis_stream(marker, queue, "job-123"))

    assert result == {"summary": "ok", "clips": []}
    assert queue.progress_updates == [
        ("job-123", "processing", 40, "Processing")
    ]
