"""Create the initial Clip Intelligence Studio schema.

Revision ID: 0001_initial_schema
Revises:

This revision intentionally pins its table list. Future models must be introduced
through new Alembic revisions instead of being silently folded into this migration.
"""
from alembic import op

from backend.database.models import Base

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None

_INITIAL_TABLES = (
    "clipstudio_users",
    "clipstudio_projects",
    "clipstudio_media_assets",
    "clipstudio_analyses",
    "clipstudio_transcripts",
    "clipstudio_clip_candidates",
    "clipstudio_editing_projects",
    "clipstudio_render_jobs",
    "clipstudio_exported_videos",
    "clipstudio_publication_suggestions",
    "clipstudio_usage_logs",
)


def upgrade() -> None:
    bind = op.get_bind()
    tables = [Base.metadata.tables[name] for name in _INITIAL_TABLES]
    Base.metadata.create_all(bind=bind, tables=tables)


def downgrade() -> None:
    # Drop only tables owned by this historical revision, in reverse FK order.
    for table_name in reversed(_INITIAL_TABLES):
        op.drop_table(table_name)
