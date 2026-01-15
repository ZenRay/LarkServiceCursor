"""SQLite configuration database initialization.

This module provides functions to initialize the SQLite database for
application configuration storage.
"""

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from lark_service.core.models.application import Application, ConfigBase


def get_config_db_path() -> Path:
    """Get the path to the SQLite configuration database.

    Returns
    ----------
        Path to the SQLite database file

    Example
    ----------
        >>> path = get_config_db_path()
        >>> print(path)
        /path/to/project/data/lark_config.db
    """
    # Get from environment variable or use default
    db_path_str = os.getenv("LARK_CONFIG_DB_PATH", "data/lark_config.db")
    db_path = Path(db_path_str)

    # Create parent directory if it doesn't exist
    db_path.parent.mkdir(parents=True, exist_ok=True)

    return db_path


def init_config_database(db_path: Path | None = None) -> None:
    """Initialize the SQLite configuration database.

    Creates the database file and all required tables if they don't exist.

    Parameters
    ----------
        db_path: Path to the database file (defaults to get_config_db_path())

    Example
    ----------
        >>> init_config_database()
        >>> # Database created at data/lark_config.db
    """
    if db_path is None:
        db_path = get_config_db_path()

    # Create engine
    engine = create_engine(f"sqlite:///{db_path}", echo=False)

    # Create all tables
    ConfigBase.metadata.create_all(engine)


def add_default_application_from_env(
    db_path: Path | None = None, encryption_key: bytes | None = None
) -> Application | None:
    """Add default application from environment variables if configured.

    Reads LARK_APP_ID and LARK_APP_SECRET from environment and adds them
    to the database if both are present.

    Parameters
    ----------
        db_path: Path to the database file (defaults to get_config_db_path())
        encryption_key: Fernet encryption key (defaults to LARK_CONFIG_ENCRYPTION_KEY env var)

    Returns
    ----------
        Application object if added, None if env vars not set

    Raises
    ----------
        ValueError: If encryption key is not provided and not in environment

    Example
    ----------
        >>> os.environ["LARK_APP_ID"] = "cli_test123"
        >>> os.environ["LARK_APP_SECRET"] = "secret123"
        >>> os.environ["LARK_CONFIG_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
        >>> app = add_default_application_from_env()
        >>> print(app.app_id)
        cli_test123
    """
    app_id = os.getenv("LARK_APP_ID")
    app_secret = os.getenv("LARK_APP_SECRET")

    if not app_id or not app_secret:
        return None

    if encryption_key is None:
        key_str = os.getenv("LARK_CONFIG_ENCRYPTION_KEY")
        if not key_str:
            raise ValueError(
                "LARK_CONFIG_ENCRYPTION_KEY environment variable is required "
                "for encrypting application secrets"
            )
        encryption_key = key_str.encode()

    if db_path is None:
        db_path = get_config_db_path()

    # Create engine and session
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    session_local = sessionmaker(bind=engine)
    session = session_local()

    try:
        # Check if application already exists
        existing_app = session.query(Application).filter_by(app_id=app_id).first()
        if existing_app:
            return existing_app

        # Create new application
        app = Application(
            app_id=app_id,
            app_name=os.getenv("LARK_APP_NAME", "Default Application"),
            description=os.getenv("LARK_APP_DESCRIPTION", "Added from environment variables"),
            status="active",
        )
        app.set_encrypted_secret(app_secret, encryption_key)

        session.add(app)
        session.commit()
        session.refresh(app)

        return app

    finally:
        session.close()


def setup_config_database(db_path: Path | None = None, add_default_app: bool = True) -> None:
    """Complete setup of configuration database.

    Initializes the database and optionally adds default application from
    environment variables.

    Parameters
    ----------
        db_path: Path to the database file (defaults to get_config_db_path())
        add_default_app: Whether to add default app from env vars (default True)

    Example
    ----------
        >>> setup_config_database()
        >>> # Database initialized and default app added if env vars present
    """
    init_config_database(db_path)

    if add_default_app:
        add_default_application_from_env(db_path)
