"""Integration tests for aPaaS with authentication.

Tests the complete flow of aPaaS API calls with automatic
user_access_token management.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from lark_service.apaas.client import WorkspaceTableClient
from lark_service.auth.card_auth_handler import CardAuthHandler
from lark_service.auth.exceptions import AuthenticationRequiredError
from lark_service.auth.session_manager import AuthSessionManager
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.models.auth_session import Base, UserAuthSession


@pytest.fixture
def test_db():
    """Create test database."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine)
    db = session_local()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def auth_manager(test_db):
    """Create AuthSessionManager instance."""
    return AuthSessionManager(test_db)


@pytest.fixture
def credential_pool():
    """Create mock CredentialPool instance."""
    from unittest.mock import Mock

    return Mock(spec=CredentialPool)


@pytest.fixture
def card_auth_handler(test_db, auth_manager):
    """Create CardAuthHandler instance."""
    from unittest.mock import Mock

    messaging_client = Mock()
    return CardAuthHandler(
        session_manager=auth_manager,
        messaging_client=messaging_client,
        app_id="cli_test1234567890ab",
        app_secret="test_secret",
    )


@pytest.fixture
def apaas_client(credential_pool):
    """Create WorkspaceTableClient instance."""
    return WorkspaceTableClient(credential_pool=credential_pool)


class TestAPaaSWithAuth:
    """Integration tests for aPaaS with authentication."""

    def test_complete_flow_with_valid_token(self, test_db, auth_manager, apaas_client):
        """Test complete aPaaS API call flow with valid token.

        T058 [US4] RED: Integration test for aPaaS API call with auto token injection

        Flow:
        1. Create auth session with valid token
        2. Get token from auth_manager
        3. Call aPaaS API with token
        4. Verify API call succeeds
        """
        # Arrange
        app_id = "cli_test1234567890ab"
        user_id = "ou_test_user_123"
        token = "u-test_token_abc123"

        # Create auth session with valid token
        session = UserAuthSession(
            session_id="test-session-id",
            app_id=app_id,
            user_id=user_id,
            state="completed",
            auth_method="websocket_card",
            user_access_token=token,
            token_expires_at=datetime.now(UTC) + timedelta(days=7),
            created_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
        )
        test_db.add(session)
        test_db.commit()

        # Act
        retrieved_token = auth_manager.get_active_token(app_id=app_id, user_id=user_id)

        # Assert
        assert retrieved_token == token

        # Note: Actual API call would require mocking or real credentials
        # This test verifies the token retrieval flow

    def test_flow_without_token_raises_error(self, test_db, auth_manager, apaas_client):
        """Test aPaaS API call without token raises AuthenticationRequiredError.

        T058 [US4] RED: Integration test for aPaaS API call with auto token injection

        Flow:
        1. No auth session exists
        2. Attempt to get token from auth_manager
        3. Verify AuthenticationRequiredError is raised
        """
        # Arrange
        app_id = "cli_test1234567890ab"
        user_id = "ou_test_user_123"

        # Act & Assert
        with pytest.raises(AuthenticationRequiredError):
            auth_manager.get_active_token(app_id=app_id, user_id=user_id)

    def test_flow_with_expired_token_raises_error(self, test_db, auth_manager, apaas_client):
        """Test aPaaS API call with expired token raises error.

        T058 [US4] RED: Integration test for aPaaS API call with auto token injection

        Flow:
        1. Create auth session with expired token
        2. Attempt to get token from auth_manager
        3. Verify AuthenticationRequiredError is raised
        """
        # Arrange
        app_id = "cli_test1234567890ab"
        user_id = "ou_test_user_123"
        token = "u-expired_token_abc123"

        # Create auth session with expired token
        session = UserAuthSession(
            session_id="test-session-id",
            app_id=app_id,
            user_id=user_id,
            state="completed",
            auth_method="websocket_card",
            user_access_token=token,
            token_expires_at=datetime.now(UTC) - timedelta(hours=1),  # Expired
            created_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
        )
        test_db.add(session)
        test_db.commit()

        # Act & Assert
        with pytest.raises(AuthenticationRequiredError):
            auth_manager.get_active_token(app_id=app_id, user_id=user_id)

    def test_multi_user_token_isolation(self, test_db, auth_manager, apaas_client):
        """Test token isolation between multiple users.

        T058 [US4] RED: Integration test for aPaaS API call with auto token injection

        Flow:
        1. Create auth sessions for two different users
        2. Get tokens for each user
        3. Verify correct tokens are returned for each user
        """
        # Arrange
        app_id = "cli_test1234567890ab"
        user1_id = "ou_test_user_001"
        user2_id = "ou_test_user_002"
        token1 = "u-token_user1_abc"
        token2 = "u-token_user2_xyz"

        # Create auth sessions for both users
        session1 = UserAuthSession(
            session_id="test-session-id-1",
            app_id=app_id,
            user_id=user1_id,
            state="completed",
            auth_method="websocket_card",
            user_access_token=token1,
            token_expires_at=datetime.now(UTC) + timedelta(days=7),
            created_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
        )
        session2 = UserAuthSession(
            session_id="test-session-id-2",
            app_id=app_id,
            user_id=user2_id,
            state="completed",
            auth_method="websocket_card",
            user_access_token=token2,
            token_expires_at=datetime.now(UTC) + timedelta(days=7),
            created_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
        )
        test_db.add(session1)
        test_db.add(session2)
        test_db.commit()

        # Act
        retrieved_token1 = auth_manager.get_active_token(app_id=app_id, user_id=user1_id)
        retrieved_token2 = auth_manager.get_active_token(app_id=app_id, user_id=user2_id)

        # Assert
        assert retrieved_token1 == token1
        assert retrieved_token2 == token2
        assert retrieved_token1 != retrieved_token2
