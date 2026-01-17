"""Unit tests for CardKit CardUpdater.

Tests card content update operations.
"""

import pytest

from lark_service.cardkit.updater import CardUpdater
from lark_service.core.exceptions import InvalidParameterError


@pytest.fixture
def card_updater() -> CardUpdater:
    """Create CardUpdater instance with mock credentials."""
    from unittest.mock import Mock

    mock_pool = Mock()
    mock_pool._get_sdk_client.return_value = Mock()
    return CardUpdater(credential_pool=mock_pool)


class TestCardUpdater:
    """Test CardUpdater methods."""

    def test_init(self) -> None:
        """Test initialization."""
        from unittest.mock import Mock

        pool = Mock()
        updater = CardUpdater(credential_pool=pool)

        assert updater.credential_pool == pool

    def test_update_card_success(self, card_updater: CardUpdater) -> None:
        """Test successful card update."""
        from unittest.mock import Mock

        mock_response = Mock()
        mock_response.success.return_value = True

        mock_client = card_updater.credential_pool._get_sdk_client.return_value
        mock_client.im.v1.message.patch.return_value = mock_response

        card_content = {"elements": [{"tag": "div", "text": {"content": "Updated"}}]}

        result = card_updater.update_card_content(
            app_id="cli_test1234567890ab",
            message_id="om_test_message_123",
            card_content=card_content,
        )

        assert result["success"] is True

    def test_update_card_empty_content(
        self, card_updater: CardUpdater
    ) -> None:
        """Test update card with empty content."""
        with pytest.raises(InvalidParameterError):
            card_updater.update_card_content(
                app_id="cli_test1234567890ab",
                message_id="om_test",
                card_content={},
            )

    def test_update_card_empty_message_id(
        self, card_updater: CardUpdater
    ) -> None:
        """Test update card with empty message_id."""
        with pytest.raises(InvalidParameterError):
            card_updater.update_card_content(
                app_id="cli_test1234567890ab",
                message_id="",
                card_content={"elements": []},
            )
