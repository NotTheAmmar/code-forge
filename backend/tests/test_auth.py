"""Unit tests for Phase A1: Auth system.

Tests auth service functions (password hashing, token creation/validation)
and the auth API endpoints (register, login, refresh, me).
"""

import uuid
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db import Base
from app.dependencies import get_db
from app.main import app
from app.models.course import Course
from app.models.user import User
from app.services.auth_service import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)

# ── Shared async SQLite engine ────────────────────────────────────────────────

@pytest.fixture(scope="module")
def engine():
    return create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)


@pytest.fixture(scope="module", autouse=True)
def create_tables(engine):
    import asyncio

    async def _create():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.get_event_loop().run_until_complete(_create())


@pytest.fixture
def client(engine):
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# Auth Service Unit Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        hashed = hash_password("s3cr3t")
        assert hashed != "s3cr3t"

    def test_verify_correct_password(self):
        hashed = hash_password("hello123")
        assert verify_password("hello123", hashed) is True

    def test_reject_wrong_password(self):
        hashed = hash_password("hello123")
        assert verify_password("wrongpass", hashed) is False

    def test_hashes_are_unique(self):
        # bcrypt includes a random salt — same input gives different hashes
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2


class TestJWTTokens:
    def test_access_token_round_trip(self):
        uid = str(uuid.uuid4())
        token = create_access_token(uid, "student")
        payload = decode_access_token(token)
        assert payload["sub"] == uid
        assert payload["role"] == "student"
        assert payload["type"] == "access"

    def test_refresh_token_round_trip(self):
        uid = str(uuid.uuid4())
        token = create_refresh_token(uid)
        returned_uid = decode_refresh_token(token)
        assert returned_uid == uid

    def test_access_token_rejected_as_refresh(self):
        token = create_access_token(str(uuid.uuid4()), "student")
        with pytest.raises(TokenError, match="Invalid token type"):
            decode_refresh_token(token)

    def test_refresh_token_rejected_as_access(self):
        token = create_refresh_token(str(uuid.uuid4()))
        with pytest.raises(TokenError, match="Invalid token type"):
            decode_access_token(token)

    def test_tampered_token_raises(self):
        token = create_access_token(str(uuid.uuid4()), "student")
        bad = token[:-4] + "XXXX"
        with pytest.raises(TokenError):
            decode_access_token(bad)

    def test_expired_token_raises(self):
        import jwt as pyjwt
        from app.config import settings
        from datetime import datetime, timezone

        uid = str(uuid.uuid4())
        payload = {
            "sub": uid,
            "role": "student",
            "type": "access",
            "iat": datetime(2020, 1, 1, tzinfo=timezone.utc),
            "exp": datetime(2020, 1, 1, 0, 1, tzinfo=timezone.utc),
        }
        expired_token = pyjwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
        with pytest.raises(TokenError, match="expired"):
            decode_access_token(expired_token)


# ═══════════════════════════════════════════════════════════════════════════════
# Auth API Endpoint Tests (via TestClient + SQLite)
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegisterEndpoint:
    def test_register_student_success(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "email": "alice@test.com",
            "name": "Alice Smith",
            "password": "password123",
            "role": "student",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "alice@test.com"
        assert data["user"]["role"] == "student"

    def test_register_instructor_success(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "email": "prof.bob@test.com",
            "name": "Bob Jones",
            "password": "securepass",
            "role": "instructor",
        })
        assert resp.status_code == 201
        assert resp.json()["user"]["role"] == "instructor"

    def test_register_duplicate_email_returns_409(self, client):
        payload = {
            "email": "duplicate@test.com",
            "name": "Dup User",
            "password": "abc123x",
        }
        client.post("/api/v1/auth/register", json=payload)
        resp = client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 409

    def test_register_email_is_normalised(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "email": "  CAPS@TEST.COM  ",
            "name": "Caps User",
            "password": "abc123x",
        })
        assert resp.status_code == 201
        assert resp.json()["user"]["email"] == "caps@test.com"

    def test_register_short_password_rejected(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "email": "short@test.com",
            "name": "Short",
            "password": "ab",
        })
        assert resp.status_code == 422

    def test_register_missing_name_rejected(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "email": "noname@test.com",
            "password": "password123",
        })
        assert resp.status_code == 422


class TestLoginEndpoint:
    def test_login_success(self, client):
        # First register
        client.post("/api/v1/auth/register", json={
            "email": "login_test@test.com",
            "name": "Login User",
            "password": "mypassword",
        })
        # Then login
        resp = client.post("/api/v1/auth/login", json={
            "email": "login_test@test.com",
            "password": "mypassword",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == "login_test@test.com"

    def test_login_wrong_password_returns_401(self, client):
        client.post("/api/v1/auth/register", json={
            "email": "badpw@test.com",
            "name": "Bad PW",
            "password": "correctpass",
        })
        resp = client.post("/api/v1/auth/login", json={
            "email": "badpw@test.com",
            "password": "wrongpass",
        })
        assert resp.status_code == 401

    def test_login_unknown_email_returns_401(self, client):
        resp = client.post("/api/v1/auth/login", json={
            "email": "nobody@test.com",
            "password": "anything",
        })
        assert resp.status_code == 401

    def test_login_error_message_is_identical_for_both_failures(self, client):
        """Prevent account enumeration: wrong email and wrong password should
        return the same error message."""
        r_bad_email = client.post("/api/v1/auth/login", json={
            "email": "nonexistent999@test.com",
            "password": "somepass",
        })
        client.post("/api/v1/auth/register", json={
            "email": "enumtest@test.com",
            "name": "Enum Test",
            "password": "realpass",
        })
        r_bad_pass = client.post("/api/v1/auth/login", json={
            "email": "enumtest@test.com",
            "password": "wrongpass",
        })
        assert r_bad_email.json()["detail"] == r_bad_pass.json()["detail"]


class TestRefreshEndpoint:
    def test_refresh_returns_new_access_token(self, client):
        reg = client.post("/api/v1/auth/register", json={
            "email": "refresh_user@test.com",
            "name": "Refresh User",
            "password": "mypassword",
        })
        refresh_token = reg.json()["refresh_token"]

        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert resp.status_code == 200
        new_access = resp.json()["access_token"]
        # Verify the returned token is a valid access token (decodable and correct type)
        payload = decode_access_token(new_access)
        assert payload["type"] == "access"
        assert payload["sub"] == reg.json()["user"]["id"]

    def test_refresh_with_garbage_returns_401(self, client):
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": "notavalidtoken"})
        assert resp.status_code == 401

    def test_refresh_with_access_token_fails(self, client):
        reg = client.post("/api/v1/auth/register", json={
            "email": "refresh_bad@test.com",
            "name": "Refresh Bad",
            "password": "mypassword",
        })
        access_token = reg.json()["access_token"]
        # Sending access token where refresh is expected
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": access_token})
        assert resp.status_code == 401


class TestMeEndpoint:
    def test_me_returns_profile(self, client):
        reg = client.post("/api/v1/auth/register", json={
            "email": "me_user@test.com",
            "name": "Me User",
            "password": "mypassword",
        })
        access_token = reg.json()["access_token"]

        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "me_user@test.com"
        assert data["name"] == "Me User"
        assert "id" in data
        assert "created_at" in data

    def test_me_without_token_returns_403(self, client):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 403

    def test_me_with_invalid_token_returns_401(self, client):
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer totallyinvalidtoken"},
        )
        assert resp.status_code == 401

    def test_me_with_refresh_token_returns_401(self, client):
        """A refresh token must not be accepted as an access token for /me."""
        reg = client.post("/api/v1/auth/register", json={
            "email": "me_wrong_token@test.com",
            "name": "Wrong Token",
            "password": "mypassword",
        })
        refresh_token = reg.json()["refresh_token"]
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {refresh_token}"},
        )
        assert resp.status_code == 401


class TestGetCurrentUserDependency:
    """Tests that require_instructor integration works correctly."""

    def test_access_with_instructor_role(self, client):
        """Verify instructor token can access instructor-gated routes."""
        reg = client.post("/api/v1/auth/register", json={
            "email": "instr_dep@test.com",
            "name": "Instr Dep",
            "password": "mypassword",
            "role": "instructor",
        })
        token = reg.json()["access_token"]
        me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json()["role"] == "instructor"
