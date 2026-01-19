"""Configuration loader for Lark Service.

This module provides configuration loading from environment variables
with validation and type safety.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class Config:
    """Lark Service configuration.

    Loads configuration from environment variables with validation.

    Attributes
    ----------
        postgres_host: PostgreSQL host
        postgres_port: PostgreSQL port
        postgres_db: PostgreSQL database name
        postgres_user: PostgreSQL username
        postgres_password: PostgreSQL password
        rabbitmq_host: RabbitMQ host
        rabbitmq_port: RabbitMQ port
        rabbitmq_user: RabbitMQ username
        rabbitmq_password: RabbitMQ password
        config_encryption_key: Fernet encryption key for app secrets
        config_db_path: Path to SQLite configuration database
        log_level: Logging level (DEBUG/INFO/WARNING/ERROR)
        max_retries: Maximum number of API retry attempts
        retry_backoff_base: Base delay for exponential backoff (seconds)
        token_refresh_threshold: Token refresh threshold (0.0-1.0)
        websocket_max_reconnect_retries: Maximum WebSocket reconnection attempts
        websocket_heartbeat_interval: WebSocket heartbeat interval (seconds)
        websocket_fallback_to_http: Enable fallback to HTTP callback on failure
        auth_card_include_description: Include detailed description in auth cards
        auth_card_template_id: Custom auth card template ID (optional)
        auth_token_refresh_threshold: Threshold for user access token refresh (0.0-1.0)
        auth_session_expiry_seconds: Auth session expiry time (seconds)
        auth_request_rate_limit: Max auth requests per user per minute
        user_info_sync_enabled: Enable user info synchronization
        user_info_sync_schedule: User info sync cron schedule

    Example
    ----------
        >>> config = Config.load_from_env()
        >>> print(config.postgres_host)
        localhost
    """

    # PostgreSQL configuration
    postgres_host: str
    postgres_port: int
    postgres_db: str
    postgres_user: str
    postgres_password: str

    # RabbitMQ configuration
    rabbitmq_host: str
    rabbitmq_port: int
    rabbitmq_user: str
    rabbitmq_password: str

    # Security
    config_encryption_key: bytes

    # Application
    config_db_path: Path
    log_level: str
    max_retries: int
    retry_backoff_base: float
    token_refresh_threshold: float

    # WebSocket Authentication
    websocket_max_reconnect_retries: int
    websocket_heartbeat_interval: int
    websocket_fallback_to_http: bool
    auth_card_include_description: bool
    auth_card_template_id: str | None
    auth_token_refresh_threshold: float
    auth_session_expiry_seconds: int
    auth_request_rate_limit: int
    user_info_sync_enabled: bool
    user_info_sync_schedule: str

    @classmethod
    def load_from_env(cls, env_file: Path | None = None) -> "Config":
        """Load configuration from environment variables.

        Parameters
        ----------
            env_file: Path to .env file (optional, defaults to .env in current directory)

        Returns
        ----------
            Config instance with loaded values

        Raises
        ----------
            ValueError: If required environment variables are missing
            FileNotFoundError: If specified env_file doesn't exist

        Example
        ----------
            >>> config = Config.load_from_env()
            >>> config = Config.load_from_env(Path("/path/to/.env"))
        """
        # Load .env file if it exists
        if env_file:
            if not env_file.exists():
                raise FileNotFoundError(f".env file not found: {env_file}")
            load_dotenv(env_file)
        else:
            load_dotenv()  # Load from default .env location

        # Validate required variables
        required_vars = [
            "POSTGRES_HOST",
            "POSTGRES_DB",
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            "LARK_CONFIG_ENCRYPTION_KEY",
        ]

        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

        # Parse and validate encryption key
        encryption_key_str = os.getenv("LARK_CONFIG_ENCRYPTION_KEY", "")
        try:
            encryption_key = encryption_key_str.encode()
            # Validate it's a valid Fernet key (will raise if invalid)
            from cryptography.fernet import Fernet

            Fernet(encryption_key)
        except Exception as e:
            raise ValueError(f"Invalid LARK_CONFIG_ENCRYPTION_KEY: {e}") from e

        # Parse token refresh threshold
        threshold_str = os.getenv("TOKEN_REFRESH_THRESHOLD", "0.1")
        try:
            threshold = float(threshold_str)
            if not 0.0 <= threshold <= 1.0:
                raise ValueError("TOKEN_REFRESH_THRESHOLD must be between 0.0 and 1.0")
        except ValueError as e:
            raise ValueError(f"Invalid TOKEN_REFRESH_THRESHOLD: {e}") from e

        # Parse auth token refresh threshold
        auth_threshold_str = os.getenv("AUTH_TOKEN_REFRESH_THRESHOLD", "0.8")
        try:
            auth_threshold = float(auth_threshold_str)
            if not 0.0 <= auth_threshold <= 1.0:
                raise ValueError("AUTH_TOKEN_REFRESH_THRESHOLD must be between 0.0 and 1.0")
        except ValueError as e:
            raise ValueError(f"Invalid AUTH_TOKEN_REFRESH_THRESHOLD: {e}") from e

        return cls(
            # PostgreSQL
            postgres_host=os.getenv("POSTGRES_HOST", "localhost"),
            postgres_port=int(os.getenv("POSTGRES_PORT", "5432")),
            postgres_db=os.getenv("POSTGRES_DB", "lark_service"),
            postgres_user=os.getenv("POSTGRES_USER", "lark"),
            postgres_password=os.getenv("POSTGRES_PASSWORD", ""),
            # RabbitMQ
            rabbitmq_host=os.getenv("RABBITMQ_HOST", "localhost"),
            rabbitmq_port=int(os.getenv("RABBITMQ_PORT", "5672")),
            rabbitmq_user=os.getenv("RABBITMQ_USER", "lark"),
            rabbitmq_password=os.getenv("RABBITMQ_PASSWORD", ""),
            # Security
            config_encryption_key=encryption_key,
            # Application
            config_db_path=Path(os.getenv("LARK_CONFIG_DB_PATH", "data/lark_config.db")),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            retry_backoff_base=float(os.getenv("RETRY_BACKOFF_BASE", "1.0")),
            token_refresh_threshold=threshold,
            # WebSocket Authentication
            websocket_max_reconnect_retries=int(os.getenv("WEBSOCKET_MAX_RECONNECT_RETRIES", "10")),
            websocket_heartbeat_interval=int(os.getenv("WEBSOCKET_HEARTBEAT_INTERVAL", "30")),
            websocket_fallback_to_http=os.getenv("WEBSOCKET_FALLBACK_TO_HTTP", "true").lower()
            == "true",
            auth_card_include_description=os.getenv("AUTH_CARD_INCLUDE_DESCRIPTION", "true").lower()
            == "true",
            auth_card_template_id=os.getenv("AUTH_CARD_TEMPLATE_ID") or None,
            auth_token_refresh_threshold=auth_threshold,
            auth_session_expiry_seconds=int(os.getenv("AUTH_SESSION_EXPIRY_SECONDS", "600")),
            auth_request_rate_limit=int(os.getenv("AUTH_REQUEST_RATE_LIMIT", "5")),
            user_info_sync_enabled=os.getenv("USER_INFO_SYNC_ENABLED", "false").lower() == "true",
            user_info_sync_schedule=os.getenv("USER_INFO_SYNC_SCHEDULE", "0 2 * * *"),
        )

    def get_postgres_url(self) -> str:
        """Get PostgreSQL connection URL.

        Returns
        ----------
            SQLAlchemy-compatible PostgreSQL URL

        Example
        ----------
            >>> config = Config.load_from_env()
            >>> url = config.get_postgres_url()
            >>> print(url)
            postgresql://lark:***@localhost:5432/lark_service
        """
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    def get_rabbitmq_url(self) -> str:
        """Get RabbitMQ connection URL.

        Returns
        ----------
            Pika-compatible RabbitMQ URL

        Example
        ----------
            >>> config = Config.load_from_env()
            >>> url = config.get_rabbitmq_url()
            >>> print(url)
            amqp://lark:***@localhost:5672/
        """
        return (
            f"amqp://{self.rabbitmq_user}:{self.rabbitmq_password}"
            f"@{self.rabbitmq_host}:{self.rabbitmq_port}/"
        )
