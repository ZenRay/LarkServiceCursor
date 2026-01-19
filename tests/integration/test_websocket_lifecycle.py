"""Integration tests for WebSocket client lifecycle.

These tests validate start/stop flow with mocked SDK clients.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from lark_service.events.types import WebSocketConfig
from lark_service.events.websocket_client import LarkWebSocketClient


@pytest.fixture
def mock_lark(monkeypatch: pytest.MonkeyPatch) -> Mock:
    """Mock lark_oapi module in websocket_client."""
    mock_lark = Mock()
    builder = Mock()
    builder.register_p2_card_action_trigger.return_value = builder
    builder.build.return_value = Mock()
    mock_lark.EventDispatcherHandler.builder.return_value = builder

    ws_client = Mock()
    ws_client.stop = Mock()
    mock_lark.ws.Client.return_value = ws_client
    mock_lark.LogLevel.INFO = "INFO"

    monkeypatch.setattr("lark_service.events.websocket_client.lark", mock_lark)
    return mock_lark


@pytest.mark.asyncio
@pytest.mark.integration
async def test_websocket_client_start_and_disconnect(mock_lark: Mock) -> None:
    """Test start() establishes connection and disconnect() shuts down."""
    config = WebSocketConfig(
        app_id="cli_test1234567890ab",
        app_secret="secret",
        heartbeat_interval=0.01,
    )
    client = LarkWebSocketClient(config)
    client.register_handler("card.action.trigger", lambda event: event)

    await client.start()
    await client.disconnect()

    ws_client = mock_lark.ws.Client.return_value
    ws_client.start.assert_called_once()
    ws_client.stop.assert_called_once()
    assert client.status.is_connected is False
