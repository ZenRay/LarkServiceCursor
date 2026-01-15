"""
CardKit module data models.

This module defines Pydantic models for Lark CardKit operations,
including card configurations, elements, callback events, and related structures.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class CardElementTag(str, Enum):
    """Supported card element tags."""

    HEADER = "header"
    DIV = "div"
    ACTION = "action"
    HR = "hr"
    IMAGE = "image"
    MARKDOWN = "markdown"
    FORM = "form"


class CardTemplateType(str, Enum):
    """Predefined card template types."""

    APPROVAL = "approval"
    NOTIFICATION = "notification"
    FORM = "form"


class CardElement(BaseModel):
    """
    Card element base model.

    Represents a single element in a Lark interactive card.
    Elements can be text, images, buttons, forms, etc.

    Attributes
    ----------
        tag : str
            Element tag (e.g., "div", "action", "markdown")
        **kwargs : Any
            Additional element-specific properties

    Examples
    --------
        >>> element = CardElement(
        ...     tag="div",
        ...     text={"tag": "lark_md", "content": "**Bold text**"}
        ... )
    """

    tag: str = Field(..., description="Element tag")
    # Allow arbitrary fields for element-specific properties
    model_config = {"extra": "allow"}


class CardConfig(BaseModel):
    """
    Interactive card configuration.

    Defines the structure and content of a Lark interactive card.
    Cards consist of a header and a list of elements.

    Attributes
    ----------
        header : Optional[Dict[str, Any]]
            Card header configuration
        elements : List[Dict[str, Any]]
            List of card elements (div, action, etc.)
        card_link : Optional[Dict[str, str]]
            Card link configuration

    Examples
    --------
        >>> config = CardConfig(
        ...     header={"title": {"tag": "plain_text", "content": "Approval"}},
        ...     elements=[
        ...         {"tag": "div", "text": {"tag": "lark_md", "content": "**Name**: John"}},
        ...         {"tag": "action", "actions": [{"tag": "button", "text": {"tag": "plain_text", "content": "Approve"}}]}
        ...     ]
        ... )
    """

    header: dict[str, Any] | None = Field(None, description="Card header")
    elements: list[dict[str, Any]] = Field(default_factory=list, description="Card elements")
    card_link: dict[str, str] | None = Field(None, description="Card link")

    @field_validator("elements")
    @classmethod
    def validate_elements_not_empty(cls, v: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Validate that elements list is not empty."""
        if not v:
            raise ValueError("Card must have at least one element")
        return v


class CallbackEvent(BaseModel):
    """
    Interactive card callback event.

    Represents a callback event triggered by user interaction with a card.
    Events are sent by Lark servers when users click buttons, submit forms, etc.

    Attributes
    ----------
        event_type : str
            Event type (e.g., "card.action.trigger")
        card_id : Optional[str]
            Card ID
        user_id : str
            User who triggered the action
        action : Dict[str, Any]
            Action payload
        signature : str
            Lark callback signature for verification
        timestamp : str
            Event timestamp
        app_id : str
            Application ID

    Examples
    --------
        >>> event = CallbackEvent(
        ...     event_type="card.action.trigger",
        ...     user_id="ou_a1b2c3d4e5f6g7h8",
        ...     action={"value": "approve", "tag": "button"},
        ...     signature="abc123",
        ...     timestamp="2026-01-15T10:30:00Z",
        ...     app_id="cli_a1b2c3d4e5f6g7h8"
        ... )
    """

    event_type: str = Field(..., description="Event type")
    card_id: str | None = Field(None, description="Card ID")
    user_id: str = Field(..., description="User who triggered the action")
    action: dict[str, Any] = Field(..., description="Action payload")
    signature: str = Field(..., description="Lark callback signature")
    timestamp: str = Field(..., description="Event timestamp")
    app_id: str = Field(..., description="Application ID")

    @field_validator("signature")
    @classmethod
    def validate_signature_not_empty(cls, v: str) -> str:
        """Validate that signature is not empty."""
        if not v or not v.strip():
            raise ValueError("Callback signature cannot be empty")
        return v


class CardUpdateRequest(BaseModel):
    """
    Card update request.

    Used to update an existing card's content.

    Attributes
    ----------
        message_id : str
            Message ID of the card to update
        card_content : CardConfig
            New card content
        app_id : str
            Application ID

    Examples
    --------
        >>> request = CardUpdateRequest(
        ...     message_id="om_a1b2c3d4e5f6g7h8",
        ...     card_content=CardConfig(elements=[...]),
        ...     app_id="cli_a1b2c3d4e5f6g7h8"
        ... )
    """

    message_id: str = Field(..., min_length=1, description="Message ID")
    card_content: CardConfig = Field(..., description="New card content")
    app_id: str = Field(..., pattern=r"^cli_[a-z0-9]{16}$", description="Lark app ID")


class CardUpdateResponse(BaseModel):
    """
    Card update response for callback.

    Used to return updated card content in response to a callback event.

    Attributes
    ----------
        card : Dict[str, Any]
            Updated card JSON structure
        toast : Optional[Dict[str, str]]
            Toast message to display to user

    Examples
    --------
        >>> response = CardUpdateResponse(
        ...     card={"header": {...}, "elements": [...]},
        ...     toast={"type": "success", "content": "Approved successfully"}
        ... )
    """

    card: dict[str, Any] = Field(..., description="Updated card JSON")
    toast: dict[str, str] | None = Field(None, description="Toast message")


class CallbackHandler(BaseModel):
    """
    Callback handler registration.

    Defines a handler function for processing card callback events.

    Attributes
    ----------
        event_type : str
            Event type to handle (e.g., "card.action.trigger")
        action_value : Optional[str]
            Specific action value to match (e.g., "approve")
        handler_name : str
            Name of the handler function

    Examples
    --------
        >>> handler = CallbackHandler(
        ...     event_type="card.action.trigger",
        ...     action_value="approve",
        ...     handler_name="handle_approval"
        ... )
    """

    event_type: str = Field(..., description="Event type to handle")
    action_value: str | None = Field(None, description="Action value to match")
    handler_name: str = Field(..., min_length=1, description="Handler function name")
