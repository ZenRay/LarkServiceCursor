"""PostgreSQL storage service for token management.

Provides token storage with connection pooling and encryption.
"""

from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from lark_service.core.exceptions import StorageError, ValidationError
from lark_service.core.models.token_storage import Base, TokenStorage
from lark_service.utils.logger import get_logger
from lark_service.utils.validators import validate_app_id, validate_token

logger = get_logger()


class TokenStorageService:
    """Service for token storage in PostgreSQL.

    Handles token CRUD operations with connection pooling.

    Attributes:
        postgres_url: PostgreSQL connection URL
        engine: SQLAlchemy engine with connection pool
        session_factory: SQLAlchemy session factory
    """

    def __init__(
        self,
        postgres_url: str,
        pool_size: int = 10,
        max_overflow: int = 20,
        pool_timeout: int = 30,
    ) -> None:
        """Initialize TokenStorageService.

        Args:
            postgres_url: PostgreSQL connection URL
            pool_size: Number of connections to maintain in pool
            max_overflow: Maximum overflow connections
            pool_timeout: Timeout for getting connection from pool (seconds)

        Raises:
            StorageError: If database initialization fails

        Example:
            >>> service = TokenStorageService(
            ...     "postgresql://user:pass@localhost/db",
            ...     pool_size=10,
            ... )
        """
        self.postgres_url = postgres_url

        try:
            # Create engine with connection pool
            self.engine = create_engine(
                postgres_url,
                poolclass=QueuePool,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_timeout=pool_timeout,
                pool_pre_ping=True,  # Verify connections before use
                echo=False,
            )

            # Create session factory
            self.session_factory = sessionmaker(bind=self.engine)

            # Create tables (idempotent)
            Base.metadata.create_all(self.engine)

            logger.info(
                "TokenStorageService initialized",
                extra={
                    "pool_size": pool_size,
                    "max_overflow": max_overflow,
                },
            )

        except Exception as e:
            raise StorageError(
                f"Failed to initialize TokenStorageService: {e}",
                details={"error": str(e)},
            ) from e

    def _get_session(self) -> Session:
        """Get database session from pool.

        Returns:
            SQLAlchemy session
        """
        return self.session_factory()

    def set_token(
        self,
        app_id: str,
        token_type: str,
        token_value: str,
        expires_at: datetime,
    ) -> TokenStorage:
        """Store or update token.

        Args:
            app_id: Application ID
            token_type: Token type (e.g., 'app_access_token', 'tenant_access_token')
            token_value: Token value (encrypted)
            expires_at: Token expiration time

        Returns:
            TokenStorage instance

        Raises:
            ValidationError: If input validation fails
            StorageError: If database operation fails

        Example:
            >>> from datetime import datetime, timedelta
            >>> token = service.set_token(
            ...     app_id="cli_abc123",
            ...     token_type="app_access_token",
            ...     token_value="encrypted_token",
            ...     expires_at=datetime.now() + timedelta(hours=2),
            ... )
        """
        validate_app_id(app_id)
        validate_token(token_value, token_type)

        if not token_type or not token_type.strip():
            raise ValidationError("token_type cannot be empty")

        session = self._get_session()
        try:
            # Check if token exists
            existing = session.query(TokenStorage).filter_by(
                app_id=app_id,
                token_type=token_type,
            ).first()

            if existing:
                # Update existing token
                existing.token_value = token_value
                existing.expires_at = expires_at
                token = existing
            else:
                # Create new token
                token = TokenStorage(
                    app_id=app_id,
                    token_type=token_type,
                    token_value=token_value,
                    expires_at=expires_at,
                )
                session.add(token)

            session.commit()
            session.refresh(token)

            logger.debug(
                "Token stored",
                extra={
                    "app_id": app_id,
                    "token_type": token_type,
                    "expires_at": expires_at.isoformat(),
                },
            )

            # Detach from session
            session.expunge(token)
            return token

        except (ValidationError, StorageError):
            session.rollback()
            raise
        except Exception as e:
            session.rollback()
            raise StorageError(
                f"Failed to store token: {e}",
                details={
                    "app_id": app_id,
                    "token_type": token_type,
                    "error": str(e),
                },
            ) from e
        finally:
            session.close()

    def get_token(
        self,
        app_id: str,
        token_type: str,
    ) -> TokenStorage | None:
        """Get token by app_id and token_type.

        Args:
            app_id: Application ID
            token_type: Token type

        Returns:
            TokenStorage instance or None if not found

        Raises:
            ValidationError: If app_id format is invalid
            StorageError: If database operation fails

        Example:
            >>> token = service.get_token("cli_abc123", "app_access_token")
            >>> if token and not token.is_expired():
            ...     print(token.token_value)
        """
        validate_app_id(app_id)

        session = self._get_session()
        try:
            token = session.query(TokenStorage).filter_by(
                app_id=app_id,
                token_type=token_type,
            ).first()

            if token:
                # Detach from session
                session.expunge(token)

            return token

        except Exception as e:
            raise StorageError(
                f"Failed to get token: {e}",
                details={
                    "app_id": app_id,
                    "token_type": token_type,
                    "error": str(e),
                },
            ) from e
        finally:
            session.close()

    def delete_token(
        self,
        app_id: str,
        token_type: str,
    ) -> bool:
        """Delete token.

        Args:
            app_id: Application ID
            token_type: Token type

        Returns:
            True if token was deleted, False if not found

        Raises:
            ValidationError: If app_id format is invalid
            StorageError: If database operation fails

        Example:
            >>> deleted = service.delete_token("cli_abc123", "app_access_token")
        """
        validate_app_id(app_id)

        session = self._get_session()
        try:
            token = session.query(TokenStorage).filter_by(
                app_id=app_id,
                token_type=token_type,
            ).first()

            if not token:
                return False

            session.delete(token)
            session.commit()

            logger.debug(
                "Token deleted",
                extra={"app_id": app_id, "token_type": token_type},
            )

            return True

        except Exception as e:
            session.rollback()
            raise StorageError(
                f"Failed to delete token: {e}",
                details={
                    "app_id": app_id,
                    "token_type": token_type,
                    "error": str(e)},
            ) from e
        finally:
            session.close()

    def list_tokens(
        self,
        app_id: str | None = None,
        include_expired: bool = False,
    ) -> list[TokenStorage]:
        """List tokens with optional filtering.

        Args:
            app_id: Optional application ID filter
            include_expired: Include expired tokens

        Returns:
            List of TokenStorage instances

        Raises:
            ValidationError: If app_id format is invalid
            StorageError: If database operation fails

        Example:
            >>> tokens = service.list_tokens(app_id="cli_abc123")
            >>> for token in tokens:
            ...     print(f"{token.token_type}: {token.is_expired()}")
        """
        if app_id:
            validate_app_id(app_id)

        session = self._get_session()
        try:
            query = session.query(TokenStorage)

            if app_id:
                query = query.filter_by(app_id=app_id)

            if not include_expired:
                query = query.filter(TokenStorage.expires_at > datetime.now())

            tokens = query.all()

            # Detach from session
            for token in tokens:
                session.expunge(token)

            return tokens

        except Exception as e:
            raise StorageError(
                f"Failed to list tokens: {e}",
                details={"app_id": app_id, "error": str(e)},
            ) from e
        finally:
            session.close()

    def cleanup_expired_tokens(self, older_than_days: int = 7) -> int:
        """Clean up expired tokens.

        Args:
            older_than_days: Delete tokens expired more than N days ago

        Returns:
            Number of tokens deleted

        Raises:
            StorageError: If database operation fails

        Example:
            >>> count = service.cleanup_expired_tokens(older_than_days=7)
            >>> print(f"Deleted {count} expired tokens")
        """
        session = self._get_session()
        try:
            cutoff_time = datetime.now() - timedelta(days=older_than_days)

            deleted_count = session.query(TokenStorage).filter(
                TokenStorage.expires_at < cutoff_time
            ).delete()

            session.commit()

            logger.info(
                "Expired tokens cleaned up",
                extra={
                    "deleted_count": deleted_count,
                    "older_than_days": older_than_days,
                },
            )

            return deleted_count

        except Exception as e:
            session.rollback()
            raise StorageError(
                f"Failed to cleanup expired tokens: {e}",
                details={"error": str(e)},
            ) from e
        finally:
            session.close()

    def get_tokens_needing_refresh(
        self,
        threshold: float = 0.1,
    ) -> list[TokenStorage]:
        """Get tokens that need refresh based on threshold.

        Args:
            threshold: Refresh threshold (0.0-1.0, default 0.1 = 10% of lifetime)

        Returns:
            List of TokenStorage instances needing refresh

        Raises:
            StorageError: If database operation fails

        Example:
            >>> tokens = service.get_tokens_needing_refresh(threshold=0.1)
            >>> for token in tokens:
            ...     print(f"Refresh needed: {token.app_id} - {token.token_type}")
        """
        session = self._get_session()
        try:
            tokens = session.query(TokenStorage).filter(
                TokenStorage.expires_at > datetime.now()
            ).all()

            # Filter by threshold
            tokens_needing_refresh = [
                token for token in tokens
                if token.should_refresh(threshold=threshold)
            ]

            # Detach from session
            for token in tokens_needing_refresh:
                session.expunge(token)

            return tokens_needing_refresh

        except Exception as e:
            raise StorageError(
                f"Failed to get tokens needing refresh: {e}",
                details={"error": str(e)},
            ) from e
        finally:
            session.close()

    def close(self) -> None:
        """Close database connections and dispose pool.

        Example:
            >>> service.close()
        """
        self.engine.dispose()
        logger.info("TokenStorageService closed")
