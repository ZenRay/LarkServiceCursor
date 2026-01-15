"""Unit tests for lock manager.

Tests concurrent access and timeout behavior.
"""

import threading
import time
from pathlib import Path

import pytest

from lark_service.core.exceptions import LockAcquisitionError
from lark_service.core.lock_manager import RefreshLockContext, TokenRefreshLock


class TestTokenRefreshLock:
    """Test TokenRefreshLock functionality."""

    def test_lock_initialization(self, tmp_path: Path) -> None:
        """Test lock manager initialization."""
        lock_manager = TokenRefreshLock(tmp_path / "locks", default_timeout=10.0)
        assert lock_manager.lock_dir.exists()
        assert lock_manager.default_timeout == 10.0

    def test_acquire_and_release(self, tmp_path: Path) -> None:
        """Test basic lock acquisition and release."""
        lock_manager = TokenRefreshLock(tmp_path / "locks")
        app_id = "cli_test123"

        # Acquire locks
        thread_lock, file_lock = lock_manager.acquire(app_id)
        assert thread_lock.locked()
        assert file_lock.is_locked

        # Release locks
        lock_manager.release(app_id, thread_lock, file_lock)
        assert not thread_lock.locked()
        assert not file_lock.is_locked

    def test_concurrent_thread_access(self, tmp_path: Path) -> None:
        """Test that thread lock prevents concurrent access."""
        lock_manager = TokenRefreshLock(tmp_path / "locks", default_timeout=2.0)
        app_id = "cli_concurrent_test"
        results = []

        def worker(worker_id: int) -> None:
            try:
                thread_lock, file_lock = lock_manager.acquire(app_id, timeout=0.5)
                results.append(f"worker_{worker_id}_acquired")
                time.sleep(1.0)  # Hold lock longer to ensure conflict
                lock_manager.release(app_id, thread_lock, file_lock)
                results.append(f"worker_{worker_id}_released")
            except LockAcquisitionError:
                results.append(f"worker_{worker_id}_timeout")

        # Start two threads trying to acquire same lock
        thread1 = threading.Thread(target=worker, args=(1,))
        thread2 = threading.Thread(target=worker, args=(2,))

        thread1.start()
        time.sleep(0.1)  # Ensure thread1 acquires first
        thread2.start()

        thread1.join()
        thread2.join()

        # Worker 1 should succeed, worker 2 should timeout
        assert "worker_1_acquired" in results
        assert "worker_1_released" in results
        assert "worker_2_timeout" in results
        # Worker 2 should NOT acquire
        assert "worker_2_acquired" not in results

    def test_timeout_behavior(self, tmp_path: Path) -> None:
        """Test lock acquisition timeout."""
        lock_manager = TokenRefreshLock(tmp_path / "locks")
        app_id = "cli_timeout_test"

        # Acquire lock in main thread
        thread_lock, file_lock = lock_manager.acquire(app_id)

        # Try to acquire again with short timeout (should fail)
        with pytest.raises(LockAcquisitionError, match="Failed to acquire"):
            lock_manager.acquire(app_id, timeout=0.5)

        # Release original lock
        lock_manager.release(app_id, thread_lock, file_lock)

    def test_non_blocking_acquire(self, tmp_path: Path) -> None:
        """Test non-blocking lock acquisition."""
        lock_manager = TokenRefreshLock(tmp_path / "locks")
        app_id = "cli_nonblocking_test"

        # Acquire lock
        thread_lock1, file_lock1 = lock_manager.acquire(app_id)

        # Try non-blocking acquire (should fail immediately)
        with pytest.raises(LockAcquisitionError):
            lock_manager.acquire(app_id, blocking=False)

        # Release lock
        lock_manager.release(app_id, thread_lock1, file_lock1)

    def test_multiple_app_ids(self, tmp_path: Path) -> None:
        """Test that different app_ids can acquire locks simultaneously."""
        lock_manager = TokenRefreshLock(tmp_path / "locks")
        app_id1 = "cli_app1"
        app_id2 = "cli_app2"

        # Acquire locks for different apps
        thread_lock1, file_lock1 = lock_manager.acquire(app_id1)
        thread_lock2, file_lock2 = lock_manager.acquire(app_id2)

        # Both should be locked
        assert thread_lock1.locked()
        assert file_lock1.is_locked
        assert thread_lock2.locked()
        assert file_lock2.is_locked

        # Release both
        lock_manager.release(app_id1, thread_lock1, file_lock1)
        lock_manager.release(app_id2, thread_lock2, file_lock2)

    def test_lock_file_creation(self, tmp_path: Path) -> None:
        """Test that lock files are created."""
        lock_manager = TokenRefreshLock(tmp_path / "locks")
        app_id = "cli_file_test"

        thread_lock, file_lock = lock_manager.acquire(app_id)

        # Check lock file exists
        lock_file = tmp_path / "locks" / f"token_refresh_{app_id}.lock"
        assert lock_file.exists()

        lock_manager.release(app_id, thread_lock, file_lock)


class TestRefreshLockContext:
    """Test RefreshLockContext context manager."""

    def test_context_manager_basic(self, tmp_path: Path) -> None:
        """Test basic context manager usage."""
        lock_manager = TokenRefreshLock(tmp_path / "locks")
        app_id = "cli_context_test"

        with RefreshLockContext(lock_manager, app_id):
            # Locks should be acquired
            # Try to acquire again (should fail)
            with pytest.raises(LockAcquisitionError):
                lock_manager.acquire(app_id, timeout=0.5)

        # After context exit, locks should be released
        # Should be able to acquire now
        thread_lock, file_lock = lock_manager.acquire(app_id, timeout=1.0)
        lock_manager.release(app_id, thread_lock, file_lock)

    def test_context_manager_with_exception(self, tmp_path: Path) -> None:
        """Test that locks are released even if exception occurs."""
        lock_manager = TokenRefreshLock(tmp_path / "locks")
        app_id = "cli_exception_test"

        try:
            with RefreshLockContext(lock_manager, app_id):
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Locks should be released despite exception
        thread_lock, file_lock = lock_manager.acquire(app_id, timeout=1.0)
        lock_manager.release(app_id, thread_lock, file_lock)

    def test_context_manager_timeout(self, tmp_path: Path) -> None:
        """Test context manager with custom timeout."""
        lock_manager = TokenRefreshLock(tmp_path / "locks")
        app_id = "cli_timeout_context_test"

        # Acquire lock first
        thread_lock1, file_lock1 = lock_manager.acquire(app_id)

        # Try to acquire with context manager and short timeout
        with pytest.raises(LockAcquisitionError):
            with RefreshLockContext(lock_manager, app_id, timeout=0.5):
                pass

        # Release original lock
        lock_manager.release(app_id, thread_lock1, file_lock1)

    def test_nested_context_different_apps(self, tmp_path: Path) -> None:
        """Test nested context managers with different app_ids."""
        lock_manager = TokenRefreshLock(tmp_path / "locks")
        app_id1 = "cli_nested1"
        app_id2 = "cli_nested2"

        with RefreshLockContext(lock_manager, app_id1):
            with RefreshLockContext(lock_manager, app_id2):
                # Both locks should be held
                with pytest.raises(LockAcquisitionError):
                    lock_manager.acquire(app_id1, timeout=0.5)
                with pytest.raises(LockAcquisitionError):
                    lock_manager.acquire(app_id2, timeout=0.5)

        # Both locks should be released
        thread_lock1, file_lock1 = lock_manager.acquire(app_id1, timeout=1.0)
        thread_lock2, file_lock2 = lock_manager.acquire(app_id2, timeout=1.0)
        lock_manager.release(app_id1, thread_lock1, file_lock1)
        lock_manager.release(app_id2, thread_lock2, file_lock2)
