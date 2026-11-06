import atexit
import os
import shutil
import tempfile

# 1. Allocate an isolated temporary directory and database before importing any backend module
TEMP_TEST_DIR = tempfile.mkdtemp(prefix="sirensync_test_")
TEST_DB_FILE = os.path.join(TEMP_TEST_DIR, "isolated_test.db")
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"

# Set DATABASE_URL in environment before backend.config or backend.database.session are loaded
os.environ["DATABASE_URL"] = TEST_DATABASE_URL


def _cleanup_temp_dir():
    """Emergency fallback cleanup handler for the temporary test directory."""
    if os.path.exists(TEMP_TEST_DIR):
        try:
            shutil.rmtree(TEMP_TEST_DIR, ignore_errors=True)
        except OSError:
            pass


atexit.register(_cleanup_temp_dir)

# 2. Standard library and framework imports
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# 3. Backend database and application imports
from backend.database.base import Base
from backend.database.session import get_db
import backend.database.session as session_module
import backend.database.init_db as init_db_module
from backend.app import app
from seed.demo_seed_data import seed_database
import backend.models  # Ensure all models are registered

# 4. Create isolated test engine with identical PRAGMA and concurrency settings
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 15.0},
    pool_pre_ping=True
)


@event.listens_for(test_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA busy_timeout=5000;")
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.close()


TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Explicitly rebind module-level engine and session factories to the isolated test database
session_module.engine = test_engine
session_module.SessionLocal = TestingSessionLocal
init_db_module.engine = test_engine


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Initializes tables and seeds initial data once for the test session in the temporary database."""
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        seed_database(session)
    finally:
        session.close()

    yield

    # Clean teardown: release SQLite connections before removing the temporary database.
    try:
        test_engine.dispose()
    finally:
        if os.path.exists(TEMP_TEST_DIR):
            shutil.rmtree(TEMP_TEST_DIR)


@pytest.fixture
def db_session():
    """Provides a transactional database session for an individual test."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    """FastAPI TestClient with overridden get_db dependency, avoiding AnyIO lifespan thread deadlock."""
    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    c = TestClient(app)
    try:
        yield c
    finally:
        app.dependency_overrides.clear()
        c.close()
