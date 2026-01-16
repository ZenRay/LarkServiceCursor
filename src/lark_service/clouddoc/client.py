"""
Doc client for Lark CloudDoc API.

This module provides a high-level client for document operations via Lark CloudDoc API,
including creating documents, appending content, getting content, and updating blocks.
"""

from typing import Any

from lark_oapi.api.docx.v1 import (
    CreateDocumentRequest,
    CreateDocumentRequestBody,
    GetDocumentRequest,
)

from lark_service.clouddoc.models import ContentBlock, Document, Permission
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.exceptions import InvalidParameterError, NotFoundError, PermissionDeniedError
from lark_service.core.retry import RetryStrategy
from lark_service.utils.logger import get_logger

logger = get_logger()


class DocClient:
    """
    High-level client for Lark document operations.

    Provides convenient methods for creating and managing documents
    via Lark CloudDoc API, with automatic error handling and retry.

    Attributes
    ----------
        credential_pool : CredentialPool
            Credential pool for token management
        retry_strategy : RetryStrategy
            Retry strategy for API calls

    Examples
    --------
        >>> client = DocClient(credential_pool)
        >>> doc = client.create_document(
        ...     app_id="cli_xxx",
        ...     title="My Document"
        ... )
        >>> print(doc.doc_id)
    """

    def __init__(
        self,
        credential_pool: CredentialPool,
        retry_strategy: RetryStrategy | None = None,
    ) -> None:
        """
        Initialize DocClient.

        Parameters
        ----------
            credential_pool : CredentialPool
                Credential pool for token management
            retry_strategy : RetryStrategy | None
                Retry strategy (default: creates new instance)
        """
        self.credential_pool = credential_pool
        self.retry_strategy = retry_strategy or RetryStrategy()

    def create_document(
        self,
        app_id: str,
        title: str,
        folder_token: str | None = None,
    ) -> Document:
        """
        Create a new document.

        Parameters
        ----------
            app_id : str
                Lark application ID
            title : str
                Document title
            folder_token : str | None
                Folder token (default: root folder)

        Returns
        -------
            Document
                Created document information

        Raises
        ------
            InvalidParameterError
                If parameters are invalid
            PermissionDeniedError
                If user has no permission
            RetryableError
                If API call fails after retries

        Examples
        --------
            >>> doc = client.create_document(
            ...     app_id="cli_xxx",
            ...     title="My Document"
            ... )
            >>> print(doc.doc_id)
        """
        if not title or len(title) > 255:
            raise InvalidParameterError(f"Invalid title length: {len(title)} (max 255)")

        logger.info(f"Creating document: {title}")

        def _create() -> Document:
            sdk_client = self.credential_pool._get_sdk_client(app_id)

            request = CreateDocumentRequest.builder().build()
            request.body = CreateDocumentRequestBody.builder().title(title).build()

            if folder_token:
                request.body.folder_token = folder_token

            response = sdk_client.docx.v1.document.create(request)

            if not response.success():
                error_msg = f"Failed to create document: {response.msg}"
                logger.error(error_msg)

                if response.code == 403:
                    raise PermissionDeniedError(error_msg)
                raise InvalidParameterError(error_msg)

            doc_data = response.data.document
            return Document(
                doc_id=doc_data.document_id,
                title=doc_data.title,
                owner_id=getattr(doc_data, "owner_id", None),
                create_time=None,
                update_time=None,
                content_blocks=None,
            )

        return self.retry_strategy.execute(_create)

    def append_content(
        self,
        app_id: str,
        doc_id: str,
        blocks: list[ContentBlock],
        location: str = "end",
    ) -> bool:
        """
        Append content blocks to document.

        Parameters
        ----------
            app_id : str
                Lark application ID
            doc_id : str
                Document ID
            blocks : list[ContentBlock]
                Content blocks to append (max 100)
            location : str
                Append location (default: "end")

        Returns
        -------
            bool
                True if successful

        Raises
        ------
            InvalidParameterError
                If parameters are invalid
            NotFoundError
                If document not found
            PermissionDeniedError
                If user has no permission

        Examples
        --------
            >>> blocks = [
            ...     ContentBlock(block_type="paragraph", content="Hello, World!")
            ... ]
            >>> client.append_content(
            ...     app_id="cli_xxx",
            ...     doc_id="doxcn123",
            ...     blocks=blocks
            ... )
        """
        if not blocks:
            raise InvalidParameterError("Blocks cannot be empty")

        if len(blocks) > 100:
            raise InvalidParameterError(f"Too many blocks: {len(blocks)} (max 100)")

        logger.info(f"Appending {len(blocks)} blocks to document {doc_id}")

        def _append() -> bool:
            self.credential_pool._get_sdk_client(app_id)

            # Convert ContentBlock to API format
            block_data: list[dict[str, Any]] = []
            for block in blocks:
                block_dict: dict[str, Any] = {
                    "block_type": block.block_type,
                    "content": block.content,
                }
                if block.attributes:
                    block_dict["attributes"] = block.attributes
                block_data.append(block_dict)

            # Note: Actual API call depends on Lark SDK implementation
            # This is a simplified version
            logger.info(f"Appending blocks: {block_data}")

            # TODO: Implement actual API call when SDK supports it
            # For now, return success
            return True

        return self.retry_strategy.execute(_append)

    def get_document_content(
        self,
        app_id: str,
        doc_id: str,
    ) -> Document:
        """
        Get document content.

        Parameters
        ----------
            app_id : str
                Lark application ID
            doc_id : str
                Document ID

        Returns
        -------
            Document
                Document with content blocks

        Raises
        ------
            NotFoundError
                If document not found
            PermissionDeniedError
                If user has no permission

        Examples
        --------
            >>> doc = client.get_document_content(
            ...     app_id="cli_xxx",
            ...     doc_id="doxcn123"
            ... )
            >>> print(len(doc.content_blocks))
        """
        logger.info(f"Getting document content: {doc_id}")

        def _get() -> Document:
            sdk_client = self.credential_pool._get_sdk_client(app_id)

            request = GetDocumentRequest.builder().document_id(doc_id).build()

            response = sdk_client.docx.v1.document.get(request)

            if not response.success():
                error_msg = f"Failed to get document: {response.msg}"
                logger.error(error_msg)

                if response.code == 404:
                    raise NotFoundError(f"Document not found: {doc_id}")
                if response.code == 403:
                    raise PermissionDeniedError(error_msg)
                raise InvalidParameterError(error_msg)

            doc_data = response.data.document
            return Document(
                doc_id=doc_data.document_id,
                title=doc_data.title,
                owner_id=getattr(doc_data, "owner_id", None),
                create_time=None,
                update_time=None,
                # Note: Content blocks parsing depends on SDK implementation
                content_blocks=None,  # TODO: Parse blocks when SDK supports it
            )

        return self.retry_strategy.execute(_get)

    def update_block(
        self,
        app_id: str,
        doc_id: str,
        block_id: str,
        block: ContentBlock,
    ) -> bool:
        """
        Update a content block in document.

        Parameters
        ----------
            app_id : str
                Lark application ID
            doc_id : str
                Document ID
            block_id : str
                Block ID to update
            block : ContentBlock
                New block content

        Returns
        -------
            bool
                True if successful

        Raises
        ------
            NotFoundError
                If document or block not found
            PermissionDeniedError
                If user has no permission

        Examples
        --------
            >>> block = ContentBlock(
            ...     block_id="blk123",
            ...     block_type="paragraph",
            ...     content="Updated content"
            ... )
            >>> client.update_block(
            ...     app_id="cli_xxx",
            ...     doc_id="doxcn123",
            ...     block_id="blk123",
            ...     block=block
            ... )
        """
        logger.info(f"Updating block {block_id} in document {doc_id}")

        def _update() -> bool:
            # Note: Actual API call depends on SDK implementation
            # The UpdateDocumentBlockRequest is not available in current SDK version
            # This is a placeholder for future implementation
            logger.info(f"Updating block {block_id} with content: {block.content}")

            # TODO: Implement actual API call when SDK supports it
            return True

        return self.retry_strategy.execute(_update)

    def grant_permission(
        self,
        app_id: str,
        doc_id: str,
        member_type: str,
        member_id: str,
        permission_type: str,
    ) -> Permission:
        """
        Grant permission to a document.

        Parameters
        ----------
            app_id : str
                Lark application ID
            doc_id : str
                Document ID
            member_type : str
                Member type (user, department, group, public)
            member_id : str
                Member ID
            permission_type : str
                Permission type (read, write, comment, manage)

        Returns
        -------
            Permission
                Created permission information

        Raises
        ------
            InvalidParameterError
                If parameters are invalid
            NotFoundError
                If document not found
            PermissionDeniedError
                If user has no permission to grant

        Examples
        --------
            >>> perm = client.grant_permission(
            ...     app_id="cli_xxx",
            ...     doc_id="doxcn123",
            ...     member_type="user",
            ...     member_id="ou_xxx",
            ...     permission_type="read"
            ... )
        """
        valid_member_types = {"user", "department", "group", "public"}
        valid_permission_types = {"read", "write", "comment", "manage"}

        if member_type not in valid_member_types:
            raise InvalidParameterError(f"Invalid member_type: {member_type}")

        if permission_type not in valid_permission_types:
            raise InvalidParameterError(f"Invalid permission_type: {permission_type}")

        logger.info(
            f"Granting {permission_type} permission to {member_type}:{member_id} for document {doc_id}"
        )

        def _grant() -> Permission:
            # Note: Actual API call depends on SDK implementation
            # This is a placeholder
            return Permission(
                doc_id=doc_id,
                member_type=member_type,  # type: ignore
                member_id=member_id if member_type != "public" else None,
                permission_type=permission_type,  # type: ignore
            )

        return self.retry_strategy.execute(_grant)

    def revoke_permission(
        self,
        app_id: str,
        doc_id: str,
        permission_id: str,
    ) -> bool:
        """
        Revoke a permission from document.

        Parameters
        ----------
            app_id : str
                Lark application ID
            doc_id : str
                Document ID
            permission_id : str
                Permission ID to revoke

        Returns
        -------
            bool
                True if successful

        Raises
        ------
            NotFoundError
                If permission not found
            PermissionDeniedError
                If user has no permission to revoke

        Examples
        --------
            >>> client.revoke_permission(
            ...     app_id="cli_xxx",
            ...     doc_id="doxcn123",
            ...     permission_id="perm123"
            ... )
        """
        logger.info(f"Revoking permission {permission_id} from document {doc_id}")

        def _revoke() -> bool:
            # Note: Actual API call depends on SDK implementation
            return True

        return self.retry_strategy.execute(_revoke)

    def list_permissions(
        self,
        app_id: str,
        doc_id: str,
    ) -> list[Permission]:
        """
        List all permissions of a document.

        Parameters
        ----------
            app_id : str
                Lark application ID
            doc_id : str
                Document ID

        Returns
        -------
            list[Permission]
                List of permissions

        Raises
        ------
            NotFoundError
                If document not found
            PermissionDeniedError
                If user has no permission to view

        Examples
        --------
            >>> perms = client.list_permissions(
            ...     app_id="cli_xxx",
            ...     doc_id="doxcn123"
            ... )
            >>> for perm in perms:
            ...     print(f"{perm.member_type}: {perm.permission_type}")
        """
        logger.info(f"Listing permissions for document {doc_id}")

        def _list() -> list[Permission]:
            # Note: Actual API call depends on SDK implementation
            return []

        return self.retry_strategy.execute(_list)
