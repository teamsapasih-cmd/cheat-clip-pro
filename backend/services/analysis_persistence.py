"""Idempotent persistence for completed AI video analysis results."""
from __future__ import annotations

from typing import Any
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.database.models import Analysis, ClipCandidate, MediaAsset, Transcript


def persist_analysis_result(
    db: Session, *, analysis_id: str, owner_id: str, result: dict[str, Any]
) -> Analysis:
    """Persist a completed legacy-engine result under strict tenant ownership.

    Replaying the same queue message replaces derived clip rows rather than
    duplicating them. The source media and analysis must belong to the owner.
    """
    analysis = db.scalar(
        select(Analysis).where(
            Analysis.id == analysis_id,
            Analysis.owner_id == owner_id,
        )
    )
    if analysis is None:
        raise LookupError("Analysis not found")

    media = db.scalar(
        select(MediaAsset).where(
            MediaAsset.id == analysis.media_asset_id,
            MediaAsset.owner_id == owner_id,
        )
    )
    if media is None:
        raise LookupError("Media asset not found")

    clips = result.get("clips") or []
    transcript_lines = result.get("transcript") or []
    if not isinstance(clips, list) or not isinstance(transcript_lines, list):
        raise ValueError("Analysis clips and transcript must be arrays")

    analysis.status = "completed"
    analysis.progress_percent = 100
    analysis.error_message = None
    analysis.provider = str(result.get("provider") or "")[:80] or analysis.provider
    analysis.model = str(result.get("model") or "")[:120] or analysis.model
    analysis.summary = str(result.get("summary") or "")
    analysis.result_json = result
    from datetime import datetime, timedelta, timezone
    import os
    media.retention_expires_at = datetime.now(timezone.utc) + timedelta(days=max(1, int(os.environ.get("SOURCE_MEDIA_RETENTION_DAYS", "7"))))

    db.execute(delete(ClipCandidate).where(ClipCandidate.analysis_id == analysis.id))
    for clip in clips:
        if not isinstance(clip, dict):
            continue
        start = float(clip.get("start_time", 0) or 0)
        end = float(clip.get("end_time", 0) or 0)
        if start < 0 or end <= start:
            continue
        db.add(ClipCandidate(
            owner_id=owner_id,
            analysis_id=analysis.id,
            start_seconds=start,
            end_seconds=end,
            score=float(clip.get("virality_score", 0) or 0),
            title=str(clip.get("title") or "")[:300] or None,
            rationale_json={
                "hook_time": clip.get("hook_time"),
                "key_quotes": clip.get("key_quotes") or [],
                "title_suggestion": clip.get("title_suggestion") or "",
                "caption_suggestion": clip.get("caption_suggestion") or "",
                "hashtag_suggestion": clip.get("hashtag_suggestion") or "",
            },
        ))

    if transcript_lines:
        latest = db.scalar(
            select(Transcript)
            .where(Transcript.media_asset_id == media.id, Transcript.owner_id == owner_id)
            .order_by(Transcript.revision.desc())
            .limit(1)
        )
        revision = (latest.revision + 1) if latest else 1
        normalized = [
            {
                "start": float(line.get("start", 0) or 0),
                "end": float(line.get("end", 0) or 0),
                "text": str(line.get("text") or ""),
                "engagement": line.get("engagement"),
            }
            for line in transcript_lines if isinstance(line, dict)
        ]
        db.add(Transcript(
            owner_id=owner_id,
            media_asset_id=media.id,
            language=str(result.get("transcript_language") or "und")[:20],
            revision=revision,
            segments_json=normalized,
            plain_text=" ".join(item["text"] for item in normalized).strip(),
            source=str(result.get("transcript_source") or "analysis")[:80],
        ))

    db.commit()
    db.refresh(analysis)
    return analysis
