"""
Callback handler for Lark CardKit interactions.

This module provides functionality for handling card interaction callbacks,
including signature verification, URL verification, and event routing.
"""

import hashlib
import hmac
import json
from collections.abc import Callable
from typing import Any

from lark_service.cardkit.models import CallbackEvent
from lark_service.core.exceptions import InvalidParameterError, ValidationError
from lark_service.utils.logger import get_logger

logger = get_logger()


class CallbackHandler:
    """
    Handler for card interaction callbacks.

    Provides methods for verifying callback signatures, handling URL verification,
    and routing callback events to registered handlers.

    Attributes
    ----------
        verification_token : str
            Lark app verification token
        encrypt_key : str | None
            Optional encryption key for signature verification
        handlers : dict[str, Callable]
            Registered callback handlers by action_id

    Examples
    --------
        >>> handler = CallbackHandler(
        ...     verification_token="v_xxx",
        ...     encrypt_key="encrypt_xxx"
        ... )
        >>> handler.register_handler("approve_leave", handle_approve)
        >>> result = handler.handle_callback(request_data)
    """

    def __init__(
        self,
        verification_token: str,
        encrypt_key: str | None = None,
    ) -> None:
        """
        Initialize CallbackHandler.

        Parameters
        ----------
            verification_token : str
                Lark app verification token
            encrypt_key : str | None
                Optional encryption key for signature verification
        """
        self.verification_token = verification_token
        self.encrypt_key = encrypt_key
        self.handlers: dict[str, Callable[[CallbackEvent], dict[str, Any]]] = {}

    def verify_signature(
        self,
        timestamp: str,
        nonce: str,
        body: str,
        signature: str,
    ) -> bool:
        """
        Verify callback request signature.

        Uses HMAC-SHA256 to verify that the callback is from Lark.

        Parameters
        ----------
            timestamp : str
                Request timestamp
            nonce : str
                Request nonce
            body : str
                Request body (raw JSON string)
            signature : str
                Request signature from header

        Returns
        -------
            bool
                True if signature is valid, False otherwise

        Examples
        --------
            >>> is_valid = handler.verify_signature(
            ...     timestamp="1642512345",
            ...     nonce="abc123",
            ...     body='{"type":"url_verification"}',
            ...     signature="sha256_signature_here"
            ... )
        """
        if not self.encrypt_key:
            logger.warning("Encrypt key not configured, skipping signature verification")
            return True

        # Construct signature string: timestamp + nonce + encrypt_key + body
        sign_str = f"{timestamp}{nonce}{self.encrypt_key}{body}"

        # Calculate HMAC-SHA256
        calculated_signature = hmac.new(
            self.encrypt_key.encode("utf-8"),
            sign_str.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        is_valid = hmac.compare_digest(calculated_signature, signature)

        if not is_valid:
            logger.warning(
                "Signature verification failed",
                extra={
                    "timestamp": timestamp,
                    "nonce": nonce,
                    "expected": calculated_signature,
                    "received": signature,
                },
            )

        return is_valid

    def handle_url_verification(
        self,
        challenge: str,
        token: str,
    ) -> dict[str, str]:
        """
        Handle URL verification callback.

        Lark sends this callback to verify the callback URL when configuring
        card interactions.

        Parameters
        ----------
            challenge : str
                Challenge string from Lark
            token : str
                Verification token from request

        Returns
        -------
            dict[str, str]
                Response with challenge

        Raises
        ------
            ValidationError
                If verification token doesn't match

        Examples
        --------
            >>> response = handler.handle_url_verification(
            ...     challenge="challenge_string",
            ...     token="v_xxx"
            ... )
            >>> print(response["challenge"])
        """
        if token != self.verification_token:
            raise ValidationError(
                "Verification token mismatch",
                details={"expected": self.verification_token, "received": token},
            )

        logger.info(
            "URL verification successful",
            extra={"challenge": challenge},
        )

        return {"challenge": challenge}

    def register_handler(
        self,
        action_id: str,
        handler: Callable[[CallbackEvent], dict[str, Any]],
    ) -> None:
        """
        Register a callback handler for a specific action.

        Parameters
        ----------
            action_id : str
                Action ID to handle (e.g., "approve_leave")
            handler : Callable[[CallbackEvent], dict[str, Any]]
                Handler function that takes CallbackEvent and returns response

        Examples
        --------
            >>> def handle_approve(event: CallbackEvent) -> dict:
            ...     # Process approval
            ...     return {"status": "approved"}
            >>> handler.register_handler("approve_leave", handle_approve)
        """
        self.handlers[action_id] = handler
        logger.info(
            f"Registered handler for action: {action_id}",
            extra={"action_id": action_id},
        )

    def route_callback(
        self,
        event_data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Route callback event to registered handler.

        Extracts action_id from event and calls the corresponding handler.
        If no handler is registered, returns a default success response.

        Parameters
        ----------
            event_data : dict[str, Any]
                Callback event data from Lark

        Returns
        -------
            dict[str, Any]
                Handler response or default response

        Raises
        ------
            InvalidParameterError
                If event_data is invalid

        Examples
        --------
            >>> response = handler.route_callback({
            ...     "action": {"action_id": "approve_leave", "value": {"action": "approve"}},
            ...     "open_id": "ou_xxx",
            ...     "open_message_id": "om_xxx"
            ... })
        """
        try:
            # Parse event using Pydantic model
            event = CallbackEvent(**event_data)
        except Exception as e:
            raise InvalidParameterError(
                f"Invalid callback event data: {e}",
                details={"event_data": event_data},
            ) from e

        # Extract action_id from action payload
        action_id = event.action.get("action_id", "")

        logger.info(
            f"Routing callback for action: {action_id}",
            extra={
                "action_id": action_id,
                "user_id": event.user_id,
                "card_id": event.card_id,
            },
        )

        # Check if handler is registered
        if action_id in self.handlers:
            try:
                response = self.handlers[action_id](event)
                logger.info(
                    f"Handler executed successfully for action: {action_id}",
                    extra={"action_id": action_id, "response": response},
                )
                return response
            except Exception as e:
                logger.error(
                    f"Handler failed for action: {action_id}",
                    extra={"action_id": action_id, "error": str(e)},
                    exc_info=True,
                )
                # Return error response
                return {
                    "status": "error",
                    "message": f"Handler failed: {str(e)}",
                }
        else:
            logger.warning(
                f"No handler registered for action: {action_id}",
                extra={"action_id": action_id},
            )
            # Return default success response
            return {
                "status": "success",
                "message": "Event received",
            }

    def handle_callback(
        self,
        request_data: dict[str, Any],
        timestamp: str | None = None,
        nonce: str | None = None,
        signature: str | None = None,
    ) -> dict[str, Any]:
        """
        Main entry point for handling card callbacks.

        Handles both URL verification and card interaction callbacks.
        Optionally verifies signature if timestamp, nonce, and signature are provided.

        Parameters
        ----------
            request_data : dict[str, Any]
                Callback request data from Lark
            timestamp : str | None
                Request timestamp (for signature verification)
            nonce : str | None
                Request nonce (for signature verification)
            signature : str | None
                Request signature (for signature verification)

        Returns
        -------
            dict[str, Any]
                Response to send back to Lark

        Raises
        ------
            ValidationError
                If signature verification fails or data is invalid

        Examples
        --------
            >>> # URL verification
            >>> response = handler.handle_callback({
            ...     "type": "url_verification",
            ...     "challenge": "challenge_string",
            ...     "token": "v_xxx"
            ... })

            >>> # Card interaction
            >>> response = handler.handle_callback(
            ...     request_data={
            ...         "type": "card_action_trigger",
            ...         "action": {"action_id": "approve_leave", ...},
            ...         ...
            ...     },
            ...     timestamp="1642512345",
            ...     nonce="abc123",
            ...     signature="sha256_signature"
            ... )
        """
        # Verify signature if provided
        if timestamp and nonce and signature:
            body = json.dumps(request_data, separators=(",", ":"))
            if not self.verify_signature(timestamp, nonce, body, signature):
                raise ValidationError(
                    "Signature verification failed",
                    details={"timestamp": timestamp, "nonce": nonce},
                )

        # Get callback type
        callback_type = request_data.get("type")

        if callback_type == "url_verification":
            # Handle URL verification
            challenge = request_data.get("challenge", "")
            token = request_data.get("token", "")
            return self.handle_url_verification(challenge, token)

        elif callback_type == "card_action_trigger":
            # Handle card interaction
            return self.route_callback(request_data)

        else:
            logger.warning(
                f"Unknown callback type: {callback_type}",
                extra={"callback_type": callback_type},
            )
            return {
                "status": "error",
                "message": f"Unknown callback type: {callback_type}",
            }
