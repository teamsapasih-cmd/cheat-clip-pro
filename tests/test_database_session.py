from backend.database.session import normalize_database_url

def test_normalize_supabase_postgres_urls_to_psycopg():
    assert normalize_database_url("postgresql://user:pass@host:5432/db") == "postgresql+psycopg://user:pass@host:5432/db"
    assert normalize_database_url("postgres://user:pass@host:5432/db") == "postgresql+psycopg://user:pass@host:5432/db"

def test_leave_sqlite_urls_unchanged():
    assert normalize_database_url("sqlite:///./test.db") == "sqlite:///./test.db"
