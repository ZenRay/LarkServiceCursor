"""Application configuration model for SQLite storage.

This module defines the Application model for storing Lark app configurations
in SQLite database with encrypted app_secret.
"""


from cryptography.fernet import Fernet
from sqlalchemy import Column, DateTime, String, Text, func
from sqlalchemy.ext.declarative import declarative_base

ConfigBase = declarative_base()


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

    app_id = Column(String(64), primary_key=True)
    app_name = Column(String(128), nullable=False, unique=True)
    app_secret = Column(Text, nullable=False)  # Encrypted with Fernet
    description = Column(Text, nullable=True)
    status = Column(String(16), nullable=False, default="active")
    permissions = Column(Text, nullable=True)  # JSON array as string
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    created_by = Column(String(64), nullable=True)

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
