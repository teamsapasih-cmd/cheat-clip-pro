import os
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.config import UPLOADS_DIR
from backend.routers.media import router


test_app = FastAPI()
test_app.include_router(router)


class TestClipWordTranscriptionApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._previous_rate_limit = os.environ.get("AUTH_RATE_LIMIT_ENABLED")
        os.environ["AUTH_RATE_LIMIT_ENABLED"] = "false"
        cls.client = TestClient(test_app)

    @classmethod
    def tearDownClass(cls):
        if cls._previous_rate_limit is None:
            os.environ.pop("AUTH_RATE_LIMIT_ENABLED", None)
        else:
            os.environ["AUTH_RATE_LIMIT_ENABLED"] = cls._previous_rate_limit

    def setUp(self):
        self.filename = f"upload_{uuid4().hex[:10]}_audio.wav"
        self.source_path = UPLOADS_DIR / self.filename
        self.source_path.parent.mkdir(parents=True, exist_ok=True)
        self.source_path.write_bytes(b"temporary test audio reference")

    def tearDown(self):
        self.source_path.unlink(missing_ok=True)

    def test_returns_word_timestamps_from_audio_transcription(self):
        expected_words = [
            {"word": "Halo", "start": 0.0, "end": 0.35},
            {"word": "dunia", "start": 0.4, "end": 0.9},
        ]
        with patch("backend.routers.media._transcribe_uploaded_audio_segment", return_value=expected_words) as transcribe:
            response = self.client.post(
                "/api/transcribe-clip-words",
                json={
                    "file_name": self.filename,
                    "start_time": 2.0,
                    "end_time": 7.0,
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["words"], expected_words)
        self.assertEqual(response.json()["source"], "audio_transcription")
        transcribe.assert_called_once()

    def test_rejects_invalid_clip_range(self):
        response = self.client.post(
            "/api/transcribe-clip-words",
            json={
                "file_name": self.filename,
                "start_time": 7.0,
                "end_time": 2.0,
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_rejects_non_upload_source(self):
        response = self.client.post(
            "/api/transcribe-clip-words",
            json={
                "file_name": "some_other_file.wav",
                "start_time": 0.0,
                "end_time": 3.0,
            },
        )
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
