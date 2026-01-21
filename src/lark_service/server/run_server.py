#!/usr/bin/env python3
"""Startup script for Lark Callback Server.

This script initializes all required services and starts the HTTP callback
server for handling Feishu callbacks.

IMPORTANT: This server is OPTIONAL and only needed if you want to receive
card interaction callbacks via HTTP. If you don't need card authorization
or other HTTP callbacks, you don't need to run this server.

To enable the callback server, set in .env:
    CALLBACK_SERVER_ENABLED=true

Usage:
    python src/lark_service/server/run_server.py
"""

import os
import sys
import time
from pathlib import Path

# Add src to path for imports (must be before other imports)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from lark_service.auth.card_auth_handler import CardAuthHandler  # noqa: E402
from lark_service.auth.session_manager import AuthSessionManager  # noqa: E402
from lark_service.clients.messaging import MessagingClient  # noqa: E402
from lark_service.config import Config  # noqa: E402
from lark_service.core.app_manager import ApplicationManager  # noqa: E402
from lark_service.core.credential_pool import CredentialPool  # noqa: E402
from lark_service.core.token_storage import TokenStorageService  # noqa: E402
from lark_service.models.base import Base  # noqa: E402
from lark_service.scheduler.scheduler import scheduler_service  # noqa: E402
from lark_service.scheduler.tasks import register_scheduled_tasks  # noqa: E402
from lark_service.server.manager import CallbackServerManager  # noqa: E402
from lark_service.utils.logger import get_logger  # noqa: E402

logger = get_logger()


def init_services() -> tuple[CardAuthHandler, str, str | None]:
    """Initialize all required services.

    Returns
    -------
        tuple: (card_auth_handler, verification_token, encrypt_key)
    """
    # Load environment variables
    load_dotenv()

    # Get configuration
    app_id = os.getenv("LARK_APP_ID")
    app_secret = os.getenv("LARK_APP_SECRET")
    verification_token = os.getenv("LARK_VERIFICATION_TOKEN")
    encrypt_key = os.getenv("LARK_ENCRYPT_KEY")
    encryption_key = os.getenv("LARK_CONFIG_ENCRYPTION_KEY")

    if not app_id or not app_secret or not verification_token:
        raise ValueError(
            "Missing required environment variables: "
            "LARK_APP_ID, LARK_APP_SECRET, LARK_VERIFICATION_TOKEN"
        )

    logger.info("Initializing services...")

    # Initialize configuration
    config = Config(
        max_retries=3,
        retry_backoff_base=2,
        timeout=30,
    )

    # Initialize application manager
    app_manager = ApplicationManager(encryption_key=encryption_key)
    try:
        app_manager.add_application(
            app_id=app_id,
            app_name=os.getenv("LARK_APP_NAME", "Lark Service"),
            app_secret=app_secret,
            verification_token=verification_token,
            encrypt_key=encrypt_key,
        )
        logger.info(f"Application registered: {app_id}")
    except Exception as e:
        logger.info(f"Application already exists: {e}")

    # Initialize token storage
    token_storage = TokenStorageService(db_path=os.getenv("TOKEN_DB_PATH", "data/config.db"))

    # Initialize credential pool
    pool = CredentialPool(
        config=config,
        app_manager=app_manager,
        token_storage=token_storage,
    )
    logger.info("Credential pool initialized")

    # Initialize database
    db_url = (
        f"postgresql://{os.getenv('POSTGRES_USER', 'lark_user')}:"
        f"{os.getenv('POSTGRES_PASSWORD', 'lark_password_123')}@"
        f"{os.getenv('POSTGRES_HOST', 'localhost')}:"
        f"{os.getenv('POSTGRES_PORT', '5432')}/"
        f"{os.getenv('POSTGRES_DB', 'lark_service')}"
    )
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine)
    db_session = session_local()
    logger.info("Database initialized")

    # Initialize authorization session manager
    session_manager = AuthSessionManager(db=db_session)

    # Initialize messaging client
    messaging_client = MessagingClient(credential_pool=pool)

    # Initialize card authorization handler
    card_auth_handler = CardAuthHandler(
        session_manager=session_manager,
        messaging_client=messaging_client,
        app_id=app_id,
        app_secret=app_secret,
    )
    logger.info("Card authorization handler initialized")

    return card_auth_handler, verification_token, encrypt_key


def main() -> None:
    """Main entry point."""
    try:
        # Initialize services
        card_auth_handler, verification_token, encrypt_key = init_services()

        # Initialize and start scheduler
        logger.info("Initializing scheduler...")
        register_scheduled_tasks(scheduler_service)
        scheduler_service.start()
        logger.info("Scheduler started successfully")

        # Create callback server manager
        manager = CallbackServerManager(
            verification_token=verification_token,
            encrypt_key=encrypt_key,
        )

        # Check if server is enabled
        if not manager.is_enabled():
            logger.warning("=" * 70)
            logger.warning("  Callback Server is DISABLED")
            logger.warning("=" * 70)
            logger.warning("Set CALLBACK_SERVER_ENABLED=true in .env to enable")
            logger.warning("=" * 70)
            # Shutdown scheduler before exit
            scheduler_service.shutdown()
            sys.exit(0)

        # Register callback handlers
        # 1. Card authorization handler
        manager.register_card_auth_handler(card_auth_handler)

        # TODO: Add more handlers here as needed
        # manager.register_handler("message_receive", message_handler)
        # manager.register_handler("contact_update", contact_handler)

        # Display startup information
        status = manager.get_status()
        logger.info("=" * 70)
        logger.info("  Lark Callback Server Ready")
        logger.info("=" * 70)
        logger.info(f"Server: http://{status['host']}:{status['port']}")
        logger.info(f"Health: http://{status['host']}:{status['port']}/health")
        logger.info(f"Handlers: {', '.join(status['handlers'])}")
        logger.info("=" * 70)
        logger.info("\n配置飞书开放平台回调地址:")
        logger.info("  → https://your-domain.com/callback")
        logger.info("\n本地测试可使用 ngrok 暴露端口:")
        logger.info(f"  → ngrok http {status['port']}")
        logger.info("=" * 70)

        # Start server
        manager.start()

        # Keep main thread alive
        logger.info("\nPress Ctrl+C to stop...")
        try:
            while manager.is_running():
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("\nShutting down...")
            # Shutdown scheduler first
            scheduler_service.shutdown(wait=True)
            logger.info("Scheduler stopped")
            # Then stop the server
            manager.stop()

    except KeyboardInterrupt:
        logger.info("\nServer stopped by user")
        # Ensure scheduler is stopped
        import contextlib

        with contextlib.suppress(Exception):
            scheduler_service.shutdown(wait=False)
    except Exception as e:
        logger.error(f"Failed to start server: {e}", exc_info=True)
        # Ensure scheduler is stopped on error
        import contextlib

        with contextlib.suppress(Exception):
            scheduler_service.shutdown(wait=False)
        sys.exit(1)


if __name__ == "__main__":
    main()
