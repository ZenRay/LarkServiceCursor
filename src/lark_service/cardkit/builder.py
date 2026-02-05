"""
Card builder for Lark CardKit.

This module provides a builder for constructing interactive cards
with various templates and components.
"""

from typing import Any

from lark_service.cardkit.models import CardConfig
from lark_service.core.exceptions import InvalidParameterError
from lark_service.utils.logger import get_logger

logger = get_logger()


class CardBuilder:
    """
    Builder for constructing Lark interactive cards.

    Supports two usage patterns:

    1. **Template Methods** (Quick & Easy): Use pre-built templates for common scenarios
    2. **Fluent API** (Flexible): Chain method calls to build custom cards

    Examples
    --------
    Template method (quick):

        >>> card = CardBuilder().build_notification_card(
        ...     title="System Alert",
        ...     content="Service maintenance scheduled",
        ...     level="warning"
        ... )

    Fluent API (flexible):

        >>> card = (CardBuilder()
        ...     .add_header("Custom Card", template="blue")
        ...     .add_markdown("**Important**: Please review")
        ...     .add_text("This is a custom notification")
        ...     .add_divider()
        ...     .add_button("Confirm", action_id="confirm")
        ...     .build()
        ... )

    Combined approach:

        >>> card = (CardBuilder()
        ...     .add_header("Alert", template="red")
        ...     .add_markdown("**Error**: System failure")
        ...     .add_button("View Details", url="https://status.example.com")
        ...     .build()
        ... )
    """

    def __init__(self) -> None:
        """Initialize CardBuilder with empty state."""
        self._header: dict[str, Any] | None = None
        self._elements: list[dict[str, Any]] = []
        self._card_link: dict[str, Any] | None = None

    # ========================================================================
    # Fluent API Methods (Chain-able)
    # ========================================================================

    def add_header(
        self,
        title: str,
        template: str = "blue",
        subtitle: str | None = None,
    ) -> "CardBuilder":
        """
        Add header to card (fluent API).

        Parameters
        ----------
            title : str
                Header title
            template : str
                Color template: "blue", "green", "red", "orange", "purple", "indigo"
            subtitle : str | None
                Optional subtitle text

        Returns
        -------
            CardBuilder
                Self for method chaining

        Examples
        --------
            >>> card = (CardBuilder()
            ...     .add_header("Welcome", template="green")
            ...     .add_text("Hello World")
            ...     .build()
            ... )
        """
        self._header = {
            "title": {"tag": "plain_text", "content": title},
            "template": template,
        }
        if subtitle:
            self._header["subtitle"] = {"tag": "plain_text", "content": subtitle}
        return self

    def add_markdown(self, content: str) -> "CardBuilder":
        """
        Add markdown text element (fluent API).

        Supports markdown formatting: **bold**, *italic*, [links](url), etc.

        Parameters
        ----------
            content : str
                Markdown content

        Returns
        -------
            CardBuilder
                Self for method chaining

        Examples
        --------
            >>> card = (CardBuilder()
            ...     .add_markdown("**Important**: Please review")
            ...     .build()
            ... )
        """
        self._elements.append({"tag": "div", "text": {"tag": "lark_md", "content": content}})
        return self

    def add_text(self, content: str) -> "CardBuilder":
        """
        Add plain text element (fluent API).

        Parameters
        ----------
            content : str
                Plain text content

        Returns
        -------
            CardBuilder
                Self for method chaining

        Examples
        --------
            >>> card = (CardBuilder()
            ...     .add_text("This is plain text")
            ...     .build()
            ... )
        """
        self._elements.append({"tag": "div", "text": {"tag": "plain_text", "content": content}})
        return self

    def add_divider(self) -> "CardBuilder":
        """
        Add horizontal divider (fluent API).

        Returns
        -------
            CardBuilder
                Self for method chaining

        Examples
        --------
            >>> card = (CardBuilder()
            ...     .add_text("Section 1")
            ...     .add_divider()
            ...     .add_text("Section 2")
            ...     .build()
            ... )
        """
        self._elements.append({"tag": "hr"})
        return self

    def add_button(
        self,
        text: str,
        action_id: str | None = None,
        url: str | None = None,
        button_type: str = "default",
        value: dict[str, Any] | None = None,
    ) -> "CardBuilder":
        """
        Add action button (fluent API).

        Parameters
        ----------
            text : str
                Button text
            action_id : str | None
                Action ID for callback handling
            url : str | None
                URL to open when clicked (alternative to action_id)
            button_type : str
                Button style: "default", "primary", "danger"
            value : dict[str, Any] | None
                Additional data to pass with action

        Returns
        -------
            CardBuilder
                Self for method chaining

        Examples
        --------
            >>> # Callback button
            >>> card = (CardBuilder()
            ...     .add_button("Confirm", action_id="confirm", button_type="primary")
            ...     .build()
            ... )

            >>> # URL button
            >>> card = (CardBuilder()
            ...     .add_button("Learn More", url="https://example.com")
            ...     .build()
            ... )
        """
        button: dict[str, Any] = {
            "tag": "button",
            "text": {"tag": "plain_text", "content": text},
            "type": button_type,
        }

        if action_id:
            button["action_id"] = action_id
            button["value"] = value or {"action": "click"}

        if url:
            button["url"] = url

        # Check if last element is action container, if so add to it
        if self._elements and self._elements[-1].get("tag") == "action":
            self._elements[-1]["actions"].append(button)
        else:
            self._elements.append({"tag": "action", "actions": [button]})

        return self

    def add_field(self, label: str, value: str) -> "CardBuilder":
        """
        Add key-value field (fluent API).

        Parameters
        ----------
            label : str
                Field label
            value : str
                Field value

        Returns
        -------
            CardBuilder
                Self for method chaining

        Examples
        --------
            >>> card = (CardBuilder()
            ...     .add_field("Name", "John Doe")
            ...     .add_field("Email", "john@example.com")
            ...     .build()
            ... )
        """
        self._elements.append(
            {"tag": "div", "text": {"tag": "lark_md", "content": f"**{label}**: {value}"}}
        )
        return self

    def add_image(self, image_key: str, alt: str = "", title: str | None = None) -> "CardBuilder":
        """
        Add image element (fluent API).

        Parameters
        ----------
            image_key : str
                Image key from Lark media upload
            alt : str
                Alt text for image
            title : str | None
                Optional image title

        Returns
        -------
            CardBuilder
                Self for method chaining

        Examples
        --------
            >>> card = (CardBuilder()
            ...     .add_image("img_xxx", alt="Product", title="New Product")
            ...     .build()
            ... )
        """
        img_element: dict[str, Any] = {
            "tag": "img",
            "img_key": image_key,
            "alt": {"tag": "plain_text", "content": alt},
        }
        if title:
            img_element["title"] = {"tag": "plain_text", "content": title}

        self._elements.append(img_element)
        return self

    def add_note(self, content: str, note_type: str = "default") -> "CardBuilder":
        """
        Add note/alert element (fluent API).

        Parameters
        ----------
            content : str
                Note content (supports markdown)
            note_type : str
                Note style: "default", "info", "warning", "error"

        Returns
        -------
            CardBuilder
                Self for method chaining

        Examples
        --------
            >>> card = (CardBuilder()
            ...     .add_note("**Important**: Please review", note_type="warning")
            ...     .build()
            ... )
        """
        self._elements.append(
            {
                "tag": "note",
                "elements": [{"tag": "plain_text", "content": content}],
            }
        )
        return self

    def add_card_link(self, url: str, text: str = "查看详情") -> "CardBuilder":
        """
        Add card-level link (fluent API).

        Makes entire card clickable.

        Parameters
        ----------
            url : str
                Link URL
            text : str
                Link text (default: "查看详情")

        Returns
        -------
            CardBuilder
                Self for method chaining

        Examples
        --------
            >>> card = (CardBuilder()
            ...     .add_text("Click anywhere to view")
            ...     .add_card_link("https://example.com")
            ...     .build()
            ... )
        """
        self._card_link = {
            "url": url,
            "text": {"tag": "plain_text", "content": text},
        }
        return self

    def build(self) -> dict[str, Any]:
        """
        Build final card and reset state (fluent API).

        Returns
        -------
            dict[str, Any]
                Complete card JSON structure

        Raises
        ------
            InvalidParameterError
                If no elements added

        Examples
        --------
            >>> card = (CardBuilder()
            ...     .add_header("Title")
            ...     .add_text("Content")
            ...     .build()
            ... )
        """
        if not self._elements:
            raise InvalidParameterError(
                "Card must have at least one element",
                details={"elements": self._elements},
            )

        card_dict: dict[str, Any] = {}

        if self._header:
            card_dict["header"] = self._header

        card_dict["elements"] = self._elements

        if self._card_link:
            card_dict["card_link"] = self._card_link

        # Validate using Pydantic model
        config = CardConfig(**card_dict)

        logger.debug(
            "Card built successfully (fluent API)",
            extra={"element_count": len(self._elements), "has_header": bool(self._header)},
        )

        # Reset state for reuse
        self._header = None
        self._elements = []
        self._card_link = None

        return config.model_dump(exclude_none=True)

    # ========================================================================
    # Template Methods (Quick & Easy)
    # ========================================================================

    def build_card(
        self,
        header: dict[str, Any] | None = None,
        elements: list[dict[str, Any]] | None = None,
        card_link: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Build a custom card with specified components.

        Parameters
        ----------
            header : dict[str, Any] | None
                Card header configuration
            elements : list[dict[str, Any]] | None
                List of card elements
            card_link : dict[str, Any] | None
                Card link configuration

        Returns
        -------
            dict[str, Any]
                Complete card JSON structure

        Raises
        ------
            InvalidParameterError
                If elements is empty

        Examples
        --------
            >>> card = builder.build_card(
            ...     header={"title": {"tag": "plain_text", "content": "Title"}},
            ...     elements=[{"tag": "div", "text": {...}}]
            ... )
        """
        if not elements:
            raise InvalidParameterError(
                "Card must have at least one element",
                details={"elements": elements},
            )

        card_dict: dict[str, Any] = {}

        if header:
            card_dict["header"] = header

        card_dict["elements"] = elements

        if card_link:
            card_dict["card_link"] = card_link

        # Validate using Pydantic model
        config = CardConfig(**card_dict)

        logger.debug(
            "Card built successfully",
            extra={"element_count": len(elements), "has_header": bool(header)},
        )

        return config.model_dump(exclude_none=True)

    def build_approval_card(
        self,
        title: str,
        applicant: str,
        fields: dict[str, str],
        approve_action_id: str,
        reject_action_id: str,
        note: str | None = None,
    ) -> dict[str, Any]:
        """
        Build an approval card template.

        Creates a card with applicant info, detail fields, and approve/reject buttons.

        Parameters
        ----------
            title : str
                Card title (e.g., "Leave Request")
            applicant : str
                Applicant name
            fields : dict[str, str]
                Detail fields as key-value pairs (e.g., {"Type": "Annual Leave"})
            approve_action_id : str
                Action ID for approve button
            reject_action_id : str
                Action ID for reject button
            note : str | None
                Optional note or description

        Returns
        -------
            dict[str, Any]
                Approval card JSON structure

        Examples
        --------
            >>> card = builder.build_approval_card(
            ...     title="Leave Request",
            ...     applicant="John Doe",
            ...     fields={"Type": "Annual Leave", "Days": "3", "Reason": "Family trip"},
            ...     approve_action_id="approve_leave",
            ...     reject_action_id="reject_leave",
            ...     note="Please review and approve"
            ... )
        """
        # Build header
        header = {
            "title": {"tag": "plain_text", "content": title},
            "template": "blue",
        }

        # Build elements
        elements: list[dict[str, Any]] = []

        # Applicant info
        elements.append(
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**申请人**: {applicant}",
                },
            }
        )

        # Add note if provided
        if note:
            elements.append(
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**备注**: {note}",
                    },
                }
            )

        # Add divider
        elements.append({"tag": "hr"})

        # Add detail fields
        for key, value in fields.items():
            elements.append(
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**{key}**: {value}",
                    },
                }
            )

        # Add divider before actions
        elements.append({"tag": "hr"})

        # Add action buttons
        elements.append(
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "批准"},
                        "type": "primary",
                        "value": {"action": "approve"},
                        "action_id": approve_action_id,
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "拒绝"},
                        "type": "danger",
                        "value": {"action": "reject"},
                        "action_id": reject_action_id,
                    },
                ],
            }
        )

        return self.build_card(header=header, elements=elements)

    def build_notification_card(
        self,
        title: str,
        content: str,
        level: str = "info",
        action_text: str | None = None,
        action_url: str | None = None,
        action_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Build a notification card template.

        Creates a simple notification card with optional action button.

        Parameters
        ----------
            title : str
                Notification title
            content : str
                Notification content (supports markdown)
            level : str
                Notification level: "info", "warning", "error", "success" (default: "info")
            action_text : str | None
                Optional action button text
            action_url : str | None
                Optional action button URL
            action_id : str | None
                Optional action button ID (for callback)

        Returns
        -------
            dict[str, Any]
                Notification card JSON structure

        Examples
        --------
            >>> card = builder.build_notification_card(
            ...     title="System Maintenance",
            ...     content="The system will be down for maintenance on Jan 20.",
            ...     level="warning",
            ...     action_text="View Details",
            ...     action_url="https://example.com/maintenance"
            ... )
        """
        # Map level to template color
        template_map = {
            "info": "blue",
            "warning": "orange",
            "error": "red",
            "success": "green",
        }
        template = template_map.get(level, "blue")

        # Build header
        header = {
            "title": {"tag": "plain_text", "content": title},
            "template": template,
        }

        # Build elements
        elements: list[dict[str, Any]] = []

        # Add content
        elements.append(
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": content,
                },
            }
        )

        # Add action button if provided
        if action_text:
            button: dict[str, Any] = {
                "tag": "button",
                "text": {"tag": "plain_text", "content": action_text},
                "type": "default",
            }

            if action_url:
                button["url"] = action_url

            if action_id:
                button["action_id"] = action_id
                button["value"] = {"action": "click"}

            elements.append({"tag": "action", "actions": [button]})

        return self.build_card(header=header, elements=elements)

    def build_form_card(
        self,
        title: str,
        fields: list[dict[str, Any]],
        submit_action_id: str,
        cancel_action_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Build a form card template.

        Creates a card with input fields and submit button.

        Parameters
        ----------
            title : str
                Form title
            fields : list[dict[str, Any]]
                List of form field configurations
                Each field should have: {"label": str, "name": str, "type": str, ...}
            submit_action_id : str
                Action ID for submit button
            cancel_action_id : str | None
                Optional action ID for cancel button

        Returns
        -------
            dict[str, Any]
                Form card JSON structure

        Examples
        --------
            >>> card = builder.build_form_card(
            ...     title="Feedback Form",
            ...     fields=[
            ...         {"label": "Name", "name": "name", "type": "input", "placeholder": "Your name"},
            ...         {"label": "Feedback", "name": "feedback", "type": "textarea", "placeholder": "Your feedback"}
            ...     ],
            ...     submit_action_id="submit_feedback",
            ...     cancel_action_id="cancel_feedback"
            ... )
        """
        # Build header
        header = {
            "title": {"tag": "plain_text", "content": title},
            "template": "blue",
        }

        # Build elements
        elements: list[dict[str, Any]] = []

        # Add form fields
        for field in fields:
            field_label = field.get("label", "")
            field_name = field.get("name", "")
            field_type = field.get("type", "input")
            placeholder = field.get("placeholder", "")
            required = field.get("required", False)

            # Add field label
            label_content = f"**{field_label}**"
            if required:
                label_content += " *"

            elements.append(
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": label_content,
                    },
                }
            )

            # Add input field based on type
            if field_type == "input":
                elements.append(
                    {
                        "tag": "input",
                        "name": field_name,
                        "placeholder": {"tag": "plain_text", "content": placeholder},
                        "required": required,
                    }
                )
            elif field_type == "textarea":
                elements.append(
                    {
                        "tag": "textarea",
                        "name": field_name,
                        "placeholder": {"tag": "plain_text", "content": placeholder},
                        "required": required,
                    }
                )
            elif field_type == "select":
                options = field.get("options", [])
                elements.append(
                    {
                        "tag": "select_static",
                        "name": field_name,
                        "placeholder": {"tag": "plain_text", "content": placeholder},
                        "options": [
                            {"text": {"tag": "plain_text", "content": opt}, "value": opt}
                            for opt in options
                        ],
                        "required": required,
                    }
                )

        # Add divider before actions
        elements.append({"tag": "hr"})

        # Add action buttons
        actions = [
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "提交"},
                "type": "primary",
                "action_id": submit_action_id,
            }
        ]

        if cancel_action_id:
            actions.append(
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "取消"},
                    "type": "default",
                    "action_id": cancel_action_id,
                }
            )

        elements.append({"tag": "action", "actions": actions})

        return self.build_card(header=header, elements=elements)
