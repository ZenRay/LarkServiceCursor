"""
Doc client for Lark CloudDoc API.

This module provides a high-level client for document operations via Lark CloudDoc API,
including creating documents, appending content, getting content, and updating blocks.
"""

from typing import Any

import requests  # type: ignore
from lark_oapi.api.docx.v1 import (
    CreateDocumentRequest,
    CreateDocumentRequestBody,
    GetDocumentRequest,
)

from lark_service.clouddoc.models import ContentBlock, Document, Permission
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.exceptions import (
    APIError,
    InvalidParameterError,
    NotFoundError,
    PermissionDeniedError,
)
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
            # Get tenant access token
            token = self.credential_pool.get_token(app_id, token_type="tenant_access_token")

            # Convert ContentBlock to Lark API format
            children: list[dict[str, Any]] = []

            # Block type mapping: string -> integer
            block_type_map = {
                "paragraph": 2,  # Text paragraph
                "heading": 3,    # Heading (need to specify level)
                "heading_1": 3,
                "heading_2": 4,
                "heading_3": 5,
                "list": 6,       # Bullet list
                "ordered_list": 7,  # Ordered list
                "code": 8,       # Code block
                "divider": 11,   # Divider line
                "image": 27,     # Image
                "table": 31,     # Table
            }

            for block in blocks:
                block_type_int = block_type_map.get(block.block_type, 2)  # Default to paragraph

                # Build block structure based on type
                if block.block_type in ["paragraph", "text"]:
                    # Text block
                    block_dict: dict[str, Any] = {
                        "block_type": block_type_int,
                        "text": {
                            "elements": [
                                {
                                    "text_run": {
                                        "content": str(block.content) if block.content else "",
                                        "text_element_style": {}
                                    }
                                }
                            ],
                            "style": {}
                        }
                    }
                elif block.block_type.startswith("heading"):
                    # Heading block
                    level = 1
                    if block.block_type == "heading_2":
                        level = 2
                    elif block.block_type == "heading_3":
                        level = 3

                    block_dict = {
                        "block_type": block_type_int,
                        f"heading{level}": {
                            "elements": [
                                {
                                    "text_run": {
                                        "content": str(block.content) if block.content else "",
                                        "text_element_style": {}
                                    }
                                }
                            ],
                            "style": {}
                        }
                    }
                elif block.block_type == "divider":
                    # Divider block
                    block_dict = {
                        "block_type": block_type_int,
                    }
                else:
                    # Default to text
                    block_dict = {
                        "block_type": 2,
                        "text": {
                            "elements": [
                                {
                                    "text_run": {
                                        "content": str(block.content) if block.content else "",
                                        "text_element_style": {}
                                    }
                                }
                            ],
                            "style": {}
                        }
                    }

                children.append(block_dict)

            # Make API request
            # First, get the document to find the root block_id
            # For simplicity, we'll use the document_id as the parent block
            # In practice, you might need to query the document structure first

            url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{doc_id}/children"

            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8"
            }

            payload = {
                "index": -1,  # Append to end
                "children": children
            }

            response = requests.post(url, headers=headers, json=payload, timeout=30)

            if response.status_code != 200:
                error_msg = f"Failed to append blocks: HTTP {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = f"{error_msg} - {error_data.get('msg', 'Unknown error')}"
                    error_code = error_data.get('code', 0)

                    # Map error codes
                    if error_code == 1770002:
                        raise NotFoundError(f"Document or block not found: {doc_id}")
                    elif error_code in [1770032, 403]:
                        raise PermissionDeniedError(f"No permission to edit document: {doc_id}")
                    elif error_code in [1770001, 1770007, 1770005, 1770028]:
                        raise InvalidParameterError(error_msg)
                except Exception as e:
                    if isinstance(e, (NotFoundError, PermissionDeniedError, InvalidParameterError)):
                        raise
                    logger.error(f"Failed to parse error response: {e}")

                raise APIError(error_msg)

            result = response.json()
            if result.get("code") != 0:
                error_msg = f"API returned error: {result.get('msg', 'Unknown error')}"
                raise APIError(error_msg)

            logger.info(f"Successfully appended {len(blocks)} blocks to document {doc_id}")
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
                logger.error(error_msg, extra={"doc_id": doc_id, "code": response.code})

                if response.code == 404:
                    raise NotFoundError(f"Document not found: {doc_id}")
                if response.code == 403:
                    raise PermissionDeniedError(error_msg)
                raise InvalidParameterError(error_msg)

            if not response.data or not response.data.document:
                raise NotFoundError(f"Document not found: {doc_id}")

            doc_data = response.data.document

            # Parse timestamps if available
            create_time = None
            update_time = None
            if hasattr(doc_data, "create_time") and doc_data.create_time:
                try:
                    from datetime import datetime
                    # Lark API returns timestamps in seconds
                    create_time = datetime.fromtimestamp(int(doc_data.create_time))
                except (ValueError, TypeError):
                    pass

            if hasattr(doc_data, "update_time") and doc_data.update_time:
                try:
                    from datetime import datetime
                    update_time = datetime.fromtimestamp(int(doc_data.update_time))
                except (ValueError, TypeError):
                    pass

            logger.info(f"Successfully retrieved document: {doc_data.title} ({doc_id})")

            return Document(
                doc_id=doc_data.document_id,
                title=doc_data.title,
                owner_id=getattr(doc_data, "owner_id", None),
                create_time=create_time,
                update_time=update_time,
                # Note: Content blocks require separate API call (GetDocumentBlockChildren)
                # For basic document info, we don't fetch blocks
                content_blocks=None,
            )

        return self.retry_strategy.execute(_get)

    def get_document(
        self,
        app_id: str,
        doc_id: str,
    ) -> Document:
        """
        Get document information (alias for get_document_content).

        Parameters
        ----------
            app_id : str
                Lark application ID
            doc_id : str
                Document ID

        Returns
        -------
            Document
                Document information

        Raises
        ------
            NotFoundError
                If document not found
            PermissionDeniedError
                If user has no permission

        Examples
        --------
            >>> doc = client.get_document(
            ...     app_id="cli_xxx",
            ...     doc_id="doxcn123"
            ... )
            >>> print(doc.title)
        """
        return self.get_document_content(app_id, doc_id)

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
            import requests  # type: ignore

            token = self.credential_pool.get_token(app_id, token_type="tenant_access_token")

            url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{block_id}"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            }

            # Build update content
            # Construct different update requests based on block_type
            elements = []

            if block.content:
                elements.append(
                    {
                        "text_run": {
                            "content": block.content,
                            "text_element_style": {},
                        }
                    }
                )

            payload = {"update_text_elements": {"elements": elements}}

            logger.debug(f"Updating block {block_id} with {len(elements)} elements")

            response = requests.patch(url, headers=headers, json=payload, timeout=30)

            if response.status_code != 200:
                error_msg = f"Failed to update block: HTTP {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = f"{error_msg} - {error_data.get('msg', 'Unknown error')}"
                    error_code = error_data.get("code", 0)

                    if error_code == 99991668:
                        raise NotFoundError(f"Block not found: {block_id}")
                    elif error_code in [403, 1254302]:
                        raise PermissionDeniedError(f"No permission to update block: {block_id}")
                    elif error_code in [400, 1254001]:
                        raise InvalidParameterError(error_msg)
                except Exception as e:
                    if isinstance(
                        e, NotFoundError | PermissionDeniedError | InvalidParameterError
                    ):
                        raise
                    logger.error(f"Failed to parse error response: {e}")

                raise APIError(error_msg)

            result = response.json()
            if result.get("code") != 0:
                error_msg = f"API returned error: {result.get('msg', 'Unknown error')}"
                error_code = result.get("code", 0)

                if error_code == 99991668:
                    raise NotFoundError(f"Block not found: {block_id}")
                elif error_code in [403, 1254302]:
                    raise PermissionDeniedError(f"No permission to update block: {block_id}")
                elif error_code in [400, 1254001]:
                    raise InvalidParameterError(error_msg)

                raise APIError(error_msg)

            logger.info(f"Successfully updated block {block_id} in document {doc_id}")
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
            import requests  # type: ignore

            token = self.credential_pool.get_token(app_id, token_type="tenant_access_token")

            url = f"https://open.feishu.cn/open-apis/drive/v1/permissions/{doc_id}/members"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            }

            # Map permission types to API format
            perm_map = {
                "read": "view",
                "write": "edit",
                "comment": "edit",
                "manage": "full_access",
            }
            perm = perm_map.get(permission_type, permission_type)

            payload = {
                "member_type": member_type,
                "member_id": member_id,
                "perm": perm,
                "type": "doc",
            }

            logger.debug(f"Granting {perm} permission to {member_type}:{member_id}")

            response = requests.post(url, headers=headers, json=payload, timeout=30)

            if response.status_code != 200:
                error_msg = f"Failed to grant permission: HTTP {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = f"{error_msg} - {error_data.get('msg', 'Unknown error')}"
                    error_code = error_data.get("code", 0)

                    if error_code in [403, 1254302]:
                        raise PermissionDeniedError(
                            f"No permission to grant access to document: {doc_id}"
                        )
                    elif error_code in [400, 1254001]:
                        raise InvalidParameterError(error_msg)
                except Exception as e:
                    if isinstance(e, PermissionDeniedError | InvalidParameterError):
                        raise
                    logger.error(f"Failed to parse error response: {e}")

                raise APIError(error_msg)

            result = response.json()
            if result.get("code") != 0:
                error_msg = f"API returned error: {result.get('msg', 'Unknown error')}"
                error_code = result.get("code", 0)

                if error_code in [403, 1254302]:
                    raise PermissionDeniedError(
                        f"No permission to grant access to document: {doc_id}"
                    )
                elif error_code in [400, 1254001]:
                    raise InvalidParameterError(error_msg)

                raise APIError(error_msg)

            logger.info(
                f"Successfully granted {permission_type} permission to {member_type}:{member_id}"
            )

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
            import requests  # type: ignore

            token = self.credential_pool.get_token(app_id, token_type="tenant_access_token")

            url = f"https://open.feishu.cn/open-apis/drive/v1/permissions/{doc_id}/members/{permission_id}"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            }

            # Add type parameter
            params = {"type": "doc"}

            logger.debug(f"Revoking permission {permission_id} from document {doc_id}")

            response = requests.delete(url, headers=headers, params=params, timeout=30)

            if response.status_code != 200:
                error_msg = f"Failed to revoke permission: HTTP {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = f"{error_msg} - {error_data.get('msg', 'Unknown error')}"
                    error_code = error_data.get("code", 0)

                    if error_code in [403, 1254302]:
                        raise PermissionDeniedError(
                            f"No permission to revoke access from document: {doc_id}"
                        )
                    elif error_code in [400, 1254001]:
                        raise InvalidParameterError(error_msg)
                except Exception as e:
                    if isinstance(e, PermissionDeniedError | InvalidParameterError):
                        raise
                    logger.error(f"Failed to parse error response: {e}")

                raise APIError(error_msg)

            result = response.json()
            if result.get("code") != 0:
                error_msg = f"API returned error: {result.get('msg', 'Unknown error')}"
                error_code = result.get("code", 0)

                if error_code in [403, 1254302]:
                    raise PermissionDeniedError(
                        f"No permission to revoke access from document: {doc_id}"
                    )
                elif error_code in [400, 1254001]:
                    raise InvalidParameterError(error_msg)

                raise APIError(error_msg)

            logger.info(f"Successfully revoked permission {permission_id} from document {doc_id}")
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
            import requests  # type: ignore

            token = self.credential_pool.get_token(app_id, token_type="tenant_access_token")

            url = f"https://open.feishu.cn/open-apis/drive/v1/permissions/{doc_id}/members"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            }

            # Determine type based on doc_id prefix
            # doxcn - doc, shtcn - sheet, bascn - bitable
            # Note: Some legacy format tokens may not require type parameter
            params = {}
            if doc_id.startswith("doxcn"):
                params["type"] = "doc"
            elif doc_id.startswith("shtcn"):
                params["type"] = "sheet"
            elif doc_id.startswith("bascn"):
                params["type"] = "bitable"
            elif doc_id.startswith("wikicn"):
                params["type"] = "wiki"
            # For legacy format tokens, don't add type parameter

            logger.debug(f"Listing permissions for document {doc_id}")

            response = requests.get(url, headers=headers, params=params, timeout=30)

            if response.status_code != 200:
                error_msg = f"Failed to list permissions: HTTP {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = f"{error_msg} - {error_data.get('msg', 'Unknown error')}"
                    error_code = error_data.get("code", 0)

                    if error_code in [403, 1254302, 1063002]:
                        raise PermissionDeniedError(
                            f"No permission to list permissions for document: {doc_id}"
                        )
                    elif error_code in [404, 1063005]:
                        raise NotFoundError(f"Document not found: {doc_id}")
                    elif error_code in [400, 1063001]:
                        raise InvalidParameterError(error_msg)
                except Exception as e:
                    if isinstance(
                        e, PermissionDeniedError | NotFoundError | InvalidParameterError
                    ):
                        raise
                    logger.error(f"Failed to parse error response: {e}")

                raise APIError(error_msg)

            result = response.json()
            if result.get("code") != 0:
                error_msg = f"API returned error: {result.get('msg', 'Unknown error')}"
                error_code = result.get("code", 0)

                if error_code in [403, 1254302, 1063002]:
                    raise PermissionDeniedError(
                        f"No permission to list permissions for document: {doc_id}"
                    )
                elif error_code in [404, 1063005]:
                    raise NotFoundError(f"Document not found: {doc_id}")
                elif error_code in [400, 1063001]:
                    raise InvalidParameterError(error_msg)

                raise APIError(error_msg)

            data = result.get("data", {})
            items = data.get("items", [])

            permissions = []
            for item in items:
                # Map permission types
                perm = item.get("perm", "view")
                perm_map = {
                    "view": "read",
                    "edit": "write",
                    "full_access": "manage",
                    "manage": "manage",
                }
                permission_type = perm_map.get(perm, perm)

                permissions.append(
                    Permission(
                        doc_id=doc_id,
                        member_type=item.get("member_type", "user"),  # type: ignore
                        member_id=item.get("member_id"),
                        permission_type=permission_type,  # type: ignore
                    )
                )

            logger.info(f"Successfully listed {len(permissions)} permissions for document {doc_id}")
            return permissions

        return self.retry_strategy.execute(_list)
