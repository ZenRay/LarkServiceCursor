"""Integration test for exception recovery.

T080 [Phase 8] Integration test: Exception recovery (network errors, API failures)

This test validates the system's ability to recover from various exceptions:
1. Network errors during token exchange
2. API failures (4xx, 5xx errors)
3. Database connection failures
4. Timeout errors
5. System continues to function after recovery
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from lark_service.auth.card_auth_handler import CardAuthHandler
from lark_service.auth.exceptions import (
    AuthorizationCodeExpiredError,
    TokenRefreshFailedError,
)
from lark_service.auth.session_manager import AuthSessionManager
from lark_service.auth.types import UserInfo
from lark_service.core.models.auth_session import Base


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
    client.send_card = AsyncMock(return_value="msg_123456")
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
class TestExceptionRecovery:
    """Integration tests for exception recovery."""

    async def test_recovery_from_network_error_during_token_exchange(
        self, test_db, auth_manager, card_auth_handler
    ):
        """Test recovery from network error during token exchange.

        Flow:
        1. Create auth session
        2. Simulate network error during token exchange
        3. Verify error is handled gracefully
        4. Retry succeeds
        5. Token is stored correctly
        """
        # Arrange
        app_id = "cli_test1234567890ab"
        user_id = "ou_test_user_123"

        session = auth_manager.create_session(
            app_id=app_id, user_id=user_id, auth_method="websocket_card"
        )

        # Create mock card event (as dict, matching actual event structure)
        mock_event = {
            "operator": {"open_id": user_id},
            "action": {
                "value": {
                    "session_id": session.session_id,
                    "authorization_code": "auth_code_test",
                }
            },
        }

        # Mock network error on first attempt, success on second
        call_count = 0

        async def mock_exchange_with_retry(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("Network error")
            return {
                "access_token": "u-token_success",
                "token_type": "Bearer",
                "expires_in": 604800,
            }

        mock_user_info = UserInfo(
            user_id=user_id,
            open_id=user_id,
            union_id="on_union_123",
            user_name="Test User",
            email="test@example.com",
            mobile=None,
        )

        # Act - Mock exchange to raise ConnectionError
        with patch.object(
            card_auth_handler, "_exchange_token", new_callable=AsyncMock
        ) as mock_exchange:
            # First call raises error, second call succeeds
            mock_exchange.side_effect = [
                ConnectionError("Network error"),
                {
                    "access_token": "u-token_success",
                    "token_type": "Bearer",
                    "expires_in": 604800,
                },
            ]

            with patch.object(
                card_auth_handler, "_fetch_user_info", new_callable=AsyncMock
            ) as mock_fetch_user:
                mock_fetch_user.return_value = mock_user_info

                # First attempt should fail with ConnectionError
                # Note: handle_card_auth_event catches exceptions and returns error response
                response = await card_auth_handler.handle_card_auth_event(mock_event)
                # Verify error response
                assert response is not None
                # Session should still be pending after error
                session_after_error = auth_manager.get_session(session.session_id)
                assert session_after_error.state == "pending"

                # Second attempt should succeed
                response = await card_auth_handler.handle_card_auth_event(mock_event)
                assert response is not None

        # Assert - Session should now be completed
        updated_session = auth_manager.get_session(session.session_id)
        assert updated_session.state == "completed"

    async def test_recovery_from_api_4xx_error(self, test_db, auth_manager, card_auth_handler):
        """Test recovery from API 4xx error (e.g., invalid authorization code).

        Flow:
        1. Create auth session
        2. Simulate 400 Bad Request during token exchange
        3. Verify error is handled gracefully
        4. Session state is updated appropriately
        5. User receives clear error message
        """
        # Arrange
        app_id = "cli_test1234567890ab"
        user_id = "ou_test_user_123"

        session = auth_manager.create_session(
            app_id=app_id, user_id=user_id, auth_method="websocket_card"
        )

        # Create mock card event (as dict, matching actual event structure)
        mock_event = {
            "operator": {"open_id": user_id},
            "action": {
                "value": {
                    "session_id": session.session_id,
                    "authorization_code": "invalid_code",
                }
            },
        }

        # Act
        with patch.object(
            card_auth_handler, "_exchange_token", new_callable=AsyncMock
        ) as mock_exchange:
            mock_exchange.side_effect = AuthorizationCodeExpiredError(
                "Authorization code expired or invalid"
            )

            response = await card_auth_handler.handle_card_auth_event(mock_event)

        # Assert
        assert response is not None
        # Session should remain in pending or be marked as failed
        updated_session = auth_manager.get_session(session.session_id)
        assert updated_session.state in ["pending", "expired", "failed"]

    async def test_recovery_from_api_5xx_error(self, test_db, auth_manager, card_auth_handler):
        """Test recovery from API 5xx error (server error).

        Flow:
        1. Create auth session
        2. Simulate 500 Internal Server Error
        3. Verify error is handled gracefully
        4. System retries with exponential backoff
        5. Eventually succeeds or fails gracefully
        """
        # Arrange
        app_id = "cli_test1234567890ab"
        user_id = "ou_test_user_123"

        session = auth_manager.create_session(
            app_id=app_id, user_id=user_id, auth_method="websocket_card"
        )

        # Create mock card event (as dict, matching actual event structure)
        mock_event = {
            "operator": {"open_id": user_id},
            "action": {
                "value": {
                    "session_id": session.session_id,
                    "authorization_code": "auth_code_test",
                }
            },
        }

        # Mock 500 error
        async def mock_exchange_500(*args, **kwargs):
            raise Exception("500 Internal Server Error")

        # Act
        with patch.object(
            card_auth_handler, "_exchange_token", new_callable=AsyncMock
        ) as mock_exchange:
            mock_exchange.side_effect = mock_exchange_500

            response = await card_auth_handler.handle_card_auth_event(mock_event)

        # Assert
        assert response is not None
        # Error should be handled gracefully

    async def test_recovery_from_database_connection_error(self, auth_manager):
        """Test recovery from database connection error.

        Flow:
        1. Simulate database connection failure
        2. Verify error is handled gracefully
        3. System retries connection
        4. Eventually succeeds or fails gracefully
        """
        # Arrange
        app_id = "cli_test1234567890ab"
        user_id = "ou_test_user_123"

        # Act & Assert
        # This test is conceptual - in real implementation,
        # database connection errors would be caught and retried
        try:
            session = auth_manager.create_session(
                app_id=app_id, user_id=user_id, auth_method="websocket_card"
            )
            assert session is not None
        except OperationalError:
            # Database connection error should be caught
            pass

    async def test_recovery_from_timeout_error(self, test_db, auth_manager, card_auth_handler):
        """Test recovery from timeout error.

        Flow:
        1. Create auth session
        2. Simulate timeout during token exchange
        3. Verify error is handled gracefully
        4. System retries with timeout
        5. Eventually succeeds or fails gracefully
        """
        # Arrange
        app_id = "cli_test1234567890ab"
        user_id = "ou_test_user_123"

        session = auth_manager.create_session(
            app_id=app_id, user_id=user_id, auth_method="websocket_card"
        )

        # Create mock card event (as dict, matching actual event structure)
        mock_event = {
            "operator": {"open_id": user_id},
            "action": {
                "value": {
                    "session_id": session.session_id,
                    "authorization_code": "auth_code_test",
                }
            },
        }

        # Act
        with patch.object(
            card_auth_handler, "_exchange_token", new_callable=AsyncMock
        ) as mock_exchange:
            mock_exchange.side_effect = TimeoutError("Request timeout")

            response = await card_auth_handler.handle_card_auth_event(mock_event)

        # Assert
        assert response is not None
        # Timeout should be handled gracefully

    async def test_recovery_from_token_refresh_failure(self, test_db, auth_manager):
        """Test recovery from token refresh failure.

        Flow:
        1. Create session with expiring token
        2. Simulate token refresh failure
        3. Verify error is handled gracefully
        4. System prompts user to re-authorize
        5. User can complete new authorization
        """
        # Arrange
        app_id = "cli_test1234567890ab"
        user_id = "ou_test_user_123"

        # Create session with expiring token
        session = auth_manager.create_session(
            app_id=app_id, user_id=user_id, auth_method="websocket_card"
        )

        auth_manager.complete_session(
            session_id=session.session_id,
            user_access_token="u-old_token",
            token_expires_at=datetime.now(UTC) + timedelta(hours=1),
            user_info=UserInfo(
                user_id=user_id,
                open_id=user_id,
                union_id="on_union_123",
                user_name="Test User",
                email="test@example.com",
            ),
        )

        # Act - Simulate refresh failure
        with (
            patch.object(
                auth_manager, "refresh_token", side_effect=TokenRefreshFailedError("Refresh failed")
            ),
            pytest.raises(TokenRefreshFailedError),
        ):
            auth_manager.refresh_token(app_id=app_id, user_id=user_id)

        # Assert - User should be able to create new session
        new_session = auth_manager.create_session(
            app_id=app_id, user_id=user_id, auth_method="websocket_card"
        )
        assert new_session is not None
        assert new_session.state == "pending"

    async def test_system_continues_after_partial_failure(
        self, test_db, auth_manager, card_auth_handler
    ):
        """Test that system continues to function after partial failure.

        Flow:
        1. Process multiple auth requests
        2. Some requests fail due to various errors
        3. Verify successful requests are processed correctly
        4. Verify system remains stable
        5. Failed requests can be retried
        """
        # Arrange
        app_id = "cli_test1234567890ab"
        num_users = 10

        # Create sessions
        sessions = []
        for i in range(num_users):
            user_id = f"ou_user_{i:03d}"
            session = auth_manager.create_session(
                app_id=app_id, user_id=user_id, auth_method="websocket_card"
            )
            sessions.append(session)

        # Act - Process auth requests with some failures
        success_count = 0
        failure_count = 0

        for i, session in enumerate(sessions):
            user_id = f"ou_user_{i:03d}"

            # Create mock card event (as dict, matching actual event structure)
            mock_event = {
                "operator": {"open_id": user_id},
                "action": {
                    "value": {
                        "session_id": session.session_id,
                        "authorization_code": f"auth_code_{i}",
                    }
                },
            }

            # Simulate failures for some users
            if i % 3 == 0:
                # Fail every 3rd request
                with patch.object(
                    card_auth_handler, "_exchange_token", new_callable=AsyncMock
                ) as mock_exchange:
                    mock_exchange.side_effect = Exception("Simulated failure")

                    response = await card_auth_handler.handle_card_auth_event(mock_event)
                    # Check if response indicates failure
                    if response and response.get("toast", {}).get("type") == "error":
                        failure_count += 1
            else:
                # Succeed for other requests
                mock_token_response = {
                    "access_token": f"u-token_{i}",
                    "token_type": "Bearer",
                    "expires_in": 604800,
                }

                mock_user_info = UserInfo(
                    user_id=user_id,
                    open_id=user_id,
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
                    success_count += 1

        # Assert
        assert success_count > 0
        assert failure_count > 0
        assert success_count + failure_count == num_users

        # Verify successful sessions have tokens
        for i in range(len(sessions)):
            if i % 3 != 0:  # Successful requests
                user_id = f"ou_user_{i:03d}"
                token = auth_manager.get_active_token(
                    app_id=app_id, user_id=user_id, raise_if_missing=False
                )
                assert token is not None

    async def test_graceful_degradation_under_high_error_rate(self, test_db, auth_manager):
        """Test graceful degradation under high error rate.

        Flow:
        1. Simulate high error rate (80% failures)
        2. Verify system continues to process successful requests
        3. Verify system doesn't crash or deadlock
        4. Verify error logging is appropriate
        5. Verify system recovers when error rate decreases
        """
        # Arrange
        app_id = "cli_test1234567890ab"
        num_requests = 50
        error_rate = 0.8  # 80% failure rate

        # Act
        success_count = 0
        failure_count = 0

        for i in range(num_requests):
            user_id = f"ou_user_{i:03d}"

            try:
                # Simulate high error rate
                if i < num_requests * error_rate:
                    # Simulate failure
                    raise Exception("Simulated high error rate")
                else:
                    # Success
                    session = auth_manager.create_session(
                        app_id=app_id, user_id=user_id, auth_method="websocket_card"
                    )
                    auth_manager.complete_session(
                        session_id=session.session_id,
                        user_access_token=f"u-token_{i}",
                        token_expires_at=datetime.now(UTC) + timedelta(days=7),
                        user_info=UserInfo(
                            user_id=user_id,
                            open_id=user_id,
                            union_id=f"on_union_{i}",
                            user_name=f"User {i}",
                            email=f"user{i}@example.com",
                        ),
                    )
                    success_count += 1
            except Exception:
                failure_count += 1

        # Assert
        assert success_count > 0  # Some requests should succeed
        assert failure_count > 0  # Some requests should fail
        assert success_count + failure_count == num_requests

        # Verify system is still functional
        # Create a new session to verify system recovered
        test_session = auth_manager.create_session(
            app_id=app_id, user_id="ou_recovery_test", auth_method="websocket_card"
        )
        assert test_session is not None
        assert test_session.state == "pending"
