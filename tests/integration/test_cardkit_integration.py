"""
Integration tests for CardKit module.

Tests the integration between CardBuilder, CallbackHandler, and CardUpdater.
"""

from unittest.mock import MagicMock, Mock

import pytest

from lark_service.cardkit.builder import CardBuilder
from lark_service.cardkit.callback_handler import CallbackHandler
from lark_service.cardkit.updater import CardUpdater
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.exceptions import InvalidParameterError, ValidationError


@pytest.fixture
def mock_credential_pool():
    """Create mock credential pool with SDK client."""
    pool = Mock(spec=CredentialPool)

    # Mock SDK client
    mock_client = MagicMock()

    # Mock card update response
    mock_update_response = MagicMock()
    mock_update_response.success.return_value = True
    mock_client.im.v1.message.patch.return_value = mock_update_response

    pool._get_sdk_client.return_value = mock_client

    return pool


@pytest.fixture
def card_builder():
    """Create CardBuilder instance."""
    return CardBuilder()


@pytest.fixture
def callback_handler():
    """Create CallbackHandler instance."""
    return CallbackHandler(
        verification_token="test_verification_token", encrypt_key="test_encrypt_key"
    )


@pytest.fixture
def card_updater(mock_credential_pool):
    """Create CardUpdater instance."""
    return CardUpdater(mock_credential_pool)


class TestCardBuilderIntegration:
    """Integration tests for CardBuilder."""

    def test_build_approval_card_integration(self, card_builder):
        """Test building approval card with full integration."""
        card = card_builder.build_approval_card(
            title="请假申请",
            applicant="张三",
            fields={"类型": "年假", "天数": "3天", "理由": "家庭旅行"},
            approve_action_id="approve_leave",
            reject_action_id="reject_leave",
            note="请审批",
        )

        # Verify card structure
        assert "header" in card
        assert card["header"]["title"]["content"] == "请假申请"
        assert "elements" in card
        assert len(card["elements"]) > 0

        # Verify action buttons
        action_elements = [e for e in card["elements"] if e.get("tag") == "action"]
        assert len(action_elements) == 1
        assert len(action_elements[0]["actions"]) == 2

    def test_build_notification_card_integration(self, card_builder):
        """Test building notification card with full integration."""
        card = card_builder.build_notification_card(
            title="系统通知",
            content="系统将于今晚 22:00 进行维护",
            level="warning",
            action_text="查看详情",
            action_url="https://example.com/maintenance",
        )

        # Verify card structure
        assert card["header"]["title"]["content"] == "系统通知"
        assert card["header"]["template"] == "orange"  # warning level
        assert len(card["elements"]) >= 2  # content + action

    def test_build_form_card_integration(self, card_builder):
        """Test building form card with full integration."""
        fields = [
            {
                "label": "姓名",
                "name": "name",
                "type": "input",
                "placeholder": "请输入姓名",
                "required": True,
            },
            {
                "label": "反馈内容",
                "name": "feedback",
                "type": "textarea",
                "placeholder": "请输入反馈内容",
                "required": True,
            },
            {
                "label": "类型",
                "name": "type",
                "type": "select",
                "placeholder": "请选择类型",
                "options": ["功能建议", "Bug反馈", "其他"],
                "required": False,
            },
        ]

        card = card_builder.build_form_card(
            title="反馈表单",
            fields=fields,
            submit_action_id="submit_feedback",
            cancel_action_id="cancel_feedback",
        )

        # Verify card structure
        assert card["header"]["title"]["content"] == "反馈表单"

        # Verify form fields (each field has label + input = 2 elements)
        # Plus divider and action buttons
        assert len(card["elements"]) >= len(fields) * 2 + 2

    def test_build_card_with_empty_elements_error(self, card_builder):
        """Test building card with empty elements raises error."""
        with pytest.raises(InvalidParameterError, match="at least one element"):
            card_builder.build_card(
                header={"title": {"tag": "plain_text", "content": "Test"}}, elements=[]
            )


class TestCallbackHandlerIntegration:
    """Integration tests for CallbackHandler."""

    def test_handle_url_verification_integration(self, callback_handler):
        """Test handling URL verification callback."""
        response = callback_handler.handle_url_verification(
            challenge="test_challenge_string", token="test_verification_token"
        )

        assert response["challenge"] == "test_challenge_string"

    def test_handle_url_verification_token_mismatch_error(self, callback_handler):
        """Test URL verification with wrong token raises error."""
        with pytest.raises(ValidationError, match="token mismatch"):
            callback_handler.handle_url_verification(
                challenge="test_challenge", token="wrong_token"
            )

    def test_register_and_route_callback_integration(self, callback_handler):
        """Test registering handler and routing callback."""

        # Register handler
        def test_handler(event):
            return {"status": "processed", "action": event.action.get("value")}

        callback_handler.register_handler("test_action", test_handler)

        # Route callback
        event_data = {
            "event_type": "card.action.trigger",
            "user_id": "ou_test_user",
            "action": {"action_id": "test_action", "value": {"key": "value"}},
            "signature": "test_signature",
            "timestamp": "1642512345",
            "app_id": "cli_test_app",
        }

        response = callback_handler.route_callback(event_data)

        assert response["status"] == "processed"
        assert response["action"] == {"key": "value"}

    def test_route_callback_without_handler_integration(self, callback_handler):
        """Test routing callback without registered handler."""
        event_data = {
            "event_type": "card.action.trigger",
            "user_id": "ou_test_user",
            "action": {"action_id": "unregistered_action", "value": {}},
            "signature": "test_signature",
            "timestamp": "1642512345",
            "app_id": "cli_test_app",
        }

        response = callback_handler.route_callback(event_data)

        # Should return default response
        assert response["status"] == "success"
        assert "Event received" in response["message"]

    def test_handle_callback_url_verification_integration(self, callback_handler):
        """Test handling callback with URL verification type."""
        request_data = {
            "type": "url_verification",
            "challenge": "test_challenge",
            "token": "test_verification_token",
        }

        response = callback_handler.handle_callback(request_data)

        assert response["challenge"] == "test_challenge"

    def test_handle_callback_card_action_integration(self, callback_handler):
        """Test handling callback with card action type."""

        # Register handler
        def test_handler(event):
            return {"status": "handled"}

        callback_handler.register_handler("test_action", test_handler)

        request_data = {
            "type": "card_action_trigger",
            "event_type": "card.action.trigger",
            "user_id": "ou_test_user",
            "action": {"action_id": "test_action", "value": {}},
            "signature": "test_signature",
            "timestamp": "1642512345",
            "app_id": "cli_test_app",
        }

        response = callback_handler.handle_callback(request_data)

        assert response["status"] == "handled"


class TestCardUpdaterIntegration:
    """Integration tests for CardUpdater."""

    def test_update_card_content_integration(self, card_updater, card_builder):
        """Test updating card content with full integration."""
        # Build new card content
        new_card = card_builder.build_notification_card(
            title="更新通知", content="卡片内容已更新", level="success"
        )

        # Update card
        result = card_updater.update_card_content(
            app_id="cli_a1b2c3d4e5f6g7h8", message_id="om_test_message_123", card_content=new_card
        )

        assert result["success"] is True
        assert result["message_id"] == "om_test_message_123"

    def test_build_update_response_integration(self, card_updater, card_builder):
        """Test building update response with full integration."""
        # Build new card content
        new_card = card_builder.build_notification_card(
            title="审批通过", content="您的申请已通过", level="success"
        )

        # Build update response
        response = card_updater.build_update_response(
            card_content=new_card, toast_message="操作成功!"
        )

        assert "card" in response
        assert "toast" in response
        assert response["toast"]["content"] == "操作成功!"

    def test_update_empty_card_content_error(self, card_updater):
        """Test updating with empty card content raises error."""
        with pytest.raises(InvalidParameterError, match="cannot be empty"):
            card_updater.update_card_content(
                app_id="cli_a1b2c3d4e5f6g7h8", message_id="om_test_message_123", card_content={}
            )


class TestEndToEndCardScenarios:
    """End-to-end integration tests for card scenarios."""

    def test_build_send_and_update_card_scenario(
        self, card_builder, card_updater, mock_credential_pool
    ):
        """Test complete scenario: build card, send it, then update it."""
        # Step 1: Build approval card
        original_card = card_builder.build_approval_card(
            title="请假申请",
            applicant="张三",
            fields={"类型": "年假", "天数": "3天"},
            approve_action_id="approve",
            reject_action_id="reject",
        )

        # Step 2: Simulate sending card (would use MessagingClient)
        message_id = "om_test_card_123"

        # Step 3: Build updated card (approved)
        updated_card = card_builder.build_notification_card(
            title="请假申请 - 已批准", content="您的请假申请已通过审批", level="success"
        )

        # Step 4: Update card
        result = card_updater.update_card_content(
            app_id="cli_a1b2c3d4e5f6g7h8", message_id=message_id, card_content=updated_card
        )

        assert result["success"] is True

    def test_card_callback_and_update_scenario(self, card_builder, callback_handler, card_updater):
        """Test complete scenario: receive callback and update card."""

        # Step 1: Register callback handler
        def approve_handler(event):
            # Build updated card
            updated_card = card_builder.build_notification_card(
                title="审批结果", content="申请已批准", level="success"
            )

            # Build update response
            return card_updater.build_update_response(
                card_content=updated_card, toast_message="审批成功!"
            )

        callback_handler.register_handler("approve_action", approve_handler)

        # Step 2: Simulate callback event
        event_data = {
            "event_type": "card.action.trigger",
            "user_id": "ou_approver",
            "action": {"action_id": "approve_action", "value": {"action": "approve"}},
            "signature": "test_signature",
            "timestamp": "1642512345",
            "app_id": "cli_test_app",
        }

        # Step 3: Route callback
        response = callback_handler.route_callback(event_data)

        # Verify response contains card update
        assert "card" in response
        assert "toast" in response
        assert response["toast"]["content"] == "审批成功!"

    def test_form_card_submission_scenario(self, card_builder, callback_handler, card_updater):
        """Test complete scenario: build form card and handle submission."""
        # Step 1: Build form card
        form_card = card_builder.build_form_card(
            title="反馈表单",
            fields=[
                {"label": "姓名", "name": "name", "type": "input", "required": True},
                {"label": "反馈", "name": "feedback", "type": "textarea", "required": True},
            ],
            submit_action_id="submit_feedback",
        )

        assert "elements" in form_card

        # Step 2: Register submission handler
        def submit_handler(event):
            # Process form data (would be in event.action.value)
            updated_card = card_builder.build_notification_card(
                title="提交成功", content="感谢您的反馈!", level="success"
            )

            return card_updater.build_update_response(
                card_content=updated_card, toast_message="提交成功!"
            )

        callback_handler.register_handler("submit_feedback", submit_handler)

        # Step 3: Simulate form submission
        event_data = {
            "event_type": "card.action.trigger",
            "user_id": "ou_user",
            "action": {
                "action_id": "submit_feedback",
                "value": {"name": "测试用户", "feedback": "这是一条测试反馈"},
            },
            "signature": "test_signature",
            "timestamp": "1642512345",
            "app_id": "cli_test_app",
        }

        response = callback_handler.route_callback(event_data)

        assert "card" in response
        assert "toast" in response
