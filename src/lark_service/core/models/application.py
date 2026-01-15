"""Application configuration model for SQLite storage.

This module defines the Application model for storing Lark app configurations
in SQLite database with encrypted app_secret.
"""


from datetime import datetime

from cryptography.fernet import Fernet
from sqlalchemy import String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class ConfigBase(DeclarativeBase):
    """Base class for SQLite config database models."""

    pass


class Application(ConfigBase):
    """Lark application configuration model.

    Stores application credentials and metadata in SQLite database.
    The app_secret is encrypted using Fernet symmetric encryption.

    Attributes
    ----------
        app_id: Lark application ID (primary key)
        app_name: Human-readable application name (unique)
        app_secret: Encrypted application secret
        description: Optional application description
        status: Application status (active/disabled)
        permissions: JSON array of permission scopes
        created_at: Record creation timestamp
        updated_at: Record last update timestamp
        created_by: Creator identifier for audit trail

    Example
    ----------
        >>> app = Application(
        ...     app_id="cli_a1b2c3d4e5f6g7h8",
        ...     app_name="Internal Notification System",
        ...     app_secret=encrypt_secret("secret_value", key),
        ...     status="active"
        ... )
        >>> app.is_active()
        True
    """

    __tablename__ = "applications"

    app_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    app_name: Mapped[str] = mapped_column(String(128), unique=True)
    app_secret: Mapped[str] = mapped_column(Text)  # Encrypted with Fernet
    description: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[str] = mapped_column(String(16), default="active")
    permissions: Mapped[str | None] = mapped_column(Text, default=None)  # JSON array
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        default=func.now(), onupdate=func.now()
    )
    created_by: Mapped[str | None] = mapped_column(String(64), default=None)

    def is_active(self) -> bool:
        """Check if application is in active status.

        Returns
        ----------
            True if status is 'active', False otherwise
        """
        return self.status == "active"

    def get_decrypted_secret(self, encryption_key: bytes) -> str:
        """Decrypt and return the application secret.

        Parameters
        ----------
            encryption_key: Fernet encryption key (32 url-safe base64-encoded bytes)

        Returns
        ----------
            Decrypted application secret string

        Raises
        ----------
            ValueError: If encryption key is invalid
            cryptography.fernet.InvalidToken: If decryption fails
        """
        cipher = Fernet(encryption_key)
        return cipher.decrypt(self.app_secret.encode()).decode()

    def set_encrypted_secret(self, secret: str, encryption_key: bytes) -> None:
        """Encrypt and set the application secret.

        Parameters
        ----------
            secret: Plain text application secret
            encryption_key: Fernet encryption key (32 url-safe base64-encoded bytes)

        Raises
        ----------
            ValueError: If encryption key is invalid
        """
        cipher = Fernet(encryption_key)
        self.app_secret = cipher.encrypt(secret.encode()).decode()

    def __repr__(self) -> str:
        """Return string representation of Application."""
        return (
            f"<Application(app_id='{self.app_id}', "
            f"app_name='{self.app_name}', "
            f"status='{self.status}')>"
        )
