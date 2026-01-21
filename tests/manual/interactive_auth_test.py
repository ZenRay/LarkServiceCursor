#!/usr/bin/env python3
"""Interactive authorization flow test script.

T081 [Phase 8] Create manual interactive test script

This script tests the real authorization flow with user interaction.

Usage:
    python tests/manual/interactive_auth_test.py

Steps:
    1. Start WebSocket client
    2. Send authorization card to your test account
    3. Click "Authorize" button in Feishu
    4. Verify token is received and stored
    5. Test aPaaS API call with token (optional)

Requirements:
    - APP_ID and APP_SECRET in .env file
    - PostgreSQL database running (or SQLite for testing)
    - Test user's OpenID
"""

import asyncio
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from dotenv import load_dotenv  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from lark_service.auth.card_auth_handler import CardAuthHandler  # noqa: E402
from lark_service.auth.session_manager import AuthSessionManager  # noqa: E402
from lark_service.core.models.auth_session import Base  # noqa: E402
from lark_service.events.types import WebSocketConfig  # noqa: E402
from lark_service.events.websocket_client import LarkWebSocketClient  # noqa: E402
from lark_service.messaging.client import MessagingClient  # noqa: E402


def print_header(text: str) -> None:
    """Print formatted header."""
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}\n")


def print_step(step_num: int, text: str) -> None:
    """Print formatted step."""
    print(f"\n[Step {step_num}] {text}")
    print("-" * 60)


def print_success(text: str) -> None:
    """Print success message."""
    print(f"✅ {text}")


def print_error(text: str) -> None:
    """Print error message."""
    print(f"❌ {text}")


def print_info(text: str) -> None:
    """Print info message."""
    print(f"ℹ️  {text}")


async def main() -> None:
    """Run interactive auth test."""
    print_header("Interactive Authorization Test")

    # Load environment variables
    load_dotenv()

    app_id = os.getenv("APP_ID")
    app_secret = os.getenv("APP_SECRET")
    db_url = os.getenv("DATABASE_URL", "sqlite:///./test_auth.db")

    if not app_id or not app_secret:
        print_error("APP_ID and APP_SECRET must be set in .env file")
        return

    print_info(f"Using APP_ID: {app_id[:10]}...")
    print_info(f"Using DATABASE: {db_url}")

    # Step 1: Initialize database
    print_step(1, "Initializing database...")
    try:
        engine = create_engine(db_url)
        Base.metadata.create_all(engine)
        session_local = sessionmaker(bind=engine)
        db_session = session_local()
        print_success("Database initialized")
    except Exception as e:
        print_error(f"Database initialization failed: {e}")
        return

    # Step 2: Initialize components
    print_step(2, "Initializing components...")
    try:
        auth_manager = AuthSessionManager(db_session)
        messaging_client = MessagingClient(app_id=app_id, app_secret=app_secret)
        card_handler = CardAuthHandler(
            session_manager=auth_manager,
            messaging_client=messaging_client,
            app_id=app_id,
            app_secret=app_secret,
        )
        print_success("Components initialized")
    except Exception as e:
        print_error(f"Component initialization failed: {e}")
        return

    # Step 3: Start WebSocket connection (optional)
    print_step(3, "Starting WebSocket connection...")
    websocket_enabled = input("Enable WebSocket connection? (y/n): ").lower() == "y"

    websocket_client = None
    if websocket_enabled:
        try:
            config = WebSocketConfig(
                app_id=app_id,
                app_secret=app_secret,
                max_reconnect_retries=3,
                heartbeat_interval=30,
            )
            websocket_client = LarkWebSocketClient(config)

            # Register card action handler
            async def handle_card_action(event):
                """Handle card action event."""
                print_info("Received card action event")
                response = await card_handler.handle_card_auth_event(event)
                return response

            websocket_client.register_handler("card.action.trigger", handle_card_action)

            await websocket_client.start()
            print_success("WebSocket connected")
        except Exception as e:
            print_error(f"WebSocket connection failed: {e}")
            print_info("Continuing without WebSocket...")
    else:
        print_info("WebSocket disabled - manual token entry mode")

    # Step 4: Get test user OpenID
    print_step(4, "Enter test user information...")
    test_user_id = input("Enter your OpenID (ou_xxx): ").strip()

    if not test_user_id:
        print_error("OpenID is required")
        if websocket_client:
            await websocket_client.disconnect()
        return

    # Step 5 & 6: Send authorization card (creates session internally)
    print_step(5, "Sending authorization card...")
    try:
        message_id = await card_handler.send_auth_card(user_id=test_user_id)
        print_success(f"Card sent successfully (message_id: {message_id})")
        print_info("📱 Please check Feishu and click 'Authorize' button")

        # Get the created session (in real implementation, we'd track this)
        # For now, create a test session
        session = auth_manager.create_session(
            app_id=app_id, user_id=test_user_id, auth_method="websocket_card"
        )
        print_success(f"Session created: {session.session_id}")
        print_info(f"Session expires at: {session.expires_at}")
    except Exception as e:
        print_error(f"Card sending failed: {e}")
        if websocket_client:
            await websocket_client.disconnect()
        return

    # Step 7: Wait for authorization
    print_step(7, "Waiting for authorization...")
    if websocket_enabled:
        print_info("Waiting for WebSocket event (max 120 seconds)...")
        for i in range(120):
            await asyncio.sleep(1)
            updated_session = auth_manager.get_session(session.session_id)
            if updated_session.state == "completed":
                print_success("Authorization completed!")
                print_info(f"User: {updated_session.user_name}")
                print_info(f"Email: {updated_session.email}")
                print_info(f"Mobile: {updated_session.mobile}")
                print_info(f"Token expires: {updated_session.token_expires_at}")
                break
            if i % 10 == 0 and i > 0:
                print_info(f"Still waiting... ({i}/120 seconds)")
        else:
            print_error("Timeout: Authorization not completed")
            if websocket_client:
                await websocket_client.disconnect()
            return
    else:
        print_info("Manual mode: Enter authorization details")
        auth_code = input("Enter authorization code (from card callback): ").strip()
        if auth_code:
            try:
                # Manually complete the session
                # In real scenario, this would be done by card_handler
                print_info("Processing authorization code...")
                # This is a simplified version - real implementation would call
                # card_handler._exchange_token and _fetch_user_info
                print_error("Manual token entry not fully implemented")
                print_info("Please use WebSocket mode for full functionality")
            except Exception as e:
                print_error(f"Authorization processing failed: {e}")
        else:
            print_error("No authorization code provided")
            if websocket_client:
                await websocket_client.disconnect()
            return

    # Step 8: Verify token retrieval
    print_step(8, "Verifying token retrieval...")
    try:
        token = auth_manager.get_active_token(app_id=app_id, user_id=test_user_id)
        if token:
            print_success("Token retrieved successfully")
            print_info(f"Token (first 20 chars): {token[:20]}...")
        else:
            print_error("Token not found")
    except Exception as e:
        print_error(f"Token retrieval failed: {e}")

    # Step 9: Test aPaaS API call (optional)
    print_step(9, "Test aPaaS API call (optional)...")
    test_api = input("Test aPaaS API call? (y/n): ").lower() == "y"

    if test_api:
        try:
            print_info("Testing aPaaS API call...")
            # This would require actual aPaaS client implementation
            print_info("aPaaS API test not implemented in this script")
            print_info("Token is available for use in aPaaS client")
        except Exception as e:
            print_error(f"API test failed: {e}")

    # Step 10: Cleanup
    print_step(10, "Cleaning up...")
    if websocket_client:
        await websocket_client.disconnect()
        print_success("WebSocket disconnected")

    db_session.close()
    print_success("Database session closed")

    print_header("Test Completed")
    print_info("Summary:")
    print_info(f"  - Session ID: {session.session_id}")
    print_info(f"  - User ID: {test_user_id}")
    print_info(f"  - Session State: {auth_manager.get_session(session.session_id).state}")
    print_info(f"  - Test Time: {datetime.now(UTC)}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback

        traceback.print_exc()
