"""SQLite storage service for application configuration.

Provides CRUD operations for application credentials with encryption.
"""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from lark_service.core.exceptions import StorageError, ValidationError
from lark_service.core.models.application import Application, ConfigBase
from lark_service.utils.logger import get_logger
from lark_service.utils.validators import validate_app_id, validate_app_secret, validate_enum

logger = get_logger()


class ApplicationManager:
    """Manager for application configuration in SQLite.

    Handles CRUD operations for application credentials with encryption.

    Attributes:
        db_path: Path to SQLite database file
        encryption_key: Fernet encryption key for secrets
        engine: SQLAlchemy engine
        session_factory: SQLAlchemy session factory
    """

    def __init__(self, db_path: Path | str, encryption_key: bytes) -> None:
        """Initialize ApplicationManager.

        Args:
            db_path: Path to SQLite database file
            encryption_key: Fernet encryption key for secrets

        Raises:
            StorageError: If database initialization fails

        Example:
            >>> key = Fernet.generate_key()
            >>> manager = ApplicationManager("data/config.db", key)
        """
        self.db_path = Path(db_path)
        self.encryption_key = encryption_key

        try:
            # Create database directory if needed
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            # Create engine
            self.engine = create_engine(
                f"sqlite:///{self.db_path}",
                echo=False,
                pool_pre_ping=True,
            )

            # Create session factory
            self.session_factory = sessionmaker(bind=self.engine)

            # Create tables
            ConfigBase.metadata.create_all(self.engine)

            logger.info(
                "ApplicationManager initialized",
                extra={"db_path": str(self.db_path)},
            )

        except Exception as e:
            raise StorageError(
                f"Failed to initialize ApplicationManager: {e}",
                details={"db_path": str(self.db_path), "error": str(e)},
            ) from e

    def _get_session(self) -> Session:
        """Get database session.

        Returns:
            SQLAlchemy session
        """
        return self.session_factory()

    def add_application(
        self,
        app_id: str,
        app_name: str,
        app_secret: str,
        description: str | None = None,
        permissions: str | None = None,
        created_by: str | None = None,
    ) -> Application:
        """Add new application configuration.

        Args:
            app_id: Application ID
            app_name: Application name (must be unique)
            app_secret: Application secret (will be encrypted)
            description: Optional description
            permissions: Optional permissions JSON string
            created_by: Optional creator identifier

        Returns:
            Created Application instance

        Raises:
            ValidationError: If input validation fails
            StorageError: If database operation fails

        Example:
            >>> app = manager.add_application(
            ...     app_id="cli_abc123",
            ...     app_name="My App",
            ...     app_secret="secret123",
            ... )
        """
        # Validate inputs
        validate_app_id(app_id)
        validate_app_secret(app_secret)

        if not app_name or not app_name.strip():
            raise ValidationError("app_name cannot be empty")

        session = self._get_session()
        try:
            # Check if app_id already exists
            existing = session.query(Application).filter_by(app_id=app_id).first()
            if existing:
                raise StorageError(
                    f"Application with app_id '{app_id}' already exists",
                    details={"app_id": app_id},
                )

            # Check if app_name already exists
            existing_name = session.query(Application).filter_by(app_name=app_name).first()
            if existing_name:
                raise StorageError(
                    f"Application with app_name '{app_name}' already exists",
                    details={"app_name": app_name},
                )

            # Create application
            app = Application(
                app_id=app_id,
                app_name=app_name,
                description=description,
                status="active",
                permissions=permissions,
                created_by=created_by,
            )
            app.set_encrypted_secret(app_secret, self.encryption_key)

            session.add(app)
            session.commit()
            session.refresh(app)

            logger.info(
                "Application added",
                extra={"app_id": app_id, "app_name": app_name},
            )

            return app

        except (ValidationError, StorageError):
            session.rollback()
            raise
        except Exception as e:
            session.rollback()
            raise StorageError(
                f"Failed to add application: {e}",
                details={"app_id": app_id, "error": str(e)},
            ) from e
        finally:
            session.close()

    def get_application(self, app_id: str) -> Application | None:
        """Get application by ID.

        Args:
            app_id: Application ID

        Returns:
            Application instance or None if not found

        Raises:
            ValidationError: If app_id format is invalid
            StorageError: If database operation fails

        Example:
            >>> app = manager.get_application("cli_abc123")
            >>> if app:
            ...     print(app.app_name)
        """
        validate_app_id(app_id)

        session = self._get_session()
        try:
            app = session.query(Application).filter_by(app_id=app_id).first()
            if app:
                # Detach from session
                session.expunge(app)
            return app

        except Exception as e:
            raise StorageError(
                f"Failed to get application: {e}",
                details={"app_id": app_id, "error": str(e)},
            ) from e
        finally:
            session.close()

    def list_applications(self, status: str | None = None) -> list[Application]:
        """List all applications.

        Args:
            status: Optional status filter ('active', 'inactive', 'deleted')

        Returns:
            List of Application instances

        Raises:
            ValidationError: If status value is invalid
            StorageError: If database operation fails

        Example:
            >>> apps = manager.list_applications(status="active")
            >>> for app in apps:
            ...     print(app.app_name)
        """
        if status:
            validate_enum(status, ["active", "inactive", "deleted"], "status")

        session = self._get_session()
        try:
            query = session.query(Application)
            if status:
                query = query.filter_by(status=status)

            apps = query.all()

            # Detach from session
            for app in apps:
                session.expunge(app)

            return apps

        except (ValidationError, StorageError):
            raise
        except Exception as e:
            raise StorageError(
                f"Failed to list applications: {e}",
                details={"status": status, "error": str(e)},
            ) from e
        finally:
            session.close()

    def update_application(
        self,
        app_id: str,
        app_name: str | None = None,
        app_secret: str | None = None,
        description: str | None = None,
        status: str | None = None,
        permissions: str | None = None,
    ) -> Application:
        """Update application configuration.

        Args:
            app_id: Application ID
            app_name: New application name (optional)
            app_secret: New application secret (optional, will be encrypted)
            description: New description (optional)
            status: New status (optional: 'active', 'inactive', 'deleted')
            permissions: New permissions JSON string (optional)

        Returns:
            Updated Application instance

        Raises:
            ValidationError: If input validation fails
            StorageError: If application not found or database operation fails

        Example:
            >>> app = manager.update_application(
            ...     app_id="cli_abc123",
            ...     status="inactive",
            ... )
        """
        validate_app_id(app_id)

        if app_secret:
            validate_app_secret(app_secret)

        if status:
            validate_enum(status, ["active", "inactive", "deleted"], "status")

        session = self._get_session()
        try:
            app = session.query(Application).filter_by(app_id=app_id).first()
            if not app:
                raise StorageError(
                    f"Application not found: {app_id}",
                    details={"app_id": app_id},
                )

            # Update fields
            if app_name is not None:
                # Check name uniqueness
                existing = session.query(Application).filter(
                    Application.app_name == app_name,
                    Application.app_id != app_id
                ).first()
                if existing:
                    raise StorageError(
                        f"Application name '{app_name}' already exists",
                        details={"app_name": app_name},
                    )
                app.app_name = app_name

            if app_secret is not None:
                app.set_encrypted_secret(app_secret, self.encryption_key)

            if description is not None:
                app.description = description

            if status is not None:
                app.status = status

            if permissions is not None:
                app.permissions = permissions

            session.commit()
            session.refresh(app)

            logger.info(
                "Application updated",
                extra={"app_id": app_id},
            )

            # Detach from session
            session.expunge(app)
            return app

        except (ValidationError, StorageError):
            session.rollback()
            raise
        except Exception as e:
            session.rollback()
            raise StorageError(
                f"Failed to update application: {e}",
                details={"app_id": app_id, "error": str(e)},
            ) from e
        finally:
            session.close()

    def delete_application(self, app_id: str, soft_delete: bool = True) -> None:
        """Delete application configuration.

        Args:
            app_id: Application ID
            soft_delete: If True, mark as deleted; if False, permanently delete

        Raises:
            ValidationError: If app_id format is invalid
            StorageError: If application not found or database operation fails

        Example:
            >>> manager.delete_application("cli_abc123")  # Soft delete
            >>> manager.delete_application("cli_abc123", soft_delete=False)  # Hard delete
        """
        validate_app_id(app_id)

        session = self._get_session()
        try:
            app = session.query(Application).filter_by(app_id=app_id).first()
            if not app:
                raise StorageError(
                    f"Application not found: {app_id}",
                    details={"app_id": app_id},
                )

            if soft_delete:
                app.status = "deleted"
                session.commit()
                logger.info(
                    "Application soft deleted",
                    extra={"app_id": app_id},
                )
            else:
                session.delete(app)
                session.commit()
                logger.info(
                    "Application permanently deleted",
                    extra={"app_id": app_id},
                )

        except (ValidationError, StorageError):
            session.rollback()
            raise
        except Exception as e:
            session.rollback()
            raise StorageError(
                f"Failed to delete application: {e}",
                details={"app_id": app_id, "error": str(e)},
            ) from e
        finally:
            session.close()

    def get_decrypted_secret(self, app_id: str) -> str:
        """Get decrypted application secret.

        Args:
            app_id: Application ID

        Returns:
            Decrypted application secret

        Raises:
            ValidationError: If app_id format is invalid
            StorageError: If application not found or decryption fails

        Example:
            >>> secret = manager.get_decrypted_secret("cli_abc123")
        """
        app = self.get_application(app_id)
        if not app:
            raise StorageError(
                f"Application not found: {app_id}",
                details={"app_id": app_id},
            )

        try:
            return app.get_decrypted_secret(self.encryption_key)
        except Exception as e:
            raise StorageError(
                f"Failed to decrypt secret: {e}",
                details={"app_id": app_id, "error": str(e)},
            ) from e

    def close(self) -> None:
        """Close database connections.

        Example:
            >>> manager.close()
        """
        self.engine.dispose()
        logger.info("ApplicationManager closed")
