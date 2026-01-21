"""Credential pool for managing Feishu tokens.

Provides centralized token management with lazy loading and auto-refresh.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import lark_oapi as lark
import requests

from lark_service.core.config import Config
from lark_service.core.exceptions import (
    AuthenticationError,
    TokenAcquisitionError,
)
from lark_service.core.lock_manager import RefreshLockContext, TokenRefreshLock
from lark_service.core.retry import RetryStrategy
from lark_service.core.storage.postgres_storage import TokenStorageService
from lark_service.core.storage.sqlite_storage import ApplicationManager
from lark_service.utils.logger import get_logger
from lark_service.utils.validators import validate_app_id

if TYPE_CHECKING:
    from lark_service.apaas.client import WorkspaceTableClient
    from lark_service.clouddoc.client import DocClient
    from lark_service.contact.client import ContactClient
    from lark_service.messaging.client import MessagingClient

logger = get_logger()


class CredentialPool:
    """Credential pool for managing Feishu application tokens.

    Handles token acquisition, caching, and automatic refresh with
    multi-application isolation.

    Attributes:
        config: Application configuration
        app_manager: Application configuration manager
        token_storage: Token storage service
        lock_manager: Lock manager for concurrent operations
        retry_strategy: Retry strategy for API calls
        sdk_clients: Cache of Lark SDK clients by app_id
    """

    def __init__(
        self,
        config: Config,
        app_manager: ApplicationManager,
        token_storage: TokenStorageService,
        lock_dir: Path | str = "data/locks",
    ) -> None:
        """Initialize CredentialPool.

        Args:
            config: Application configuration
            app_manager: Application configuration manager
            token_storage: Token storage service
            lock_dir: Directory for lock files

        Example:
            >>> config = Config.load_from_env()
            >>> app_manager = ApplicationManager("data/config.db", encryption_key)
            >>> token_storage = TokenStorageService(config.get_postgres_url())
            >>> pool = CredentialPool(config, app_manager, token_storage)
        """
        self.config = config
        self.app_manager = app_manager
        self.token_storage = token_storage
        self.lock_manager = TokenRefreshLock(lock_dir, default_timeout=30.0)
        self.retry_strategy = RetryStrategy(
            max_retries=config.max_retries,
            base_delay=config.retry_backoff_base,
        )

        # Cache of SDK clients
        self.sdk_clients: dict[str, lark.Client] = {}

        # Pool-level default app_id (layer 4 in priority)
        self._default_app_id: str | None = None

        logger.info("CredentialPool initialized")

    def _get_sdk_client(self, app_id: str) -> lark.Client:
        """Get or create Lark SDK client for app_id.

        Args:
            app_id: Application ID

        Returns:
            Lark SDK client

        Raises:
            AuthenticationError: If application not found or credentials invalid
        """
        if app_id in self.sdk_clients:
            return self.sdk_clients[app_id]

        # Get application credentials
        app = self.app_manager.get_application(app_id)
        if not app:
            raise AuthenticationError(
                f"Application not found: {app_id}",
                details={"app_id": app_id},
            )

        if not app.is_active():
            raise AuthenticationError(
                f"Application is not active: {app_id}",
                details={"app_id": app_id, "status": app.status},
            )

        # Get decrypted secret
        app_secret = self.app_manager.get_decrypted_secret(app_id)

        # Create SDK client
        client = (
            lark.Client.builder()
            .app_id(app_id)
            .app_secret(app_secret)
            .log_level(lark.LogLevel.ERROR)
            .build()
        )

        self.sdk_clients[app_id] = client

        logger.debug(
            "SDK client created",
            extra={"app_id": app_id},
        )

        return client

    def _fetch_app_access_token(self, app_id: str) -> tuple[str, datetime]:
        """Fetch app_access_token from Feishu API.

        Note: Uses direct HTTP request instead of SDK due to potential compatibility issues.

        Args:
            app_id: Application ID

        Returns:
            Tuple of (token_value, expires_at)

        Raises:
            TokenAcquisitionError: If token acquisition fails
        """
        try:
            # Get app secret
            app_secret = self.app_manager.get_decrypted_secret(app_id)

            # Use direct HTTP request for better compatibility
            # Reference: https://open.feishu.cn/document/server-docs/authentication-management/access-token/app_access_token_internal
            url = "https://open.feishu.cn/open-apis/auth/v3/app_access_token/internal"
            payload = {"app_id": app_id, "app_secret": app_secret}

            response = requests.post(url, json=payload, timeout=10)
            result = response.json()

            # Check response
            if result.get("code") != 0:
                error_code = result.get("code")
                error_msg = result.get("msg", "Unknown error")
                raise TokenAcquisitionError(
                    f"Failed to get app_access_token: {error_msg}",
                    details={
                        "app_id": app_id,
                        "code": error_code,
                        "msg": error_msg,
                    },
                )

            token_value = result["app_access_token"]
            expires_in = result["expire"]  # seconds

            expires_at = datetime.now() + timedelta(seconds=expires_in)

            logger.info(
                "app_access_token acquired",
                extra={
                    "app_id": app_id,
                    "expires_in": expires_in,
                    "expires_at": expires_at.isoformat(),
                },
            )

            return token_value, expires_at

        except TokenAcquisitionError:
            raise
        except requests.RequestException as e:
            raise TokenAcquisitionError(
                f"Failed to fetch app_access_token: Network error - {e}",
                details={"app_id": app_id, "error": str(e)},
            ) from e
        except KeyError as e:
            raise TokenAcquisitionError(
                f"Failed to fetch app_access_token: Invalid response format - missing {e}",
                details={"app_id": app_id, "error": str(e)},
            ) from e
        except Exception as e:
            raise TokenAcquisitionError(
                f"Failed to fetch app_access_token: {e}",
                details={"app_id": app_id, "error": str(e)},
            ) from e

    def _fetch_tenant_access_token(self, app_id: str) -> tuple[str, datetime]:
        """Fetch tenant_access_token from Feishu API.

        Note: Uses direct HTTP request instead of SDK due to bug in lark-oapi v1.5.2
        InternalTenantAccessTokenRequest. See: https://open.feishu.cn/document/server-docs/authentication-management/access-token/tenant_access_token_internal

        Args:
            app_id: Application ID

        Returns:
            Tuple of (token_value, expires_at)

        Raises:
            TokenAcquisitionError: If token acquisition fails
        """
        try:
            # Get app secret
            app_secret = self.app_manager.get_decrypted_secret(app_id)

            # Use direct HTTP request to avoid SDK bug
            # Reference: https://open.feishu.cn/document/server-docs/authentication-management/access-token/tenant_access_token_internal
            url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
            payload = {"app_id": app_id, "app_secret": app_secret}

            response = requests.post(url, json=payload, timeout=10)
            result = response.json()

            # Check response
            if result.get("code") != 0:
                error_code = result.get("code")
                error_msg = result.get("msg", "Unknown error")
                raise TokenAcquisitionError(
                    f"Failed to get tenant_access_token: {error_msg}",
                    details={
                        "app_id": app_id,
                        "code": error_code,
                        "msg": error_msg,
                    },
                )

            token_value = result["tenant_access_token"]
            expires_in = result["expire"]  # seconds

            expires_at = datetime.now() + timedelta(seconds=expires_in)

            logger.info(
                "tenant_access_token acquired",
                extra={
                    "app_id": app_id,
                    "expires_in": expires_in,
                    "expires_at": expires_at.isoformat(),
                },
            )

            return token_value, expires_at

        except TokenAcquisitionError:
            raise
        except requests.RequestException as e:
            raise TokenAcquisitionError(
                f"Failed to fetch tenant_access_token: Network error - {e}",
                details={"app_id": app_id, "error": str(e)},
            ) from e
        except KeyError as e:
            raise TokenAcquisitionError(
                f"Failed to fetch tenant_access_token: Invalid response format - missing {e}",
                details={"app_id": app_id, "error": str(e)},
            ) from e
        except Exception as e:
            raise TokenAcquisitionError(
                f"Failed to fetch tenant_access_token: {e}",
                details={"app_id": app_id, "error": str(e)},
            ) from e

    def get_token(
        self,
        app_id: str,
        token_type: str = "app_access_token",  # nosec B107
        force_refresh: bool = False,
    ) -> str:
        """Get token with automatic refresh.

        Args:
            app_id: Application ID
            token_type: Token type ('app_access_token' or 'tenant_access_token')
            force_refresh: Force token refresh even if not expired

        Returns:
            Token value

        Raises:
            AuthenticationError: If application not found or credentials invalid
            TokenAcquisitionError: If token acquisition fails

        Example:
            >>> pool = CredentialPool(config, app_manager, token_storage)
            >>> token = pool.get_token("cli_abc123", "app_access_token")
        """
        validate_app_id(app_id)

        if token_type not in ["app_access_token", "tenant_access_token"]:
            raise ValueError(
                f"Invalid token_type: {token_type}. "
                "Must be 'app_access_token' or 'tenant_access_token'"
            )

        # Check cache first (unless force_refresh)
        if not force_refresh:
            cached_token = self.token_storage.get_token(app_id, token_type)
            if cached_token and not cached_token.is_expired():
                # Check if refresh is needed
                if cached_token.should_refresh(threshold=self.config.token_refresh_threshold):
                    logger.info(
                        "Token needs refresh",
                        extra={
                            "app_id": app_id,
                            "token_type": token_type,
                            "remaining_seconds": cached_token.get_remaining_seconds(),
                        },
                    )
                    # Refresh in background (or synchronously if needed)
                    return self._refresh_token_internal(app_id, token_type, force=False)
                else:
                    logger.debug(
                        "Using cached token",
                        extra={
                            "app_id": app_id,
                            "token_type": token_type,
                            "remaining_seconds": cached_token.get_remaining_seconds(),
                        },
                    )
                    return cached_token.token_value

        # Token not cached or expired, fetch new one
        return self._refresh_token_internal(app_id, token_type, force=force_refresh)

    def refresh_token(
        self,
        app_id: str,
        token_type: str = "app_access_token",  # nosec B107
    ) -> str:
        """Force refresh token from Feishu API (always fetches new token).

        Args:
            app_id: Application ID
            token_type: Token type ('app_access_token' or 'tenant_access_token')

        Returns:
            New token value

        Raises:
            AuthenticationError: If application not found or credentials invalid
            TokenAcquisitionError: If token acquisition fails

        Example:
            >>> pool = CredentialPool(config, app_manager, token_storage)
            >>> token = pool.refresh_token("cli_abc123", "app_access_token")
        """
        return self._refresh_token_internal(app_id, token_type, force=True)

    def _refresh_token_internal(
        self,
        app_id: str,
        token_type: str = "app_access_token",  # nosec B107
        force: bool = False,
    ) -> str:
        """Internal method to refresh token with optional force flag.

        Args:
            app_id: Application ID
            token_type: Token type
            force: If True, always fetch new token; if False, use double-check locking

        Returns:
            Token value
        """
        validate_app_id(app_id)

        # Use lock to prevent concurrent refresh
        with RefreshLockContext(self.lock_manager, app_id, timeout=30.0):
            # Double-check cache after acquiring lock (unless force=True)
            if not force:
                cached_token = self.token_storage.get_token(app_id, token_type)
                # Check if token exists, not expired, and doesn't need refresh
                if (
                    cached_token
                    and not cached_token.is_expired()
                    and not cached_token.should_refresh(
                        threshold=self.config.token_refresh_threshold
                    )
                ):
                    # Token was refreshed by another process
                    logger.debug(
                        "Token was refreshed by another process",
                        extra={"app_id": app_id, "token_type": token_type},
                    )
                    return cached_token.token_value

            # Fetch new token with retry
            def fetch_token() -> tuple[str, datetime]:
                if token_type == "app_access_token":  # nosec B105
                    return self._fetch_app_access_token(app_id)
                else:
                    return self._fetch_tenant_access_token(app_id)

            token_value, expires_at = self.retry_strategy.execute(fetch_token)

            # Store in database
            self.token_storage.set_token(
                app_id=app_id,
                token_type=token_type,
                token_value=token_value,
                expires_at=expires_at,
            )

            logger.info(
                "Token refreshed and stored",
                extra={
                    "app_id": app_id,
                    "token_type": token_type,
                    "expires_at": expires_at.isoformat(),
                },
            )

            return token_value

    def invalidate_token(
        self,
        app_id: str,
        token_type: str = "app_access_token",  # nosec B107
    ) -> None:
        """Invalidate cached token.

        Args:
            app_id: Application ID
            token_type: Token type

        Example:
            >>> pool = CredentialPool(config, app_manager, token_storage)
            >>> pool.invalidate_token("cli_abc123", "app_access_token")
        """
        validate_app_id(app_id)

        deleted = self.token_storage.delete_token(app_id, token_type)

        if deleted:
            logger.info(
                "Token invalidated",
                extra={"app_id": app_id, "token_type": token_type},
            )
        else:
            logger.debug(
                "Token not found for invalidation",
                extra={"app_id": app_id, "token_type": token_type},
            )

    def set_default_app_id(self, app_id: str) -> None:
        """Set pool-level default app_id (layer 4 in priority).

        This default app_id will be used when:
        - No explicit app_id is passed to client methods (layer 1)
        - No context manager is active (layer 2)
        - No client-level default is set (layer 3)

        Args:
            app_id: Application ID to set as default

        Raises:
            ValidationError: If app_id format is invalid
            AuthenticationError: If application not found or inactive

        Example:
            >>> pool = CredentialPool(config, app_manager, token_storage)
            >>> pool.set_default_app_id("cli_abc123")
            >>> # Now all clients created from this pool use "cli_abc123" by default
        """
        validate_app_id(app_id)

        # Validate that application exists and is active
        app = self.app_manager.get_application(app_id)
        if not app:
            raise AuthenticationError(
                f"Application not found: {app_id}",
                details={"app_id": app_id},
            )

        if not app.is_active():
            raise AuthenticationError(
                f"Application is not active: {app_id}",
                details={"app_id": app_id, "status": app.status},
            )

        self._default_app_id = app_id
        logger.info(
            "Pool-level default app_id set",
            extra={"app_id": app_id},
        )

    def get_default_app_id(self) -> str | None:
        """Get pool-level default app_id.

        Returns pool-level default if explicitly set via `set_default_app_id()`,
        otherwise delegates to ApplicationManager's intelligent selection strategy.

        Returns:
            Default app_id (str) or None if not available

        Example:
            >>> pool = CredentialPool(config, app_manager, token_storage)
            >>> pool.set_default_app_id("cli_abc123")
            >>> default = pool.get_default_app_id()
            >>> # default == "cli_abc123"

            >>> # If not explicitly set, auto-selects in single-app scenario
            >>> pool2 = CredentialPool(config, app_manager, token_storage)
            >>> default = pool2.get_default_app_id()
            >>> # default == "cli_abc123" (if only one active app exists)
        """
        # Priority 1: Explicitly set pool-level default
        if self._default_app_id:
            return self._default_app_id

        # Priority 2: ApplicationManager's intelligent selection
        return self.app_manager.get_default_app_id()

    def list_app_ids(self) -> list[str]:
        """List all active application IDs.

        Returns:
            List of active application IDs

        Example:
            >>> pool = CredentialPool(config, app_manager, token_storage)
            >>> apps = pool.list_app_ids()
            >>> # apps == ["cli_app1", "cli_app2", "cli_app3"]
        """
        apps = self.app_manager.list_applications()
        return [app.app_id for app in apps if app.is_active()]

    def create_messaging_client(self, app_id: str | None = None) -> MessagingClient:
        """Factory method to create MessagingClient with optional app_id.

        Note: This method will be fully functional after T003 refactoring.

        Args:
            app_id: Optional application ID to bind to this client

        Returns:
            MessagingClient instance

        Example:
            >>> pool = CredentialPool(config, app_manager, token_storage)
            >>> client1 = pool.create_messaging_client("cli_app1")
            >>> client2 = pool.create_messaging_client("cli_app2")
            >>> # Each client bound to different app
        """
        from lark_service.messaging.client import MessagingClient

        return MessagingClient(self, app_id=app_id)

    def create_contact_client(self, app_id: str | None = None) -> ContactClient:
        """Factory method to create ContactClient with optional app_id.

        Note: This method will be fully functional after T003 refactoring.

        Args:
            app_id: Optional application ID to bind to this client

        Returns:
            ContactClient instance

        Example:
            >>> pool = CredentialPool(config, app_manager, token_storage)
            >>> client = pool.create_contact_client("cli_app1")
        """
        from lark_service.contact.client import ContactClient

        return ContactClient(self, app_id=app_id)

    def create_clouddoc_client(self, app_id: str | None = None) -> DocClient:
        """Factory method to create DocClient (CloudDoc) with optional app_id.

        Note: This method will be fully functional after T003 refactoring.

        Args:
            app_id: Optional application ID to bind to this client

        Returns:
            DocClient instance

        Example:
            >>> pool = CredentialPool(config, app_manager, token_storage)
            >>> client = pool.create_clouddoc_client("cli_app1")
        """
        from lark_service.clouddoc.client import DocClient

        return DocClient(self, app_id=app_id)

    def create_apaas_client(self, app_id: str | None = None) -> WorkspaceTableClient:
        """Factory method to create WorkspaceTableClient (aPaaS) with optional app_id.

        Note: This method will be fully functional after T003 refactoring.

        Args:
            app_id: Optional application ID to bind to this client

        Returns:
            WorkspaceTableClient instance

        Example:
            >>> pool = CredentialPool(config, app_manager, token_storage)
            >>> client = pool.create_apaas_client("cli_app1")
        """
        from lark_service.apaas.client import WorkspaceTableClient

        return WorkspaceTableClient(self, app_id=app_id)

    def close(self) -> None:
        """Close all resources.

        Example:
            >>> pool = CredentialPool(config, app_manager, token_storage)
            >>> try:
            ...     token = pool.get_token("cli_abc123")
            ... finally:
            ...     pool.close()
        """
        self.app_manager.close()
        self.token_storage.close()
        logger.info("CredentialPool closed")
