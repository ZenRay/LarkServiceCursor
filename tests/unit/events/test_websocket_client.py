"""Unit tests for LarkWebSocketClient.

Tests cover connection lifecycle, reconnect backoff, heartbeat, and
event handler registration behavior.
"""

from __future__ import annotations

import asyncio
from unittest.mock import Mock

import pytest

from lark_service.events.exceptions import WebSocketConnectionError
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
    mock_lark.ws.Client.return_value = ws_client
    mock_lark.LogLevel.INFO = "INFO"

    monkeypatch.setattr("lark_service.events.websocket_client.lark", mock_lark)
    return mock_lark


def test_websocket_client_connect_success(mock_lark: Mock) -> None:
    """Test WebSocket client successfully establishes connection."""
    config = WebSocketConfig(app_id="cli_test1234567890ab", app_secret="secret")
    client = LarkWebSocketClient(config)
    client.register_handler("card.action.trigger", lambda event: event)

    client.connect()

    ws_client = mock_lark.ws.Client.return_value
    ws_client.start.assert_called_once()
    assert client.status.is_connected is True
    assert client.is_connected() is True


def test_websocket_client_reconnect_with_backoff(mock_lark: Mock) -> None:
    """Test WebSocket client reconnects with exponential backoff."""
    from unittest.mock import patch

    config = WebSocketConfig(app_id="cli_test1234567890ab", app_secret="secret")
    client = LarkWebSocketClient(config)

    connect_mock = Mock(
        side_effect=[
            WebSocketConnectionError("fail", app_id="cli_test1234567890ab"),
            WebSocketConnectionError("fail", app_id="cli_test1234567890ab"),
            None,
        ]
    )
    client.connect = connect_mock  # type: ignore[assignment]

    sleep_calls: list[float] = []

    def fake_sleep(delay: float) -> None:
        sleep_calls.append(delay)

    with patch("time.sleep", fake_sleep):
        client._reconnect_with_backoff()

    assert sleep_calls[:3] == [1, 2, 4]
    assert connect_mock.call_count == 3


@pytest.mark.asyncio
async def test_websocket_client_heartbeat_records() -> None:
    """Test heartbeat loop records heartbeat events."""
    config = WebSocketConfig(
        app_id="cli_test1234567890ab",
        app_secret="secret",
        heartbeat_interval=0.01,
    )
    client = LarkWebSocketClient(config)

    client._start_heartbeat()
    await asyncio.sleep(0.03)
    client.disconnect()

    assert client.status.heartbeat_count > 0
    assert client.status.last_heartbeat_at is not None


def test_websocket_client_register_handler(mock_lark: Mock) -> None:
    """Test event handler registration uses SDK dispatcher."""
    config = WebSocketConfig(app_id="cli_test1234567890ab", app_secret="secret")
    client = LarkWebSocketClient(config)
    handler = Mock()

    client.register_handler("card.action.trigger", handler)
    client.connect()

    builder = mock_lark.EventDispatcherHandler.builder.return_value
    builder.register_p2_card_action_trigger.assert_called_once_with(handler)
