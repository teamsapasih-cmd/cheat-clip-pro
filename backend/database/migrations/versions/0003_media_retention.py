"""Add expiry tracking for source media and exported video objects.

Revision ID: 0003_media_retention
Revises: 0002_analysis_jobs
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_media_retention"
down_revision = "0002_analysis_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    media_cols = {c["name"] for c in inspector.get_columns("clipstudio_media_assets")}
    if "retention_expires_at" not in media_cols:
        op.add_column("clipstudio_media_assets", sa.Column("retention_expires_at", sa.DateTime(timezone=True), nullable=True))
        op.create_index("ix_clipstudio_media_assets_retention_expires_at", "clipstudio_media_assets", ["retention_expires_at"])
    export_cols = {c["name"] for c in inspector.get_columns("clipstudio_exported_videos")}
    if "storage_deleted_at" not in export_cols:
        op.add_column("clipstudio_exported_videos", sa.Column("storage_deleted_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    export_cols = {c["name"] for c in inspector.get_columns("clipstudio_exported_videos")}
    if "storage_deleted_at" in export_cols:
        op.drop_column("clipstudio_exported_videos", "storage_deleted_at")
    media_cols = {c["name"] for c in inspector.get_columns("clipstudio_media_assets")}
    if "retention_expires_at" in media_cols:
        op.drop_index("ix_clipstudio_media_assets_retention_expires_at", table_name="clipstudio_media_assets")
        op.drop_column("clipstudio_media_assets", "retention_expires_at")
