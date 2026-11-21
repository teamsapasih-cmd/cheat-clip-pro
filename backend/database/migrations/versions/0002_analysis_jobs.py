"""Add cloud analysis job request and queue lifecycle fields."""
from alembic import op
import sqlalchemy as sa
revision = "0002_analysis_jobs"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None
def upgrade() -> None:
    op.add_column("analyses", sa.Column("request_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    op.add_column("analyses", sa.Column("queue_job_id", sa.String(length=255), nullable=True))
    op.create_unique_constraint("uq_analyses_queue_job_id", "analyses", ["queue_job_id"])
    op.add_column("analyses", sa.Column("progress_percent", sa.Float(), nullable=False, server_default="0"))
def downgrade() -> None:
    op.drop_column("analyses", "progress_percent")
    op.drop_constraint("uq_analyses_queue_job_id", "analyses", type_="unique")
    op.drop_column("analyses", "queue_job_id")
    op.drop_column("analyses", "request_json")
