"""Owner-scoped project API."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.dependencies import get_db_session
from backend.database.models import ExportedVideo, MediaAsset, Project, RenderJob, User
from backend.routers.auth import get_current_user
from backend.schemas.identity import ProjectCreateRequest, ProjectResponse

router = APIRouter(prefix="/api/projects", tags=["Projects"])


@router.get("", response_model=list[ProjectResponse])
def list_projects(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    return list(
        db.scalars(
            select(Project)
            .where(Project.owner_id == user.id)
            .order_by(Project.updated_at.desc())
        ).all()
    )


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    body: ProjectCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    project = Project(
        owner_id=user.id,
        name=body.name.strip(),
        description=(body.description or "").strip() or None,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    project = db.scalar(
        select(Project).where(Project.id == project_id, Project.owner_id == user.id)
    )
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    project = db.scalar(
        select(Project).where(Project.id == project_id, Project.owner_id == user.id)
    )
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    source_object = db.scalar(
        select(MediaAsset.id)
        .where(MediaAsset.project_id == project.id, MediaAsset.storage_key.is_not(None))
        .limit(1)
    )
    export_object = db.scalar(
        select(ExportedVideo.id)
        .join(RenderJob, ExportedVideo.render_job_id == RenderJob.id)
        .where(
            RenderJob.project_id == project.id,
            ExportedVideo.storage_deleted_at.is_(None),
        )
        .limit(1)
    )
    if source_object or export_object:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Project still contains cloud media or exports. Wait until their configured retention period has expired before deleting this project.",
        )

    db.delete(project)
    db.commit()
