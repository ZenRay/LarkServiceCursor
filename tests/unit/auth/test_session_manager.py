"""Unit tests for AuthSessionManager.

This module tests the authentication session management functionality
following TDD (Test-Driven Development) approach.

Test Coverage:
- T025: create_session() - Create new auth session with UUID
- T026: complete_session() - Complete session with token and user info
- T027: get_active_token() - Retrieve active token for user
- T028: cleanup_expired_sessions() - Clean up expired sessions
- T029: Multi-user isolation - Ensure proper app_id/user_id isolation
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from lark_service.auth.exceptions import (
    AuthSessionExpiredError,
    AuthSessionNotFoundError,
)
from lark_service.auth.session_manager import AuthSessionManager
from lark_service.auth.types import UserInfo
from lark_service.core.models.auth_session import Base, UserAuthSession


@pytest.fixture
def db_engine():
    """Create in-memory SQLite database for testing."""
    # Use UTC timezone for SQLite
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(db_engine):
    """Create database session for testing."""
    session_local = sessionmaker(bind=db_engine)
    session = session_local()
    yield session
    session.close()


@pytest.fixture
def session_manager(db_session):
    """Create AuthSessionManager instance for testing."""
    return AuthSessionManager(db_session)


# T025: Unit test for create_session
class TestCreateSession:
    """Test suite for AuthSessionManager.create_session()."""

    def test_create_session_generates_uuid(self, session_manager):
        """Test: create_session generates valid UUID session_id."""
        session = session_manager.create_session(
            app_id="cli_test123456789",
            user_id="ou_test_user_123",
            auth_method="websocket_card",
        )

        # Verify UUID format
        assert session.session_id is not None
        uuid.UUID(session.session_id)  # Should not raise ValueError

        # Verify initial state
        assert session.state == "pending"
        assert session.app_id == "cli_test123456789"
        assert session.user_id == "ou_test_user_123"
        assert session.auth_method == "websocket_card"

    def test_create_session_sets_expiration(self, session_manager):
        """Test: create_session sets expires_at to 10 minutes from now."""
        now = datetime.now(UTC).replace(tzinfo=None)
        session = session_manager.create_session(
            app_id="cli_test123456789",
            user_id="ou_test_user_123",
        )

        # Verify expiration time (allow 1 second tolerance)
        expected_expires = now + timedelta(minutes=10)
        time_diff = abs((session.expires_at - expected_expires).total_seconds())
        assert time_diff < 1.0

    def test_create_session_persists_to_database(self, session_manager, db_session):
        """Test: create_session persists session to database."""
        session = session_manager.create_session(
            app_id="cli_test123456789",
            user_id="ou_test_user_123",
        )

        # Verify persistence
        db_session.expire_all()  # Clear SQLAlchemy cache
        retrieved = (
            db_session.query(UserAuthSession).filter_by(session_id=session.session_id).first()
        )
        assert retrieved is not None
        assert retrieved.session_id == session.session_id


# T026: Unit test for complete_session with token and user info
class TestCompleteSession:
    """Test suite for AuthSessionManager.complete_session()."""

    def test_complete_session_stores_token_and_user_info(self, session_manager):
        """Test: complete_session stores encrypted token and user info."""
        # Create pending session
        session = session_manager.create_session(
            app_id="cli_test123456789",
            user_id="ou_test_user_123",
        )

        # Complete session
        user_info = UserInfo(
            user_id="ou_test_user_123",
            open_id="ou_test_user_123",
            union_id="on_test_union_456",
            user_name="Test User",
            mobile="+86-13800138000",
            email="test@example.com",
        )

        token_expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=7)
        session_manager.complete_session(
            session_id=session.session_id,
            user_access_token="u-test-token-abc123",
            token_expires_at=token_expires_at,
            user_info=user_info,
        )

        # Verify completion
        updated = session_manager.get_session(session.session_id)
        assert updated.state == "completed"
        assert updated.user_access_token is not None
        assert updated.token_expires_at == token_expires_at
        assert updated.user_name == "Test User"
        assert updated.email == "test@example.com"
        assert updated.mobile == "+86-13800138000"
        assert updated.open_id == "ou_test_user_123"
        assert updated.union_id == "on_test_union_456"
        assert updated.completed_at is not None

    def test_complete_session_raises_if_not_found(self, session_manager):
        """Test: complete_session raises AuthSessionNotFoundError if session not found."""
        user_info = UserInfo(
            user_id="ou_test",
            open_id="ou_test",
            union_id="on_test",
            user_name="Test",
        )

        with pytest.raises(AuthSessionNotFoundError):
            session_manager.complete_session(
                session_id="non-existent-session-id",
                user_access_token="u-token",
                token_expires_at=datetime.now(UTC) + timedelta(days=7),
                user_info=user_info,
            )

    def test_complete_session_raises_if_expired(self, session_manager, db_session):
        """Test: complete_session raises AuthSessionExpiredError if session expired."""
        # Create expired session
        now = datetime.now(UTC).replace(tzinfo=None)
        session = UserAuthSession(
            session_id=str(uuid.uuid4()),
            app_id="cli_test123456789",
            user_id="ou_test",
            state="pending",
            auth_method="websocket_card",
            created_at=now - timedelta(minutes=15),
            expires_at=now - timedelta(minutes=5),  # Already expired
        )
        db_session.add(session)
        db_session.commit()

        user_info = UserInfo(
            user_id="ou_test",
            open_id="ou_test",
            union_id="on_test",
            user_name="Test",
        )

        with pytest.raises(AuthSessionExpiredError):
            session_manager.complete_session(
                session_id=session.session_id,
                user_access_token="u-token",
                token_expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(days=7),
                user_info=user_info,
            )


# T027: Unit test for get_active_token
class TestGetActiveToken:
    """Test suite for AuthSessionManager.get_active_token()."""

    def test_get_active_token_returns_valid_token(self, session_manager, db_session):
        """Test: get_active_token returns valid token for user."""
        # Create completed session with valid token
        now = datetime.now(UTC).replace(tzinfo=None)
        session = UserAuthSession(
            session_id=str(uuid.uuid4()),
            app_id="cli_test123456789",
            user_id="ou_test_user_123",
            state="completed",
            auth_method="websocket_card",
            user_access_token="u-valid-token-123",
            token_expires_at=now + timedelta(days=7),
            created_at=now,
            expires_at=now + timedelta(minutes=10),
            completed_at=now,
        )
        db_session.add(session)
        db_session.commit()

        # Get active token
        token = session_manager.get_active_token(
            app_id="cli_test123456789",
            user_id="ou_test_user_123",
        )

        assert token == "u-valid-token-123"

    def test_get_active_token_returns_none_if_expired(self, session_manager, db_session):
        """Test: get_active_token returns None if token expired."""
        # Create completed session with expired token
        now = datetime.now(UTC).replace(tzinfo=None)
        session = UserAuthSession(
            session_id=str(uuid.uuid4()),
            app_id="cli_test123456789",
            user_id="ou_test_user_123",
            state="completed",
            auth_method="websocket_card",
            user_access_token="u-expired-token",
            token_expires_at=now - timedelta(days=1),  # Expired
            created_at=now - timedelta(days=8),
            expires_at=now - timedelta(days=7),
            completed_at=now - timedelta(days=7),
        )
        db_session.add(session)
        db_session.commit()

        # Get active token
        token = session_manager.get_active_token(
            app_id="cli_test123456789",
            user_id="ou_test_user_123",
        )

        assert token is None

    def test_get_active_token_returns_none_if_no_session(self, session_manager):
        """Test: get_active_token returns None if no session exists."""
        token = session_manager.get_active_token(
            app_id="cli_test123456789",
            user_id="ou_nonexistent_user",
        )

        assert token is None

    def test_get_active_token_returns_most_recent(self, session_manager, db_session):
        """Test: get_active_token returns most recent token when multiple exist."""
        # Create two completed sessions
        now = datetime.now(UTC).replace(tzinfo=None)
        old_session = UserAuthSession(
            session_id=str(uuid.uuid4()),
            app_id="cli_test123456789",
            user_id="ou_test_user_123",
            state="completed",
            auth_method="websocket_card",
            user_access_token="u-old-token",
            token_expires_at=now + timedelta(days=7),
            created_at=now - timedelta(days=2),
            expires_at=now - timedelta(days=1),
            completed_at=now - timedelta(days=2),
        )
        new_session = UserAuthSession(
            session_id=str(uuid.uuid4()),
            app_id="cli_test123456789",
            user_id="ou_test_user_123",
            state="completed",
            auth_method="websocket_card",
            user_access_token="u-new-token",
            token_expires_at=now + timedelta(days=7),
            created_at=now,
            expires_at=now + timedelta(minutes=10),
            completed_at=now,
        )
        db_session.add_all([old_session, new_session])
        db_session.commit()

        # Get active token
        token = session_manager.get_active_token(
            app_id="cli_test123456789",
            user_id="ou_test_user_123",
        )

        assert token == "u-new-token"


# T028: Unit test for cleanup_expired_sessions
class TestCleanupExpiredSessions:
    """Test suite for AuthSessionManager.cleanup_expired_sessions()."""

    def test_cleanup_expired_sessions_marks_as_expired(self, session_manager, db_session):
        """Test: cleanup_expired_sessions marks expired pending sessions as expired."""
        # Create expired pending session
        now = datetime.now(UTC).replace(tzinfo=None)
        expired_session = UserAuthSession(
            session_id=str(uuid.uuid4()),
            app_id="cli_test123456789",
            user_id="ou_test_user_123",
            state="pending",
            auth_method="websocket_card",
            created_at=now - timedelta(minutes=15),
            expires_at=now - timedelta(minutes=5),  # Expired
        )
        # Create valid pending session
        valid_session = UserAuthSession(
            session_id=str(uuid.uuid4()),
            app_id="cli_test123456789",
            user_id="ou_test_user_456",
            state="pending",
            auth_method="websocket_card",
            created_at=now,
            expires_at=now + timedelta(minutes=10),  # Not expired
        )
        db_session.add_all([expired_session, valid_session])
        db_session.commit()

        # Cleanup expired sessions
        count = session_manager.cleanup_expired_sessions()

        # Verify cleanup
        assert count == 1
        db_session.expire_all()
        expired = (
            db_session.query(UserAuthSession)
            .filter_by(session_id=expired_session.session_id)
            .first()
        )
        valid = (
            db_session.query(UserAuthSession).filter_by(session_id=valid_session.session_id).first()
        )
        assert expired.state == "expired"
        assert valid.state == "pending"

    def test_cleanup_expired_sessions_returns_count(self, session_manager, db_session):
        """Test: cleanup_expired_sessions returns count of cleaned sessions."""
        # Create 3 expired sessions
        now = datetime.now(UTC).replace(tzinfo=None)
        for i in range(3):
            session = UserAuthSession(
                session_id=str(uuid.uuid4()),
                app_id="cli_test123456789",
                user_id=f"ou_test_user_{i}",
                state="pending",
                auth_method="websocket_card",
                created_at=now - timedelta(minutes=15),
                expires_at=now - timedelta(minutes=5),
            )
            db_session.add(session)
        db_session.commit()

        # Cleanup
        count = session_manager.cleanup_expired_sessions()

        assert count == 3


# T029: Unit test for multi-user isolation
class TestMultiUserIsolation:
    """Test suite for multi-user and multi-app isolation."""

    def test_get_active_token_isolates_by_app_id(self, session_manager, db_session):
        """Test: get_active_token isolates tokens by app_id."""
        # Create sessions for different apps
        now = datetime.now(UTC).replace(tzinfo=None)
        session_app1 = UserAuthSession(
            session_id=str(uuid.uuid4()),
            app_id="cli_app1_12345678",
            user_id="ou_test_user_123",
            state="completed",
            auth_method="websocket_card",
            user_access_token="u-app1-token",
            token_expires_at=now + timedelta(days=7),
            created_at=now,
            expires_at=now + timedelta(minutes=10),
            completed_at=now,
        )
        session_app2 = UserAuthSession(
            session_id=str(uuid.uuid4()),
            app_id="cli_app2_87654321",
            user_id="ou_test_user_123",
            state="completed",
            auth_method="websocket_card",
            user_access_token="u-app2-token",
            token_expires_at=now + timedelta(days=7),
            created_at=now,
            expires_at=now + timedelta(minutes=10),
            completed_at=now,
        )
        db_session.add_all([session_app1, session_app2])
        db_session.commit()

        # Get tokens for different apps
        token_app1 = session_manager.get_active_token(
            app_id="cli_app1_12345678",
            user_id="ou_test_user_123",
        )
        token_app2 = session_manager.get_active_token(
            app_id="cli_app2_87654321",
            user_id="ou_test_user_123",
        )

        assert token_app1 == "u-app1-token"
        assert token_app2 == "u-app2-token"

    def test_get_active_token_isolates_by_user_id(self, session_manager, db_session):
        """Test: get_active_token isolates tokens by user_id."""
        # Create sessions for different users
        now = datetime.now(UTC).replace(tzinfo=None)
        session_user1 = UserAuthSession(
            session_id=str(uuid.uuid4()),
            app_id="cli_test123456789",
            user_id="ou_user1_123",
            state="completed",
            auth_method="websocket_card",
            user_access_token="u-user1-token",
            token_expires_at=now + timedelta(days=7),
            created_at=now,
            expires_at=now + timedelta(minutes=10),
            completed_at=now,
        )
        session_user2 = UserAuthSession(
            session_id=str(uuid.uuid4()),
            app_id="cli_test123456789",
            user_id="ou_user2_456",
            state="completed",
            auth_method="websocket_card",
            user_access_token="u-user2-token",
            token_expires_at=now + timedelta(days=7),
            created_at=now,
            expires_at=now + timedelta(minutes=10),
            completed_at=now,
        )
        db_session.add_all([session_user1, session_user2])
        db_session.commit()

        # Get tokens for different users
        token_user1 = session_manager.get_active_token(
            app_id="cli_test123456789",
            user_id="ou_user1_123",
        )
        token_user2 = session_manager.get_active_token(
            app_id="cli_test123456789",
            user_id="ou_user2_456",
        )

        assert token_user1 == "u-user1-token"
        assert token_user2 == "u-user2-token"
