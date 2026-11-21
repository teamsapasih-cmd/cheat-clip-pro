"""Authenticated cloud analysis job API."""
from __future__ import annotations
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.cloud.factory import build_job_queue, build_object_storage
from backend.database.dependencies import get_db_session
from backend.database.models import Analysis, MediaAsset, User
from backend.routers.auth import get_current_user

router = APIRouter(prefix="/api/analyses", tags=["Cloud Analysis"])

class AnalysisJobRequest(BaseModel):
    media_asset_id: str = Field(min_length=1, max_length=36)
    provider: Literal["gemini", "openrouter"] = "gemini"
    model: str | None = Field(default=None, max_length=160)
    duration: Literal["15s", "30s", "60s", "auto"] = "auto"
    target_clip_count: int | Literal["auto"] = "auto"
    custom_prompt: str | None = Field(default=None, max_length=12000)
    range_start: float | None = Field(default=None, ge=0)
    range_end: float | None = Field(default=None, gt=0)
    transcript_language: Literal["id", "en"] = "id"

@router.post("", status_code=status.HTTP_202_ACCEPTED)
def create_analysis_job(body: AnalysisJobRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db_session)):
    media = db.scalar(select(MediaAsset).where(MediaAsset.id == body.media_asset_id, MediaAsset.owner_id == user.id, MediaAsset.status == "uploaded"))
    if media is None or not media.storage_key:
        raise HTTPException(status_code=404, detail="Uploaded media asset not found")
    try:
        build_object_storage()
        queue = build_job_queue()
    except (RuntimeError, ValueError):
        raise HTTPException(status_code=503, detail="Cloud storage and job queue must be connected before analysis can be queued")
    if body.range_start is not None and body.range_end is not None and body.range_start >= body.range_end:
        raise HTTPException(status_code=422, detail="range_start must be less than range_end")
    analysis = Analysis(owner_id=user.id, media_asset_id=media.id, status="queued", progress_percent=0,
        request_json=body.model_dump(exclude={"media_asset_id"}, exclude_none=True))
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    try:
        receipt = queue.enqueue("analysis.run", {"analysis_id": analysis.id, "owner_id": user.id, "media_asset_id": media.id})
        analysis.queue_job_id = receipt.job_id
        db.commit()
        db.refresh(analysis)
    except Exception:
        db.rollback()
        failed = db.scalar(select(Analysis).where(Analysis.id == analysis.id, Analysis.owner_id == user.id))
        if failed is not None:
            failed.status = "failed"
            failed.error_message = "Unable to enqueue analysis job"
            db.commit()
        raise HTTPException(status_code=503, detail="Unable to enqueue analysis job; please retry")
    return {"analysis_id": analysis.id, "job_id": analysis.queue_job_id, "status": analysis.status, "progress": analysis.progress_percent}

@router.get("/{analysis_id}")
def get_analysis_job(analysis_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db_session)):
    analysis = db.scalar(select(Analysis).where(Analysis.id == analysis_id, Analysis.owner_id == user.id))
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    queue_state = None
    if analysis.queue_job_id:
        try:
            queue_state = build_job_queue().get_progress(analysis.queue_job_id)
        except Exception:
            queue_state = None
    status_value, progress, detail = analysis.status, float(analysis.progress_percent or 0), None
    if queue_state:
        qs = queue_state.get("status")
        if status_value not in {"completed", "failed", "cancelled"} and qs:
            status_value = qs
        try: progress = float(queue_state.get("progress", progress))
        except (TypeError, ValueError): pass
        detail = queue_state.get("detail")
    response = {"analysis_id": analysis.id, "job_id": analysis.queue_job_id, "media_asset_id": analysis.media_asset_id,
        "status": status_value, "progress": progress, "detail": detail, "error": analysis.error_message,
        "created_at": analysis.created_at, "updated_at": analysis.updated_at}
    if analysis.status == "completed": response["result"] = analysis.result_json
    return response
