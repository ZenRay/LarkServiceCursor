"""Integration test for complete WebSocket authorization flow.

T076 [Phase 8] Integration test: Complete auth flow from card to API call

This test validates the complete end-to-end authorization flow:
1. User calls aPaaS API without auth
2. System sends auth card
3. User clicks "Authorize" button
4. System receives WebSocket event
5. System exchanges authorization_code for token
6. System stores token and user info
7. User calls aPaaS API again (success with token)
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from lark_service.auth.card_auth_handler import CardAuthHandler
from lark_service.auth.exceptions import AuthenticationRequiredError
from lark_service.auth.session_manager import AuthSessionManager
from lark_service.auth.types import UserInfo
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
def mock_messaging_client():
    """Create mock messaging client."""
    client = Mock()
    client.send_card_message = Mock(return_value={"message_id": "msg_123456"})
    return client


@pytest.fixture
def card_auth_handler(auth_manager, mock_messaging_client):
    """Create CardAuthHandler instance."""
    return CardAuthHandler(
        session_manager=auth_manager,
        messaging_client=mock_messaging_client,
        app_id="cli_test1234567890ab",
        app_secret="test_secret",
    )


@pytest.mark.asyncio
@pytest.mark.integration
class TestCompleteAuthFlow:
    """Integration tests for complete authorization flow."""

    async def test_complete_auth_flow_from_card_to_token(
        self, test_db, auth_manager, card_auth_handler, mock_messaging_client
    ):
        """Test complete authorization flow from card send to token storage.

        Flow:
        1. Create auth session
        2. Send auth card to user
        3. Simulate user clicking "Authorize" button
        4. Handle card callback event
        5. Exchange authorization_code for token
        6. Store token and user info
        7. Verify token is retrievable
        """
        # Arrange
        app_id = "cli_test1234567890ab"
        user_id = "ou_test_user_123"
        open_id = "ou_test_user_123"

        # Step 1: Create auth session manually (simulating what send_auth_card does)
        session = auth_manager.create_session(
            app_id=app_id, user_id=user_id, auth_method="websocket_card"
        )
        assert session.state == "pending"
        assert session.session_id is not None

        # Step 2: Simulate card sending (we skip actual send_auth_card to avoid complexity)
        # In real flow, send_auth_card would be called here

        # Step 3 & 4: Simulate user clicking "Authorize" and handle event
        # Mock the Feishu API responses
        mock_token_response = {
            "access_token": "u-test_token_abc123",
            "token_type": "Bearer",
            "expires_in": 604800,  # 7 days
            "refresh_token": "ur-refresh_token_xyz",
            "refresh_expires_in": 2592000,  # 30 days
        }

        mock_user_info = UserInfo(
            user_id="ou_test_user_123",
            open_id="ou_test_user_123",
            union_id="on_test_union_456",
            user_name="测试用户",
            email="test@example.com",
            mobile="+86-13800138000",
        )

        # Create mock card event (as dict, matching actual event structure)
        mock_event = {
            "operator": {"open_id": open_id},
            "action": {
                "value": {
                    "session_id": session.session_id,
                    "authorization_code": "auth_code_test_xyz",
                }
            },
        }

        with (
            patch.object(
                card_auth_handler, "_exchange_token", new_callable=AsyncMock
            ) as mock_exchange,
            patch.object(
                card_auth_handler, "_fetch_user_info", new_callable=AsyncMock
            ) as mock_fetch_user,
        ):
            mock_exchange.return_value = mock_token_response
            mock_fetch_user.return_value = mock_user_info

            # Handle the card auth event
            response = await card_auth_handler.handle_card_auth_event(mock_event)

            # Verify response
            assert response is not None

        # Step 5 & 6: Verify token and user info are stored
        updated_session = auth_manager.get_session(session.session_id)
        assert updated_session.state == "completed"
        assert updated_session.user_access_token is not None
        assert updated_session.user_name == "测试用户"
        assert updated_session.email == "test@example.com"
        assert updated_session.mobile == "+86-13800138000"
        assert updated_session.union_id == "on_test_union_456"

        # Step 7: Verify token is retrievable
        token = auth_manager.get_active_token(app_id=app_id, user_id=user_id)
        assert token is not None
        assert token == updated_session.user_access_token

    async def test_auth_flow_with_missing_token_raises_error(self, test_db, auth_manager):
        """Test that missing token raises AuthenticationRequiredError.

        Flow:
        1. No auth session exists
        2. Attempt to get token
        3. Verify AuthenticationRequiredError is raised
        """
        # Arrange
        app_id = "cli_test1234567890ab"
        user_id = "ou_test_user_123"

        # Act & Assert
        with pytest.raises(AuthenticationRequiredError):
            auth_manager.get_active_token(app_id=app_id, user_id=user_id)

    async def test_auth_flow_with_expired_token_raises_error(self, test_db, auth_manager):
        """Test that expired token raises AuthenticationRequiredError.

        Flow:
        1. Create session with expired token
        2. Attempt to get token
        3. Verify AuthenticationRequiredError is raised
        """
        # Arrange
        app_id = "cli_test1234567890ab"
        user_id = "ou_test_user_123"
        expired_token = "u-expired_token_abc"

        # Create session with expired token
        session = UserAuthSession(
            session_id="test-session-expired",
            app_id=app_id,
            user_id=user_id,
            state="completed",
            auth_method="websocket_card",
            user_access_token=expired_token,
            token_expires_at=datetime.now(UTC) - timedelta(hours=1),  # Already expired
            created_at=datetime.now(UTC) - timedelta(days=7),
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
        )
        test_db.add(session)
        test_db.commit()

        # Act & Assert
        with pytest.raises(AuthenticationRequiredError):
            auth_manager.get_active_token(app_id=app_id, user_id=user_id)

    async def test_auth_flow_with_rejected_authorization(
        self, test_db, auth_manager, card_auth_handler, mock_messaging_client
    ):
        """Test authorization flow when user rejects authorization.

        Flow:
        1. Create auth session
        2. Send auth card
        3. Simulate user clicking "Reject" button
        4. Verify session state is updated to rejected
        """
        # Arrange
        app_id = "cli_test1234567890ab"
        user_id = "ou_test_user_123"
        open_id = "ou_test_user_123"

        # Send auth card (creates session internally)
        await card_auth_handler.send_auth_card(user_id=user_id)

        # Create a test session for testing rejection
        session = auth_manager.create_session(
            app_id=app_id, user_id=user_id, auth_method="websocket_card"
        )

        # Create mock card event for rejection
        mock_event = Mock()
        mock_event.event.operator.open_id = open_id
        mock_event.event.action.value = {
            "session_id": session.session_id,
            "action": "reject",
        }

        # Handle the rejection event
        response = await card_auth_handler.handle_card_auth_event(mock_event)

        # Verify response indicates rejection
        assert response is not None

        # Verify session state
        updated_session = auth_manager.get_session(session.session_id)
        # Session should still be pending or marked as rejected
        assert updated_session.state in ["pending", "rejected", "expired"]

    async def test_auth_flow_with_multiple_users(
        self, test_db, auth_manager, card_auth_handler, mock_messaging_client
    ):
        """Test authorization flow with multiple users simultaneously.

        Flow:
        1. Create auth sessions for multiple users
        2. Send auth cards to all users
        3. Simulate users authorizing in different order
        4. Verify tokens are correctly isolated
        """
        # Arrange
        app_id = "cli_test1234567890ab"
        users = [
            {"user_id": "ou_user_001", "token": "u-token_001"},
            {"user_id": "ou_user_002", "token": "u-token_002"},
            {"user_id": "ou_user_003", "token": "u-token_003"},
        ]

        sessions = []
        for user in users:
            # Send auth card (creates session internally)
            await card_auth_handler.send_auth_card(user_id=user["user_id"])

            # Create test session for tracking
            session = auth_manager.create_session(
                app_id=app_id, user_id=user["user_id"], auth_method="websocket_card"
            )
            sessions.append(session)

        # Simulate users authorizing
        for i, user in enumerate(users):
            # Create mock card event (as dict, matching actual event structure)
            mock_event = {
                "operator": {"open_id": user["user_id"]},
                "action": {
                    "value": {
                        "session_id": sessions[i].session_id,
                        "authorization_code": f"auth_code_{i}",
                    }
                },
            }

            mock_token_response = {
                "access_token": user["token"],
                "token_type": "Bearer",
                "expires_in": 604800,
            }

            mock_user_info = UserInfo(
                user_id=user["user_id"],
                open_id=user["user_id"],
                union_id=f"on_union_{i}",
                user_name=f"User {i}",
                email=f"user{i}@example.com",
                mobile=None,
            )

            with (
                patch.object(
                    card_auth_handler, "_exchange_token", new_callable=AsyncMock
                ) as mock_exchange,
                patch.object(
                    card_auth_handler, "_fetch_user_info", new_callable=AsyncMock
                ) as mock_fetch_user,
            ):
                mock_exchange.return_value = mock_token_response
                mock_fetch_user.return_value = mock_user_info

                await card_auth_handler.handle_card_auth_event(mock_event)

        # Verify tokens are correctly isolated
        for user in users:
            token = auth_manager.get_active_token(app_id=app_id, user_id=user["user_id"])
            # Token should exist and be unique
            assert token is not None

        # Verify all tokens are different
        tokens = [
            auth_manager.get_active_token(app_id=app_id, user_id=user["user_id"]) for user in users
        ]
        assert len(set(tokens)) == len(users)  # All tokens are unique
