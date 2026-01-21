"""Base service client for unified app_id management.

Provides a common interface for all service clients to resolve app_id
with a 5-layer priority mechanism and context-based application switching.
"""

from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING

from lark_service.core.exceptions import ConfigError
from lark_service.utils.logger import get_logger

if TYPE_CHECKING:
    from lark_service.core.credential_pool import CredentialPool

logger = get_logger()


class BaseServiceClient:
    """Base class for all Lark service clients with unified app_id management.

    This class provides a common app_id resolution mechanism with the following
    5-layer priority (highest to lowest):
    1. Method parameter `app_id`
    2. Context stack top (set by `use_app()` context manager)
    3. Client-level default `_default_app_id`
    4. CredentialPool-level default
    5. Raise ConfigError if none available

    Attributes
    ----------
    credential_pool : CredentialPool
        The credential pool instance for SDK client management
    _default_app_id : str | None
        Client-level default app_id (layer 3 in priority)
    _context_app_stack : list[str]
        Context stack for nested `use_app()` calls (layer 2 in priority)

    Examples
    --------
    Single-app scenario (no explicit app_id needed):

    >>> pool = CredentialPool(...)
    >>> pool.set_default_app_id("cli_a1b2c3d4e5f6g7h8")
    >>> client = MessagingClient(pool)
    >>> client.send_text_message(receiver_id="ou_xxx", text="Hello")

    Multi-app scenario (using context manager):

    >>> pool = CredentialPool(...)
    >>> client = MessagingClient(pool)
    >>> with client.use_app("cli_app1"):
    ...     client.send_text_message(receiver_id="ou_xxx", text="To app1")
    >>> with client.use_app("cli_app2"):
    ...     client.send_text_message(receiver_id="ou_yyy", text="To app2")

    Notes
    -----
    The `use_app()` context manager is NOT thread-safe for concurrent
    application switching. For multi-threaded scenarios, create separate
    client instances per thread or use explicit app_id parameters.
    """

    def __init__(
        self,
        credential_pool: "CredentialPool",
        app_id: str | None = None,
    ) -> None:
        """Initialize BaseServiceClient.

        Parameters
        ----------
        credential_pool : CredentialPool
            The credential pool for managing SDK clients and tokens
        app_id : str | None, optional
            Client-level default app_id (layer 3 in priority)

        Examples
        --------
        Client with explicit default app_id:

        >>> pool = CredentialPool(...)
        >>> client = MessagingClient(pool, app_id="cli_xxx")
        >>> # All calls use "cli_xxx" by default

        Client without default (relies on pool-level default):

        >>> pool = CredentialPool(...)
        >>> pool.set_default_app_id("cli_yyy")
        >>> client = MessagingClient(pool)
        >>> # All calls use "cli_yyy" by default
        """
        self.credential_pool = credential_pool
        self._default_app_id = app_id
        self._context_app_stack: list[str] = []

        if app_id:
            logger.debug(f"BaseServiceClient initialized with default app_id: {app_id}")
        else:
            logger.debug("BaseServiceClient initialized without default app_id")

    def _resolve_app_id(self, app_id: str | None = None) -> str:
        """Resolve app_id using 5-layer priority mechanism.

        Priority (highest to lowest):
        1. Method parameter `app_id`
        2. Context stack top (from `use_app()`)
        3. Client-level default `_default_app_id`
        4. CredentialPool-level default
        5. Raise ConfigError (no app_id available)

        Parameters
        ----------
        app_id : str | None, optional
            Explicit app_id parameter (highest priority)

        Returns
        -------
        str
            The resolved app_id

        Raises
        ------
        ConfigError
            If no app_id can be determined from any layer

        Examples
        --------
        Priority 1: Method parameter (highest):

        >>> client = MessagingClient(pool, app_id="cli_default")
        >>> with client.use_app("cli_context"):
        ...     resolved = client._resolve_app_id(app_id="cli_param")
        >>> # resolved == "cli_param"

        Priority 2: Context stack:

        >>> client = MessagingClient(pool, app_id="cli_default")
        >>> with client.use_app("cli_context"):
        ...     resolved = client._resolve_app_id()
        >>> # resolved == "cli_context"

        Priority 3: Client-level default:

        >>> client = MessagingClient(pool, app_id="cli_default")
        >>> resolved = client._resolve_app_id()
        >>> # resolved == "cli_default"

        Priority 4: CredentialPool-level default:

        >>> pool.set_default_app_id("cli_pool_default")
        >>> client = MessagingClient(pool)
        >>> resolved = client._resolve_app_id()
        >>> # resolved == "cli_pool_default"

        Priority 5: No app_id available (error):

        >>> client = MessagingClient(pool)  # No defaults
        >>> try:
        ...     resolved = client._resolve_app_id()
        ... except ConfigError as e:
        ...     print(e)
        ConfigError: Unable to determine app_id...
        """
        # Priority 1: Method parameter
        if app_id:
            logger.debug(f"Resolved app_id from method parameter: {app_id}")
            return app_id

        # Priority 2: Context stack top
        if self._context_app_stack:
            resolved = self._context_app_stack[-1]
            logger.debug(f"Resolved app_id from context stack: {resolved}")
            return resolved

        # Priority 3: Client-level default
        if self._default_app_id:
            logger.debug(f"Resolved app_id from client default: {self._default_app_id}")
            return self._default_app_id

        # Priority 4: CredentialPool-level default
        pool_default = self.credential_pool.get_default_app_id()
        if pool_default:
            logger.debug(f"Resolved app_id from pool default: {pool_default}")
            return pool_default

        # Priority 5: No app_id available - raise ConfigError
        available_apps = self.credential_pool.list_app_ids()
        error_msg = (
            "Unable to determine app_id. No app_id was provided via:\n"
            "  1. Method parameter (app_id=...)\n"
            "  2. Context manager (use_app(...))\n"
            "  3. Client initialization (MessagingClient(pool, app_id=...))\n"
            "  4. CredentialPool default (pool.set_default_app_id(...))\n\n"
            "Please specify app_id using one of the methods above."
        )

        if available_apps:
            error_msg += f"\n\nAvailable app_ids: {', '.join(available_apps)}"
        else:
            error_msg += "\n\nNo applications configured. Please register an application first."

        logger.error(f"Failed to resolve app_id: {error_msg}")
        raise ConfigError(error_msg, details={"available_apps": available_apps})

    def get_current_app_id(self) -> str | None:
        """Get the currently resolved app_id (for debugging).

        This method returns the app_id that would be used for the next
        API call, or None if no app_id can be determined. Unlike
        `_resolve_app_id()`, this does not raise an exception.

        Returns
        -------
        str | None
            The currently resolved app_id, or None if not available

        Examples
        --------
        Check current app_id:

        >>> client = MessagingClient(pool, app_id="cli_xxx")
        >>> print(client.get_current_app_id())
        cli_xxx

        >>> with client.use_app("cli_yyy"):
        ...     print(client.get_current_app_id())
        cli_yyy

        No app_id available:

        >>> client = MessagingClient(pool)  # No defaults
        >>> print(client.get_current_app_id())
        None
        """
        try:
            return self._resolve_app_id()
        except ConfigError:
            return None

    def list_available_apps(self) -> list[str]:
        """List all available application IDs.

        Returns
        -------
        list[str]
            List of all active application IDs

        Examples
        --------
        >>> client = MessagingClient(pool)
        >>> apps = client.list_available_apps()
        >>> print(apps)
        ['cli_app1', 'cli_app2', 'cli_app3']
        """
        return self.credential_pool.list_app_ids()

    @contextmanager
    def use_app(self, app_id: str) -> Generator[None, None, None]:
        """Context manager for temporarily switching application context.

        This allows switching between applications for specific operations
        without changing the client's default app_id. Supports nested calls.

        Parameters
        ----------
        app_id : str
            The application ID to use within this context

        Yields
        ------
        None

        Examples
        --------
        Single context:

        >>> client = MessagingClient(pool, app_id="cli_default")
        >>> with client.use_app("cli_temp"):
        ...     # All calls here use "cli_temp"
        ...     client.send_text_message(receiver_id="ou_xxx", text="Hello")
        >>> # Back to "cli_default"

        Nested contexts:

        >>> client = MessagingClient(pool, app_id="cli_default")
        >>> with client.use_app("cli_app1"):
        ...     print(client.get_current_app_id())  # cli_app1
        ...     with client.use_app("cli_app2"):
        ...         print(client.get_current_app_id())  # cli_app2
        ...     print(client.get_current_app_id())  # cli_app1
        >>> print(client.get_current_app_id())  # cli_default

        Override with method parameter:

        >>> client = MessagingClient(pool)
        >>> with client.use_app("cli_context"):
        ...     # Method parameter has highest priority
        ...     client.send_text_message(
        ...         app_id="cli_override",
        ...         receiver_id="ou_xxx",
        ...         text="Hello"
        ...     )

        Warnings
        --------
        This context manager is NOT thread-safe. For multi-threaded scenarios,
        use one of the following approaches:

        1. Create separate client instances per thread
        2. Use explicit app_id parameters
        3. Use factory methods to create isolated clients

        See Also
        --------
        CredentialPool.create_messaging_client : Factory method for creating clients
        """
        logger.debug(f"Entering use_app context: {app_id}")
        self._context_app_stack.append(app_id)
        try:
            yield
        finally:
            popped = self._context_app_stack.pop()
            logger.debug(f"Exiting use_app context: {popped}")
