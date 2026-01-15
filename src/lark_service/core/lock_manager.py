"""Lock manager for concurrent token refresh operations.

Provides thread-safe and process-safe locking mechanisms.
"""

import threading
from pathlib import Path
from typing import Any

from filelock import FileLock, Timeout

from lark_service.core.exceptions import LockAcquisitionError
from lark_service.utils.logger import get_logger

logger = get_logger()


class TokenRefreshLock:
    """Lock manager for token refresh operations.

    Provides both thread-level and process-level locking to prevent
    concurrent token refresh operations for the same app_id.

    Attributes:
        lock_dir: Directory for lock files
        thread_locks: Dictionary of thread locks by app_id
        thread_locks_lock: Lock for thread_locks dictionary
        default_timeout: Default lock acquisition timeout
    """

    def __init__(self, lock_dir: Path | str = "data/locks", default_timeout: float = 30.0) -> None:
        """Initialize TokenRefreshLock.

        Args:
            lock_dir: Directory for lock files
            default_timeout: Default timeout for lock acquisition (seconds)

        Example:
            >>> lock_manager = TokenRefreshLock("data/locks", default_timeout=30.0)
        """
        self.lock_dir = Path(lock_dir)
        self.lock_dir.mkdir(parents=True, exist_ok=True)
        self.default_timeout = default_timeout

        # Thread-level locks (per app_id)
        self.thread_locks: dict[str, threading.Lock] = {}
        self.thread_locks_lock = threading.Lock()

        logger.info(
            "TokenRefreshLock initialized",
            extra={"lock_dir": str(self.lock_dir), "timeout": default_timeout},
        )

    def _get_thread_lock(self, app_id: str) -> threading.Lock:
        """Get or create thread lock for app_id.

        Args:
            app_id: Application ID

        Returns:
            Thread lock for the app_id
        """
        with self.thread_locks_lock:
            if app_id not in self.thread_locks:
                self.thread_locks[app_id] = threading.Lock()
            return self.thread_locks[app_id]

    def _get_file_lock_path(self, app_id: str) -> Path:
        """Get file lock path for app_id.

        Args:
            app_id: Application ID

        Returns:
            Path to lock file
        """
        return self.lock_dir / f"token_refresh_{app_id}.lock"

    def acquire(
        self,
        app_id: str,
        timeout: float | None = None,
        blocking: bool = True,
    ) -> tuple[threading.Lock, FileLock]:
        """Acquire both thread and file locks for token refresh.

        Args:
            app_id: Application ID
            timeout: Lock acquisition timeout (uses default if None)
            blocking: Whether to block waiting for lock

        Returns:
            Tuple of (thread_lock, file_lock)

        Raises:
            LockAcquisitionError: If lock cannot be acquired within timeout

        Example:
            >>> lock_manager = TokenRefreshLock()
            >>> thread_lock, file_lock = lock_manager.acquire("cli_abc123")
            >>> try:
            ...     # Perform token refresh
            ...     pass
            ... finally:
            ...     lock_manager.release("cli_abc123", thread_lock, file_lock)
        """
        if timeout is None:
            timeout = self.default_timeout

        thread_lock = self._get_thread_lock(app_id)
        file_lock_path = self._get_file_lock_path(app_id)
        file_lock = FileLock(file_lock_path, timeout=timeout)

        # Acquire thread lock
        try:
            thread_acquired = thread_lock.acquire(blocking=blocking, timeout=timeout if blocking else None)
            if not thread_acquired:
                raise LockAcquisitionError(
                    f"Failed to acquire thread lock for app_id: {app_id}",
                    lock_key=app_id,
                    timeout=timeout,
                )
        except Exception as e:
            raise LockAcquisitionError(
                f"Failed to acquire thread lock: {e}",
                lock_key=app_id,
                timeout=timeout,
            ) from e

        # Acquire file lock
        try:
            file_lock.acquire(timeout=timeout, poll_interval=0.1)
        except Timeout as e:
            # Release thread lock if file lock fails
            thread_lock.release()
            raise LockAcquisitionError(
                f"Failed to acquire file lock for app_id: {app_id}",
                lock_key=app_id,
                timeout=timeout,
            ) from e
        except Exception as e:
            # Release thread lock if file lock fails
            thread_lock.release()
            raise LockAcquisitionError(
                f"Failed to acquire file lock: {e}",
                lock_key=app_id,
                timeout=timeout,
            ) from e

        logger.debug(
            "Locks acquired",
            extra={"app_id": app_id, "timeout": timeout},
        )

        return thread_lock, file_lock

    def release(
        self,
        app_id: str,
        thread_lock: threading.Lock,
        file_lock: FileLock,
    ) -> None:
        """Release both thread and file locks.

        Args:
            app_id: Application ID
            thread_lock: Thread lock to release
            file_lock: File lock to release

        Example:
            >>> lock_manager = TokenRefreshLock()
            >>> thread_lock, file_lock = lock_manager.acquire("cli_abc123")
            >>> try:
            ...     # Perform token refresh
            ...     pass
            ... finally:
            ...     lock_manager.release("cli_abc123", thread_lock, file_lock)
        """
        # Release file lock first
        try:
            if file_lock.is_locked:
                file_lock.release()
        except Exception as e:
            logger.warning(
                "Failed to release file lock",
                extra={"app_id": app_id, "error": str(e)},
            )

        # Release thread lock
        try:
            if thread_lock.locked():
                thread_lock.release()
        except Exception as e:
            logger.warning(
                "Failed to release thread lock",
                extra={"app_id": app_id, "error": str(e)},
            )

        logger.debug(
            "Locks released",
            extra={"app_id": app_id},
        )

    def __enter__(self) -> "TokenRefreshLock":
        """Context manager entry.

        Returns:
            Self for context manager protocol
        """
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any) -> None:
        """Context manager exit.

        Args:
            exc_type: Exception type if raised
            exc_val: Exception value if raised
            exc_tb: Exception traceback if raised
        """
        # Cleanup is handled by individual release() calls
        pass


class RefreshLockContext:
    """Context manager for token refresh locking.

    Automatically acquires and releases locks.

    Example:
        >>> lock_manager = TokenRefreshLock()
        >>> with RefreshLockContext(lock_manager, "cli_abc123"):
        ...     # Perform token refresh
        ...     pass
    """

    def __init__(
        self,
        lock_manager: TokenRefreshLock,
        app_id: str,
        timeout: float | None = None,
    ) -> None:
        """Initialize RefreshLockContext.

        Args:
            lock_manager: TokenRefreshLock instance
            app_id: Application ID
            timeout: Lock acquisition timeout
        """
        self.lock_manager = lock_manager
        self.app_id = app_id
        self.timeout = timeout
        self.thread_lock: threading.Lock | None = None
        self.file_lock: FileLock | None = None

    def __enter__(self) -> "RefreshLockContext":
        """Acquire locks on context entry.

        Returns:
            Self for context manager protocol

        Raises:
            LockAcquisitionError: If locks cannot be acquired
        """
        self.thread_lock, self.file_lock = self.lock_manager.acquire(
            self.app_id,
            timeout=self.timeout,
        )
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any) -> None:
        """Release locks on context exit.

        Args:
            exc_type: Exception type if raised
            exc_val: Exception value if raised
            exc_tb: Exception traceback if raised
        """
        if self.thread_lock and self.file_lock:
            self.lock_manager.release(
                self.app_id,
                self.thread_lock,
                self.file_lock,
            )
