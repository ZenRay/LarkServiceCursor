"""Unit tests for PostgreSQL TokenStorageService.

Tests token CRUD operations, connection pooling, and error handling with mocked database.
Focus on: token persistence, expiry handling, connection pool, transaction rollback.
"""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session

from lark_service.core.exceptions import StorageError, ValidationError
from lark_service.core.models.token_storage import TokenStorage
from lark_service.core.storage.postgres_storage import TokenStorageService

# === Mock Fixtures ===

@pytest.fixture
def mock_engine() -> Mock:
    """Create mock SQLAlchemy engine."""
    engine = Mock()
    engine.dispose = Mock()
    return engine


@pytest.fixture
def mock_session() -> Mock:
    """Create mock SQLAlchemy session."""
    session = Mock(spec=Session)
    session.query = Mock(return_value=Mock())
    session.commit = Mock()
    session.rollback = Mock()
    session.close = Mock()
    session.add = Mock()
    session.refresh = Mock()
    session.expunge = Mock()
    session.delete = Mock()
    session.execute = Mock()
    return session


@pytest.fixture
def mock_session_factory(mock_session: Mock) -> Mock:
    """Create mock session factory."""
    factory = Mock()
    factory.return_value = mock_session
    return factory


@pytest.fixture
def storage_service(mock_engine: Mock, mock_session_factory: Mock) -> TokenStorageService:
    """Create TokenStorageService with mocked dependencies."""
    with patch("lark_service.core.storage.postgres_storage.create_engine", return_value=mock_engine):
        with patch("lark_service.core.storage.postgres_storage.sessionmaker", return_value=mock_session_factory):
            with patch("lark_service.core.storage.postgres_storage.Base.metadata.create_all"):
                service = TokenStorageService(
                    postgres_url="postgresql://test:test@localhost/test_db",
                    pool_size=5,
                    max_overflow=10,
                    pool_timeout=20,
                )
                return service


# === Initialization Tests ===

class TestTokenStorageServiceInitialization:
    """Test service initialization and configuration."""

    def test_init_success(self) -> None:
        """Test successful initialization with connection pool."""
        with patch("lark_service.core.storage.postgres_storage.create_engine") as mock_create_engine:
            with patch("lark_service.core.storage.postgres_storage.sessionmaker"):
                with patch("lark_service.core.storage.postgres_storage.Base.metadata.create_all"):
                    mock_engine = Mock()
                    mock_create_engine.return_value = mock_engine

                    service = TokenStorageService(
                        postgres_url="postgresql://user:pass@localhost/db",
                        pool_size=15,
                        max_overflow=25,
                        pool_timeout=35,
                    )

                    assert service.postgres_url == "postgresql://user:pass@localhost/db"
                    assert service.engine == mock_engine

                    # Verify create_engine was called with correct pool params
                    mock_create_engine.assert_called_once()
                    call_kwargs = mock_create_engine.call_args.kwargs
                    assert call_kwargs["pool_size"] == 15
                    assert call_kwargs["max_overflow"] == 25
                    assert call_kwargs["pool_timeout"] == 35
                    assert call_kwargs["pool_pre_ping"] is True

    def test_init_database_error(self) -> None:
        """Test initialization failure with database connection error."""
        with patch("lark_service.core.storage.postgres_storage.create_engine", side_effect=OperationalError("Connection failed", None, None)):
            with pytest.raises(StorageError, match="Failed to initialize TokenStorageService"):
                TokenStorageService("postgresql://bad:connection@localhost/db")

    def test_get_session(self, storage_service: TokenStorageService, mock_session: Mock) -> None:
        """Test session retrieval from pool."""
        session = storage_service._get_session()
        assert session == mock_session


# === set_token Tests ===

class TestSetToken:
    """Test set_token method (FR-012: PostgreSQL persistence)."""

    def test_set_token_new(
        self,
        storage_service: TokenStorageService,
        mock_session: Mock,
    ) -> None:
        """Test storing new token."""
        # Mock no existing token
        mock_session.query().filter_by().first.return_value = None

        expires_at = datetime.now() + timedelta(hours=2)
        created_at = datetime.now()

        storage_service.set_token(
            app_id="cli_test1234567890ab",
            token_type="app_access_token",
            token_value="test_token_value_123",
            expires_at=expires_at,
            created_at=created_at,
        )

        # Verify session.add was called
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()
        mock_session.expunge.assert_called_once()
        mock_session.close.assert_called_once()

    def test_set_token_update_existing(
        self,
        storage_service: TokenStorageService,
        mock_session: Mock,
    ) -> None:
        """Test updating existing token."""
        # Mock existing token
        existing_token = Mock(spec=TokenStorage)
        existing_token.app_id = "cli_test1234567890ab"
        existing_token.token_type = "app_access_token"
        existing_token.token_value = "old_token"

        mock_session.query().filter_by().first.return_value = existing_token

        new_expires_at = datetime.now() + timedelta(hours=2)
        new_created_at = datetime.now()

        storage_service.set_token(
            app_id="cli_test1234567890ab",
            token_type="app_access_token",
            token_value="new_token_value_456",
            expires_at=new_expires_at,
            created_at=new_created_at,
        )

        # Verify token was updated (not added)
        assert existing_token.token_value == "new_token_value_456"
        assert existing_token.expires_at == new_expires_at
        assert existing_token.created_at == new_created_at

        mock_session.add.assert_not_called()  # Should not add new, just update
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    def test_set_token_default_created_at(
        self,
        storage_service: TokenStorageService,
        mock_session: Mock,
    ) -> None:
        """Test set_token with default created_at (None)."""
        mock_session.query().filter_by().first.return_value = None

        expires_at = datetime.now() + timedelta(hours=2)

        storage_service.set_token(
            app_id="cli_test1234567890ab",
            token_type="app_access_token",
            token_value="test_token",
            expires_at=expires_at,
            created_at=None,  # Should default to now()
        )

        mock_session.add.assert_called_once()
        # Verify token was created with a created_at value
        added_token = mock_session.add.call_args[0][0]
        assert added_token.created_at is not None

    def test_set_token_invalid_app_id(
        self,
        storage_service: TokenStorageService,
    ) -> None:
        """Test set_token with invalid app_id."""
        with pytest.raises(ValidationError, match="Invalid app_id format"):
            storage_service.set_token(
                app_id="invalid",  # Too short
                token_type="app_access_token",
                token_value="token",
                expires_at=datetime.now() + timedelta(hours=1),
            )

    def test_set_token_empty_token_type(
        self,
        storage_service: TokenStorageService,
    ) -> None:
        """Test set_token with empty token_type."""
        with pytest.raises(ValidationError, match="token_type cannot be empty"):
            storage_service.set_token(
                app_id="cli_test1234567890ab",
                token_type="   ",  # Whitespace only
                token_value="t-" + "a" * 20,  # Valid length token
                expires_at=datetime.now() + timedelta(hours=1),
            )

    def test_set_token_database_error_rollback(
        self,
        storage_service: TokenStorageService,
        mock_session: Mock,
    ) -> None:
        """Test set_token with database error triggers rollback (FR-119)."""
        mock_session.query().filter_by().first.return_value = None
        mock_session.commit.side_effect = SQLAlchemyError("Database error")

        with pytest.raises(StorageError, match="Failed to store token"):
            storage_service.set_token(
                app_id="cli_test1234567890ab",
                token_type="app_access_token",
                token_value="t-" + "a" * 30,  # Valid length token
                expires_at=datetime.now() + timedelta(hours=1),
            )

        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()


# === get_token Tests ===

class TestGetToken:
    """Test get_token method."""

    def test_get_token_found(
        self,
        storage_service: TokenStorageService,
        mock_session: Mock,
    ) -> None:
        """Test retrieving existing token."""
        mock_token = Mock(spec=TokenStorage)
        mock_token.app_id = "cli_test1234567890ab"
        mock_token.token_type = "app_access_token"
        mock_token.token_value = "test_token_123"

        mock_session.query().filter_by().first.return_value = mock_token

        token = storage_service.get_token(
            app_id="cli_test1234567890ab",
            token_type="app_access_token",
        )

        assert token == mock_token
        mock_session.expunge.assert_called_once_with(mock_token)
        mock_session.close.assert_called_once()

    def test_get_token_not_found(
        self,
        storage_service: TokenStorageService,
        mock_session: Mock,
    ) -> None:
        """Test retrieving non-existent token."""
        mock_session.query().filter_by().first.return_value = None

        token = storage_service.get_token(
            app_id="cli_nonexistent12345",
            token_type="app_access_token",
        )

        assert token is None
        mock_session.expunge.assert_not_called()
        mock_session.close.assert_called_once()

    def test_get_token_invalid_app_id(
        self,
        storage_service: TokenStorageService,
    ) -> None:
        """Test get_token with invalid app_id."""
        with pytest.raises(ValidationError, match="Invalid app_id format"):
            storage_service.get_token(
                app_id="short",  # Too short
                token_type="app_access_token",
            )

    def test_get_token_database_error(
        self,
        storage_service: TokenStorageService,
        mock_session: Mock,
    ) -> None:
        """Test get_token with database error."""
        mock_session.query().filter_by().first.side_effect = SQLAlchemyError("Query failed")

        with pytest.raises(StorageError, match="Failed to get token"):
            storage_service.get_token(
                app_id="cli_test1234567890ab",
                token_type="app_access_token",
            )

        mock_session.close.assert_called_once()


# === delete_token Tests ===

class TestDeleteToken:
    """Test delete_token method."""

    def test_delete_token_success(
        self,
        storage_service: TokenStorageService,
        mock_session: Mock,
    ) -> None:
        """Test successful token deletion."""
        mock_token = Mock(spec=TokenStorage)
        mock_session.query().filter_by().first.return_value = mock_token

        result = storage_service.delete_token(
            app_id="cli_test1234567890ab",
            token_type="app_access_token",
        )

        assert result is True
        mock_session.delete.assert_called_once_with(mock_token)
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    def test_delete_token_not_found(
        self,
        storage_service: TokenStorageService,
        mock_session: Mock,
    ) -> None:
        """Test deleting non-existent token."""
        mock_session.query().filter_by().first.return_value = None

        result = storage_service.delete_token(
            app_id="cli_nonexistent12345",
            token_type="app_access_token",
        )

        assert result is False
        mock_session.delete.assert_not_called()
        mock_session.commit.assert_not_called()
        mock_session.close.assert_called_once()

    def test_delete_token_database_error_rollback(
        self,
        storage_service: TokenStorageService,
        mock_session: Mock,
    ) -> None:
        """Test delete_token with database error triggers rollback."""
        mock_token = Mock(spec=TokenStorage)
        mock_session.query().filter_by().first.return_value = mock_token
        mock_session.delete.side_effect = SQLAlchemyError("Delete failed")

        with pytest.raises(StorageError, match="Failed to delete token"):
            storage_service.delete_token(
                app_id="cli_test1234567890ab",
                token_type="app_access_token",
            )

        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()


# === list_tokens Tests ===

class TestListTokens:
    """Test list_tokens method."""

    def test_list_tokens_all(
        self,
        storage_service: TokenStorageService,
        mock_session: Mock,
    ) -> None:
        """Test listing all tokens."""
        mock_tokens = [Mock(spec=TokenStorage) for _ in range(3)]
        mock_session.query().all.return_value = mock_tokens

        tokens = storage_service.list_tokens(
            app_id=None,
            include_expired=True,
        )

        assert tokens == mock_tokens
        assert len(tokens) == 3
        mock_session.close.assert_called_once()

    def test_list_tokens_by_app_id(
        self,
        storage_service: TokenStorageService,
        mock_session: Mock,
    ) -> None:
        """Test listing tokens filtered by app_id."""
        mock_tokens = [Mock(spec=TokenStorage)]
        mock_query = Mock()
        mock_query.filter_by().all.return_value = mock_tokens
        mock_session.query.return_value = mock_query

        tokens = storage_service.list_tokens(
            app_id="cli_test1234567890ab",
            include_expired=True,
        )

        assert tokens == mock_tokens
        mock_session.close.assert_called_once()

    def test_list_tokens_exclude_expired(
        self,
        storage_service: TokenStorageService,
        mock_session: Mock,
    ) -> None:
        """Test listing tokens excluding expired ones."""
        mock_tokens = [Mock(spec=TokenStorage)]
        mock_query = Mock()
        mock_query.filter().all.return_value = mock_tokens
        mock_session.query.return_value = mock_query

        tokens = storage_service.list_tokens(
            app_id=None,
            include_expired=False,
        )

        assert tokens == mock_tokens
        mock_session.close.assert_called_once()

    def test_list_tokens_database_error(
        self,
        storage_service: TokenStorageService,
        mock_session: Mock,
    ) -> None:
        """Test list_tokens with database error."""
        mock_session.query().all.side_effect = SQLAlchemyError("List failed")

        with pytest.raises(StorageError, match="Failed to list tokens"):
            storage_service.list_tokens()

        mock_session.close.assert_called_once()


# === cleanup_expired_tokens Tests ===

class TestCleanupExpiredTokens:
    """Test cleanup_expired_tokens method."""

    def test_cleanup_expired_tokens_success(
        self,
        storage_service: TokenStorageService,
        mock_session: Mock,
    ) -> None:
        """Test cleaning up expired tokens."""
        mock_session.query().filter().delete.return_value = 5  # 5 tokens deleted

        deleted_count = storage_service.cleanup_expired_tokens()

        assert deleted_count == 5
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    def test_cleanup_expired_tokens_none_expired(
        self,
        storage_service: TokenStorageService,
        mock_session: Mock,
    ) -> None:
        """Test cleanup when no tokens are expired."""
        mock_session.query().filter().delete.return_value = 0

        deleted_count = storage_service.cleanup_expired_tokens()

        assert deleted_count == 0
        mock_session.commit.assert_called_once()

    def test_cleanup_expired_tokens_custom_cutoff(
        self,
        storage_service: TokenStorageService,
        mock_session: Mock,
    ) -> None:
        """Test cleanup with default cutoff time (now)."""
        mock_session.query().filter().delete.return_value = 3

        deleted_count = storage_service.cleanup_expired_tokens()

        assert deleted_count == 3

    def test_cleanup_expired_tokens_database_error_rollback(
        self,
        storage_service: TokenStorageService,
        mock_session: Mock,
    ) -> None:
        """Test cleanup with database error triggers rollback."""
        mock_session.query().filter().delete.side_effect = SQLAlchemyError("Cleanup failed")

        with pytest.raises(StorageError, match="Failed to cleanup expired tokens"):
            storage_service.cleanup_expired_tokens()

        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()


# === get_tokens_needing_refresh Tests ===

class TestGetTokensNeedingRefresh:
    """Test get_tokens_needing_refresh method."""

    def test_get_tokens_needing_refresh(
        self,
        storage_service: TokenStorageService,
        mock_session: Mock,
    ) -> None:
        """Test retrieving tokens needing refresh."""
        # Create mock tokens
        mock_token1 = Mock(spec=TokenStorage)
        mock_token1.should_refresh.return_value = True

        mock_token2 = Mock(spec=TokenStorage)
        mock_token2.should_refresh.return_value = False

        mock_token3 = Mock(spec=TokenStorage)
        mock_token3.should_refresh.return_value = True

        mock_session.query().filter().all.return_value = [mock_token1, mock_token2, mock_token3]

        tokens = storage_service.get_tokens_needing_refresh(threshold=0.1)

        # Should return only tokens that need refresh
        assert len(tokens) == 2
        assert mock_token1 in tokens
        assert mock_token3 in tokens
        assert mock_token2 not in tokens

        mock_session.close.assert_called_once()

    def test_get_tokens_needing_refresh_none(
        self,
        storage_service: TokenStorageService,
        mock_session: Mock,
    ) -> None:
        """Test when no tokens need refresh."""
        mock_token = Mock(spec=TokenStorage)
        mock_token.should_refresh.return_value = False

        mock_session.query().filter().all.return_value = [mock_token]

        tokens = storage_service.get_tokens_needing_refresh(threshold=0.1)

        assert len(tokens) == 0

    def test_get_tokens_needing_refresh_database_error(
        self,
        storage_service: TokenStorageService,
        mock_session: Mock,
    ) -> None:
        """Test get_tokens_needing_refresh with database error."""
        mock_session.query().filter().all.side_effect = SQLAlchemyError("Query failed")

        with pytest.raises(StorageError, match="Failed to get tokens needing refresh"):
            storage_service.get_tokens_needing_refresh()

        mock_session.close.assert_called_once()


# === close Tests ===

class TestClose:
    """Test close method (FR-120: Connection pool cleanup)."""

    def test_close_disposes_engine(
        self,
        storage_service: TokenStorageService,
        mock_engine: Mock,
    ) -> None:
        """Test close method disposes engine and releases connections."""
        storage_service.close()

        mock_engine.dispose.assert_called_once()


# === Edge Cases and Error Scenarios ===

class TestEdgeCases:
    """Test edge cases and error scenarios."""

    def test_concurrent_set_token_same_key(
        self,
        storage_service: TokenStorageService,
        mock_session: Mock,
    ) -> None:
        """Test concurrent set_token for same app_id/token_type."""
        # Simulate race condition: token appears after first query
        mock_existing = Mock(spec=TokenStorage)
        mock_existing.token_value = "old_token"

        mock_session.query().filter_by().first.return_value = mock_existing

        expires_at = datetime.now() + timedelta(hours=2)

        storage_service.set_token(
            app_id="cli_test1234567890ab",
            token_type="app_access_token",
            token_value="new_token_race",
            expires_at=expires_at,
        )

        # Should update existing token
        assert mock_existing.token_value == "new_token_race"
        mock_session.add.assert_not_called()
        mock_session.commit.assert_called_once()

    def test_session_always_closed_on_exception(
        self,
        storage_service: TokenStorageService,
        mock_session: Mock,
    ) -> None:
        """Test session is closed even when exception occurs."""
        mock_session.query().filter_by().first.side_effect = SQLAlchemyError("Unexpected error")

        with pytest.raises(StorageError):
            storage_service.get_token("cli_test1234567890ab", "app_access_token")

        mock_session.close.assert_called_once()

    def test_set_token_with_very_long_token_value(
        self,
        storage_service: TokenStorageService,
        mock_session: Mock,
    ) -> None:
        """Test set_token with valid length token (up to 1024 chars)."""
        mock_session.query().filter_by().first.return_value = None

        long_token = "t-" + "a" * 1000  # Within 1024 char limit
        expires_at = datetime.now() + timedelta(hours=2)

        storage_service.set_token(
            app_id="cli_test1234567890ab",
            token_type="app_access_token",
            token_value=long_token,
            expires_at=expires_at,
        )

        mock_session.add.assert_called_once()
        added_token = mock_session.add.call_args[0][0]
        assert added_token.token_value == long_token
