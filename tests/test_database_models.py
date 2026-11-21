from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from backend.database.models import Base, User, Project, MediaAsset, RenderJob


def test_schema_creates_expected_core_tables():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    names = set(inspect(engine).get_table_names())
    assert {
        "clipstudio_users", "clipstudio_projects", "clipstudio_media_assets", "clipstudio_analyses", "clipstudio_transcripts",
        "clipstudio_clip_candidates", "clipstudio_editing_projects", "clipstudio_render_jobs",
        "clipstudio_exported_videos", "clipstudio_publication_suggestions", "clipstudio_usage_logs",
    }.issubset(names)


def test_user_project_media_relationships_persist():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        user = User(email="owner@example.test", display_name="Owner")
        project = Project(name="First project", owner=user)
        media = MediaAsset(
            project=project,
            owner_id=user.id or "pending",
            original_filename="sample.mp4",
            source_type="upload",
        )
        session.add(user)
        session.flush()
        media.owner_id = user.id
        session.commit()

        saved = session.query(Project).filter_by(owner_id=user.id).one()
        assert saved.name == "First project"
        assert saved.media_assets[0].original_filename == "sample.mp4"


def test_render_job_schema_has_tenant_owner_field():
    columns = {column.name for column in RenderJob.__table__.columns}
    assert "owner_id" in columns
    assert "status" in columns
    assert "queue_job_id" in columns
