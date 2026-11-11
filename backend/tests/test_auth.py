import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.testclient import TestClient
import bcrypt

# Force test environment variables before importing app
os.environ["ENVIRONMENT"] = "test"
os.environ["TURNSTILE_SECRET_KEY"] = "1x0000000000000000000000000000000AA"
TEST_DB_PATH = "/tmp/test_sirensync_auth.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"

from app.database import Base, get_db
from app.models import Patient, UserSession
from app.main import app

# Create test engine and session factory
test_engine = create_engine(
    f"sqlite:///{TEST_DB_PATH}",
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    # Remove old test db file if exists
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except OSError:
            pass
    Base.metadata.create_all(bind=test_engine)
    yield
    # Teardown
    Base.metadata.drop_all(bind=test_engine)
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except OSError:
            pass

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

# 1. Registration succeeds with valid details & returns patient profile (excluding password)
def test_01_registration_success(client):
    payload = {
        "full_name": "Aarav Sharma",
        "email": "aarav.sharma@example.com",
        "password": "SecurePassword123!",
        "confirm_password": "SecurePassword123!",
        "captcha_token": "XXXX.DUMMY.TOKEN.XXXX"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert "patient" in data
    assert data["patient"]["full_name"] == "Aarav Sharma"
    assert data["patient"]["email"] == "aarav.sharma@example.com"
    assert "password" not in data["patient"]
    assert "password_hash" not in data["patient"]
    # Check session cookie is set
    assert "sirensync_session" in response.cookies

# 2. Registration fails with duplicate email
def test_02_registration_fails_duplicate_email(client):
    payload = {
        "full_name": "Aarav Duplicate",
        "email": "AARAV.SHARMA@example.com",  # case-insensitive check
        "password": "AnotherPassword456!",
        "confirm_password": "AnotherPassword456!",
        "captcha_token": "XXXX.DUMMY.TOKEN.XXXX"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"].lower()

# 3. Registration fails with invalid email format
def test_03_registration_fails_invalid_email(client):
    payload = {
        "full_name": "Invalid Email User",
        "email": "not-an-email-address",
        "password": "SecurePassword123!",
        "confirm_password": "SecurePassword123!",
        "captcha_token": "XXXX.DUMMY.TOKEN.XXXX"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 422  # Pydantic validation error

# 4. Registration fails with password mismatch or too short
def test_04_registration_fails_password_validation(client):
    # Short password
    payload_short = {
        "full_name": "Short Pass",
        "email": "short@example.com",
        "password": "123",
        "confirm_password": "123",
        "captcha_token": "XXXX.DUMMY.TOKEN.XXXX"
    }
    res_short = client.post("/api/auth/register", json=payload_short)
    assert res_short.status_code == 422

    # Password mismatch
    payload_mismatch = {
        "full_name": "Mismatch User",
        "email": "mismatch@example.com",
        "password": "ValidPassword123!",
        "confirm_password": "DifferentPassword456!",
        "captcha_token": "XXXX.DUMMY.TOKEN.XXXX"
    }
    res_mismatch = client.post("/api/auth/register", json=payload_mismatch)
    assert res_mismatch.status_code == 422

# 5. Password hashing check: verify plaintext password is NEVER stored in database, and password hash verifies with bcrypt
def test_05_password_hashing_security():
    db = TestingSessionLocal()
    try:
        user = db.query(Patient).filter(Patient.email == "aarav.sharma@example.com").first()
        assert user is not None
        assert user.password_hash != "SecurePassword123!"
        assert user.password_hash.startswith("$2b$") or user.password_hash.startswith("$2a$")
        assert bcrypt.checkpw("SecurePassword123!".encode("utf-8"), user.password_hash.encode("utf-8"))
        assert not bcrypt.checkpw("WrongPassword!".encode("utf-8"), user.password_hash.encode("utf-8"))
    finally:
        db.close()

# 6. Login succeeds with valid credentials & sets HTTP-only session cookie
def test_06_login_success(client):
    payload = {
        "email": "aarav.sharma@example.com",
        "password": "SecurePassword123!",
        "captcha_token": "XXXX.DUMMY.TOKEN.XXXX"
    }
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["patient"]["email"] == "aarav.sharma@example.com"
    assert "password" not in data["patient"]
    assert "sirensync_session" in response.cookies

# 7. Login fails with invalid password (generic error message)
def test_07_login_fails_invalid_password(client):
    payload = {
        "email": "aarav.sharma@example.com",
        "password": "IncorrectPassword999!",
        "captcha_token": "XXXX.DUMMY.TOKEN.XXXX"
    }
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 401
    assert "invalid email or password" in response.json()["detail"].lower()

# 8. Login fails with non-existent email (generic error message to prevent user enumeration)
def test_08_login_fails_nonexistent_email(client):
    payload = {
        "email": "ghost.user@example.com",
        "password": "SomePassword123!",
        "captcha_token": "XXXX.DUMMY.TOKEN.XXXX"
    }
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 401
    # Check that error message is identical generic message
    assert "invalid email or password" in response.json()["detail"].lower()

# 9. CAPTCHA verification succeeds with valid token, and is rejected when invalid
def test_09_captcha_rejection(client):
    payload = {
        "email": "aarav.sharma@example.com",
        "password": "SecurePassword123!",
        "captcha_token": "invalid-test-token"
    }
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 400
    assert "captcha" in response.json()["detail"].lower()

# 10. GET /api/auth/me returns authenticated user profile when session cookie is present
def test_10_get_me_authenticated(client):
    # First login to establish session
    login_resp = client.post("/api/auth/login", json={
        "email": "aarav.sharma@example.com",
        "password": "SecurePassword123!",
        "captcha_token": "XXXX.DUMMY.TOKEN.XXXX"
    })
    assert login_resp.status_code == 200

    # Call /api/auth/me with cookie
    me_resp = client.get("/api/auth/me")
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["success"] is True
    assert me_data["patient"]["email"] == "aarav.sharma@example.com"
    assert me_data["patient"]["full_name"] == "Aarav Sharma"

# 11. GET /api/auth/me returns 401 when unauthenticated / session cookie missing
def test_11_get_me_unauthenticated():
    with TestClient(app) as clean_client:
        me_resp = clean_client.get("/api/auth/me")
        assert me_resp.status_code == 401
        assert "not authenticated" in me_resp.json()["detail"].lower() or "required" in me_resp.json()["detail"].lower()

# 12. Logout invalidates session & clears cookie; subsequent /api/auth/me returns 401
def test_12_logout_invalidation(client):
    # Ensure client is logged in
    client.post("/api/auth/login", json={
        "email": "aarav.sharma@example.com",
        "password": "SecurePassword123!",
        "captcha_token": "XXXX.DUMMY.TOKEN.XXXX"
    })
    me_before = client.get("/api/auth/me")
    assert me_before.status_code == 200

    # Logout
    logout_resp = client.post("/api/auth/logout")
    assert logout_resp.status_code == 200
    assert logout_resp.json()["success"] is True

    # Subsequent /api/auth/me must return 401
    me_after = client.get("/api/auth/me")
    assert me_after.status_code == 401

# 13. Persistence across backend restarts: data persists in SQLite database across DB session reload
def test_13_database_persistence_across_reconnect():
    # Insert new patient in session 1
    new_engine = create_engine(f"sqlite:///{TEST_DB_PATH}", connect_args={"check_same_thread": False})
    Session1 = sessionmaker(bind=new_engine)
    s1 = Session1()
    p = Patient(
        full_name="Persistent Patient",
        email="persistent@sirensync.org",
        password_hash=bcrypt.hashpw(b"SecretPass999!", bcrypt.gensalt()).decode("utf-8")
    )
    s1.add(p)
    s1.commit()
    patient_id = p.id
    s1.close()
    new_engine.dispose()

    # Simulate backend restart: new engine instance reading from same SQLite file
    restarted_engine = create_engine(f"sqlite:///{TEST_DB_PATH}", connect_args={"check_same_thread": False})
    Session2 = sessionmaker(bind=restarted_engine)
    s2 = Session2()
    reloaded_patient = s2.query(Patient).filter(Patient.id == patient_id).first()
    assert reloaded_patient is not None
    assert reloaded_patient.full_name == "Persistent Patient"
    assert reloaded_patient.email == "persistent@sirensync.org"
    assert bcrypt.checkpw(b"SecretPass999!", reloaded_patient.password_hash.encode("utf-8"))
    s2.close()
    restarted_engine.dispose()
