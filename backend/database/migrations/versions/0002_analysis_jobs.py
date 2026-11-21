"""Add cloud analysis job request and queue lifecycle fields.

The initial schema migration creates tables from current metadata. These guards
also support databases that already applied the earlier version of revision 0001.
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_analysis_jobs"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing = {column["name"] for column in inspector.get_columns("analyses")}
    if "request_json" not in existing:
        op.add_column("analyses", sa.Column("request_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    if "queue_job_id" not in existing:
        op.add_column("analyses", sa.Column("queue_job_id", sa.String(length=255), nullable=True))
    if "progress_percent" not in existing:
        op.add_column("analyses", sa.Column("progress_percent", sa.Float(), nullable=False, server_default="0"))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing = {column["name"] for column in inspector.get_columns("analyses")}
    for column in ("progress_percent", "queue_job_id", "request_json"):
        if column in existing:
            op.drop_column("analyses", column)
