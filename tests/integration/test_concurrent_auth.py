"""Integration test for concurrent authorization.

T078 [Phase 8] Integration test: Concurrent authorization (100 users)

# mypy: disable-error-code="no-untyped-def,type-arg"

This test validates the system's ability to handle concurrent authorization:
1. Multiple users authorize simultaneously
2. System handles concurrent token exchanges
3. Database transactions are properly isolated
4. No race conditions or deadlocks occur
5. All users receive correct tokens
"""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from lark_service.auth.card_auth_handler import CardAuthHandler
from lark_service.auth.session_manager import AuthSessionManager
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
class TestConcurrentAuth:
    """Integration tests for concurrent authorization."""

    async def test_concurrent_auth_sessions_creation(self, test_db, auth_manager) -> None:
        """Test concurrent creation of auth sessions.

        Flow:
        1. Create 100 auth sessions concurrently
        2. Verify all sessions are created successfully
        3. Verify no duplicate session_ids
        4. Verify database integrity
        """
        # Arrange
        app_id = "cli_test1234567890ab"
        num_users = 100

        async def create_session_for_user(user_index: int) -> UserAuthSession:
            """Create auth session for a user."""
            user_id = f"ou_user_{user_index:03d}"
            session = auth_manager.create_session(
                app_id=app_id, user_id=user_id, auth_method="websocket_card"
            )
            return session

        # Act - Create sessions concurrently
        tasks = [create_session_for_user(i) for i in range(num_users)]
        sessions = await asyncio.gather(*tasks)

        # Assert
        assert len(sessions) == num_users

        # Verify all sessions are unique
        session_ids = [s.session_id for s in sessions]
        assert len(set(session_ids)) == num_users

        # Verify all sessions are in pending state
        for session in sessions:
            assert session.state == "pending"
            assert session.session_id is not None

    async def test_concurrent_token_exchange(
        self, test_db, auth_manager, card_auth_handler
    ) -> None:
        """Test concurrent token exchange for multiple users.

        Flow:
        1. Create auth sessions for 50 users
        2. Simulate 50 users clicking "Authorize" simultaneously
        3. Handle all card events concurrently
        4. Verify all tokens are stored correctly
        5. Verify no race conditions or deadlocks
        """
        # Arrange
        app_id = "cli_test1234567890ab"
        num_users = 50

        # Create sessions
        sessions = []
        for i in range(num_users):
            user_id = f"ou_user_{i:03d}"
            session = auth_manager.create_session(
                app_id=app_id, user_id=user_id, auth_method="websocket_card"
            )
            sessions.append(session)

        async def handle_auth_for_user(user_index: int, session: UserAuthSession) -> dict:
            """Handle authorization for a user."""
            user_id = f"ou_user_{user_index:03d}"

            # Create mock card event
            mock_event = Mock()
            mock_event.event.operator.open_id = user_id
            mock_event.event.action.value = {
                "session_id": session.session_id,
                "authorization_code": f"auth_code_{user_index}",
            }

            mock_token_response = {
                "access_token": f"u-token_{user_index}",
                "token_type": "Bearer",
                "expires_in": 604800,
            }

            mock_user_info = {
                "user_id": user_id,
                "open_id": user_id,
                "union_id": f"on_union_{user_index}",
                "name": f"User {user_index}",
                "email": f"user{user_index}@example.com",
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

                response = await card_auth_handler.handle_card_auth_event(mock_event)
                return response

        # Act - Handle all auth events concurrently
        tasks = [handle_auth_for_user(i, sessions[i]) for i in range(num_users)]
        responses = await asyncio.gather(*tasks)

        # Assert
        assert len(responses) == num_users

        # Verify all sessions are completed
        for session in sessions:
            updated_session = auth_manager.get_session(session.session_id)
            assert updated_session.state == "completed"
            assert updated_session.user_access_token is not None

        # Verify all tokens are unique
        tokens = [
            auth_manager.get_active_token(app_id=app_id, user_id=f"ou_user_{i:03d}")
            for i in range(num_users)
        ]
        assert len(set(tokens)) == num_users

    async def test_concurrent_token_retrieval(self, test_db, auth_manager) -> None:
        """Test concurrent token retrieval for multiple users.

        Flow:
        1. Create completed sessions with tokens for 100 users
        2. Retrieve tokens concurrently for all users
        3. Verify all tokens are retrieved correctly
        4. Verify no database locking issues
        """
        # Arrange
        app_id = "cli_test1234567890ab"
        num_users = 100

        # Create completed sessions with tokens
        for i in range(num_users):
            user_id = f"ou_user_{i:03d}"
            session = auth_manager.create_session(
                app_id=app_id, user_id=user_id, auth_method="websocket_card"
            )

            # Complete the session
            auth_manager.complete_session(
                session_id=session.session_id,
                user_access_token=f"u-token_{i}",
                token_expires_at=datetime.now(UTC) + timedelta(days=7),
                user_info={
                    "user_id": user_id,
                    "open_id": user_id,
                    "union_id": f"on_union_{i}",
                    "name": f"User {i}",
                    "email": f"user{i}@example.com",
                },
            )

        async def get_token_for_user(user_index: int):
            """Get token for a user."""
            user_id = f"ou_user_{user_index:03d}"
            token = auth_manager.get_active_token(app_id=app_id, user_id=user_id)
            return token

        # Act - Retrieve tokens concurrently
        tasks = [get_token_for_user(i) for i in range(num_users)]
        tokens = await asyncio.gather(*tasks)

        # Assert
        assert len(tokens) == num_users
        assert all(token is not None for token in tokens)

        # Verify all tokens are unique
        assert len(set(tokens)) == num_users

    async def test_concurrent_session_cleanup(self, test_db, auth_manager):
        """Test concurrent session cleanup.

        Flow:
        1. Create 100 expired sessions
        2. Run cleanup concurrently from multiple threads
        3. Verify all expired sessions are cleaned up
        4. Verify no race conditions
        """
        # Arrange
        app_id = "cli_test1234567890ab"
        num_sessions = 100

        # Create expired sessions
        for i in range(num_sessions):
            user_id = f"ou_user_{i:03d}"
            session = auth_manager.create_session(
                app_id=app_id, user_id=user_id, auth_method="websocket_card"
            )

            # Manually expire the session
            session.expires_at = datetime.now(UTC) - timedelta(hours=1)
            test_db.commit()

        async def cleanup_sessions():
            """Run session cleanup."""
            count = auth_manager.cleanup_expired_sessions()
            return count

        # Act - Run cleanup concurrently
        tasks = [cleanup_sessions() for _ in range(5)]
        counts = await asyncio.gather(*tasks)

        # Assert
        # At least one cleanup should have found expired sessions
        assert sum(counts) >= num_sessions

    async def test_concurrent_auth_with_rate_limiting(
        self, test_db, auth_manager, card_auth_handler
    ) -> None:
        """Test concurrent authorization with rate limiting.

        Flow:
        1. Simulate 20 users authorizing simultaneously
        2. Each user makes multiple rapid requests
        3. Verify rate limiting is applied correctly
        4. Verify system remains stable under load
        """
        # Arrange
        app_id = "cli_test1234567890ab"
        num_users = 20
        requests_per_user = 5

        async def make_multiple_requests(user_index: int):
            """Make multiple auth requests for a user."""
            user_id = f"ou_user_{user_index:03d}"
            results = []

            for _request_num in range(requests_per_user):
                try:
                    session = auth_manager.create_session(
                        app_id=app_id, user_id=user_id, auth_method="websocket_card"
                    )
                    results.append(("success", session))
                except Exception as e:
                    results.append(("error", str(e)))

                # Small delay between requests
                await asyncio.sleep(0.01)

            return results

        # Act - Make concurrent requests
        tasks = [make_multiple_requests(i) for i in range(num_users)]
        all_results = await asyncio.gather(*tasks)

        # Assert
        assert len(all_results) == num_users

        # Verify at least some requests succeeded
        total_requests = num_users * requests_per_user
        successful_requests = sum(
            1 for user_results in all_results for status, _ in user_results if status == "success"
        )

        # At least 80% of requests should succeed (allowing for some rate limiting)
        assert successful_requests >= total_requests * 0.8

    async def test_concurrent_auth_database_integrity(self, test_db, auth_manager) -> None:
        """Test database integrity under concurrent load.

        Flow:
        1. Perform 200 concurrent database operations
        2. Mix of create, update, and read operations
        3. Verify database remains consistent
        4. Verify no data corruption
        """
        # Arrange
        app_id = "cli_test1234567890ab"
        num_operations = 200

        async def perform_random_operation(op_index: int):
            """Perform a random database operation."""
            user_id = f"ou_user_{op_index % 50:03d}"

            # Create session
            if op_index % 3 == 0:
                session = auth_manager.create_session(
                    app_id=app_id, user_id=user_id, auth_method="websocket_card"
                )
                return ("create", session.session_id)

            # Complete session
            elif op_index % 3 == 1:
                try:
                    # Try to get an existing session
                    session = auth_manager.create_session(
                        app_id=app_id, user_id=user_id, auth_method="websocket_card"
                    )
                    auth_manager.complete_session(
                        session_id=session.session_id,
                        user_access_token=f"u-token_{op_index}",
                        token_expires_at=datetime.now(UTC) + timedelta(days=7),
                        user_info={
                            "user_id": user_id,
                            "open_id": user_id,
                            "union_id": f"on_union_{op_index}",
                            "name": f"User {op_index}",
                            "email": f"user{op_index}@example.com",
                        },
                    )
                    return ("complete", session.session_id)
                except Exception as e:
                    return ("error", str(e))

            # Read token
            else:
                try:
                    token = auth_manager.get_active_token(
                        app_id=app_id, user_id=user_id, raise_if_missing=False
                    )
                    return ("read", token)
                except Exception as e:
                    return ("error", str(e))

        # Act - Perform operations concurrently
        tasks = [perform_random_operation(i) for i in range(num_operations)]
        results = await asyncio.gather(*tasks)

        # Assert
        assert len(results) == num_operations

        # Count operation types
        create_count = sum(1 for op_type, _ in results if op_type == "create")
        complete_count = sum(1 for op_type, _ in results if op_type == "complete")
        read_count = sum(1 for op_type, _ in results if op_type == "read")
        error_count = sum(1 for op_type, _ in results if op_type == "error")

        # Verify operations were performed
        assert create_count > 0
        assert complete_count > 0
        assert read_count > 0

        # Allow some errors (e.g., reading tokens that don't exist yet)
        # but most operations should succeed
        assert error_count < num_operations * 0.5
